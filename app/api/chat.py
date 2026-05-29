import asyncio
import json
import queue
import threading
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agent.factory import build_agent
from app.agent.stream_callback import ToolStepCallbackHandler
from app.agent.utils import extract_agent_answer
from app.api.tenants import get_authenticated_tenant
from app.database import SessionLocal, get_db
from app.logging import get_logger
from app.logging.context import request_id_var
from app.models.chat_history import ChatHistory
from app.models.tenant_database import TenantDatabase
from app.security.auth import require_tenant_access

router = APIRouter()
log = get_logger(__name__)

STREAM_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


class ChatRequest(BaseModel):
    message: str
    session_id: str


class ChatResponse(BaseModel):
    answer: str
    session_id: str


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _validate_chat_ready(tenant_id: str, db: Session) -> uuid.UUID:
    tenant_uuid = uuid.UUID(tenant_id)
    tenant_db = (
        db.query(TenantDatabase)
        .filter(TenantDatabase.tenant_id == tenant_uuid)
        .first()
    )
    if not tenant_db:
        log.warning("chat.rejected", tenant_id=tenant_id, reason="no_database")
        raise HTTPException(status_code=400, detail="No database connected.")
    if tenant_db.status != "active":
        log.warning(
            "chat.rejected",
            tenant_id=tenant_id,
            reason="database_not_active",
            db_status=tenant_db.status,
        )
        raise HTTPException(
            status_code=400,
            detail=(
                "Database not ready. Call POST /onboard/{tenant_id} and wait for "
                "status 'active' before chatting."
            ),
        )
    return tenant_uuid


def _load_chat_history(
    tenant_uuid: uuid.UUID, session_id: str, db: Session
) -> list[dict]:
    history_rows = (
        db.query(ChatHistory)
        .filter(
            ChatHistory.tenant_id == tenant_uuid,
            ChatHistory.session_id == session_id,
        )
        .order_by(ChatHistory.created_at.desc())
        .limit(10)
        .all()
    )
    history_rows.reverse()
    return [{"role": row.role, "content": row.content} for row in history_rows]


def _save_chat_turn(
    tenant_uuid: uuid.UUID,
    session_id: str,
    user_message: str,
    answer: str,
    db: Session,
) -> None:
    db.add(
        ChatHistory(
            tenant_id=tenant_uuid,
            session_id=session_id,
            role="user",
            content=user_message,
        )
    )
    db.add(
        ChatHistory(
            tenant_id=tenant_uuid,
            session_id=session_id,
            role="assistant",
            content=answer,
        )
    )
    db.commit()


def _friendly_stream_error(exc: Exception) -> str:
    message = str(exc)
    if "429" in message or "Too Many Requests" in message:
        return "NVIDIA API rate limit reached. Wait a moment and try again."
    if "401" in message or "Unauthorized" in message:
        return "NVIDIA API authentication failed. Check your NVIDIA_API_KEY."
    return (
        "Chat failed while running the agent. "
        "Check server logs for details."
    )


