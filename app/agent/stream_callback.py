import queue
from typing import Any

from langchain_core.callbacks.base import BaseCallbackHandler

from app.agent.tool_messages import friendly_tool_message


class ToolStepCallbackHandler(BaseCallbackHandler):
    """Sync callback that pushes tool step events to a thread-safe queue."""

    def __init__(self, event_queue: queue.Queue[dict[str, Any]]):
        self._queue = event_queue
        self._run_tools: dict[Any, str] = {}

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: Any,
        **kwargs: Any,
    ) -> None:
        tool_name = serialized.get("name") or "tool"
        self._run_tools[run_id] = tool_name
        self._queue.put(
            {
                "type": "step",
                "status": "start",
                "tool": tool_name,
                "message": friendly_tool_message(tool_name),
            }
        )

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: Any,
        **kwargs: Any,
    ) -> None:
        tool_name = self._run_tools.pop(run_id, "tool")
        self._queue.put(
            {
                "type": "step",
                "status": "end",
                "tool": tool_name,
            }
        )

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: Any,
        **kwargs: Any,
    ) -> None:
        tool_name = self._run_tools.pop(run_id, "tool")
        self._queue.put(
            {
                "type": "step",
                "status": "end",
                "tool": tool_name,
            }
        )