@router.post("/{tenant_id}/stream")
async def chat_stream(
    tenant_id: str,
    body: ChatRequest,
    db: Session = Depends(get_db),
    authenticated_tenant_id: str = Depends(get_authenticated_tenant),
):
    require_tenant_access(tenant_id, authenticated_tenant_id)
    tenant_uuid = _validate_chat_ready(tenant_id, db)
    history = _load_chat_history(tenant_uuid, body.session_id, db)

    log.info(
        "chat.stream.request",
        tenant_id=tenant_id,
        session_id=body.session_id,
        message_length=len(body.message),
        history_messages=len(history),
    )

    agent_input = {"messages": history + [{"role": "user", "content": body.message}]}
    event_queue: queue.Queue = queue.Queue()
    sentinel = object()

    _req_id = request_id_var.get()

    def run_agent_sync() -> None:
        from app.logging.context import bind_context
        if _req_id:
            bind_context(request_id=_req_id, tenant_id=tenant_id)
        thread_db = SessionLocal()
        try:
            thread_agent = build_agent(tenant_id, thread_db)
            handler = ToolStepCallbackHandler(event_queue)
            result = thread_agent.invoke(
                agent_input,
                config={"callbacks": [handler]},
            )
            event_queue.put({"type": "_result", "result": result})
        except Exception as exc:
            event_queue.put({"type": "_error", "error": exc})
        finally:
            thread_db.close()
            event_queue.put(sentinel)

    async def event_generator():
        agent_start = time.perf_counter()
        thread = threading.Thread(target=run_agent_sync, daemon=True)
        thread.start()

        yield _sse({"type": "started"})

        try:
            while True:
                item = await asyncio.to_thread(event_queue.get)
                if item is sentinel:
                    break

                if item.get("type") == "_error":
                    raise item["error"]

                if item.get("type") == "_result":
                    answer = extract_agent_answer(item["result"])
                    if not answer:
                        answer = "I could not generate a response. Please try again."

                    _save_chat_turn(
                        tenant_uuid,
                        body.session_id,
                        body.message,
                        answer,
                        db,
                    )

                    duration_ms = round((time.perf_counter() - agent_start) * 1000, 2)
                    log.info(
                        "chat.stream.complete",
                        tenant_id=tenant_id,
                        session_id=body.session_id,
                        duration_ms=duration_ms,
                        answer_length=len(answer),
                    )
                    yield _sse(
                        {
                            "type": "done",
                            "answer": answer,
                            "session_id": body.session_id,
                        }
                    )
                    continue

                if item.get("type") == "step":
                    if item.get("status") == "start":
                        log.info(
                            "chat.stream.tool_start",
                            tenant_id=tenant_id,
                            tool=item.get("tool"),
                        )
                    else:
                        log.info(
                            "chat.stream.tool_end",
                            tenant_id=tenant_id,
                            tool=item.get("tool"),
                        )
                    yield _sse(item)

            thread.join(timeout=1)
        except Exception as exc:
            log.exception(
                "chat.stream.failed",
                tenant_id=tenant_id,
                session_id=body.session_id,
                error=str(exc),
            )
            yield _sse(
                {
                    "type": "error",
                    "message": _friendly_stream_error(exc),
                }
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=STREAM_HEADERS,
    )


@router.post("/{tenant_id}", response_model=ChatResponse)
def chat(
    tenant_id: str,
    body: ChatRequest,
    db: Session = Depends(get_db),
    authenticated_tenant_id: str = Depends(get_authenticated_tenant),
):
    require_tenant_access(tenant_id, authenticated_tenant_id)
    log.info(
        "chat.request",
        tenant_id=tenant_id,
        session_id=body.session_id,
        message_length=len(body.message),
    )

    tenant_uuid = _validate_chat_ready(tenant_id, db)
    history = _load_chat_history(tenant_uuid, body.session_id, db)
    log.info(
        "chat.history.loaded",
        tenant_id=tenant_id,
        session_id=body.session_id,
        history_messages=len(history),
    )

    agent_start = time.perf_counter()
    try:
        log.info("chat.agent.build", tenant_id=tenant_id)
        agent = build_agent(tenant_id, db)
        log.info("chat.agent.invoke", tenant_id=tenant_id, session_id=body.session_id)
        result = agent.invoke(
            {"messages": history + [{"role": "user", "content": body.message}]}
        )
        answer = extract_agent_answer(result)
        agent_duration_ms = round((time.perf_counter() - agent_start) * 1000, 2)
        log.info(
            "chat.agent.complete",
            tenant_id=tenant_id,
            session_id=body.session_id,
            duration_ms=agent_duration_ms,
            answer_length=len(answer) if answer else 0,
        )
    except Exception:
        agent_duration_ms = round((time.perf_counter() - agent_start) * 1000, 2)
        log.exception(
            "chat.agent.failed",
            tenant_id=tenant_id,
            session_id=body.session_id,
            duration_ms=agent_duration_ms,
        )
        raise HTTPException(
            status_code=500,
            detail="Chat failed while running the agent. Check server logs for details.",
        ) from None

    if not answer:
        answer = "I could not generate a response. Please try again."
        log.warning(
            "chat.agent.empty_answer",
            tenant_id=tenant_id,
            session_id=body.session_id,
        )

    _save_chat_turn(tenant_uuid, body.session_id, body.message, answer, db)
    log.info(
        "chat.complete",
        tenant_id=tenant_id,
        session_id=body.session_id,
        answer_length=len(answer),
    )

    return ChatResponse(answer=answer, session_id=body.session_id)
