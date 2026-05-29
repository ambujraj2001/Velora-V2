import uuid

from deepagents import create_deep_agent
from sqlalchemy.orm import Session

from app.agent.prompt_loader import load_query_format_hint, load_system_prompt
from app.agent.tools.add_sample_query import build_add_sample_query_tool
from app.agent.tools.execute_query import build_execute_query_tool
from app.agent.tools.get_db_info import build_get_db_info_tool
from app.agent.tools.retrieve_schema import build_retrieve_schema_tool
from app.logging import get_logger
from app.models.tenant import Tenant
from app.models.tenant_database import TenantDatabase
from app.nvidia import get_llm

log = get_logger(__name__)


def build_agent(tenant_id: str, db_session: Session):
    tenant_uuid = uuid.UUID(tenant_id)
    tenant = db_session.query(Tenant).filter_by(id=tenant_uuid).first()
    tenant_db = (
        db_session.query(TenantDatabase).filter_by(tenant_id=tenant_uuid).first()
    )

    log.info(
        "agent.build",
        tenant_id=tenant_id,
        tenant_name=tenant.name if tenant else None,
        db_type=tenant_db.db_type if tenant_db else None,
    )

    tools = [
        build_retrieve_schema_tool(tenant_id, db_session),
        build_execute_query_tool(tenant_id, db_session),
        build_get_db_info_tool(tenant_id, db_session),
        build_add_sample_query_tool(tenant_id, db_session),
    ]

    query_format_hint = load_query_format_hint(tenant_db.db_type)
    system_prompt = load_system_prompt(
        tenant_name=tenant.name,
        db_type=tenant_db.db_type,
        query_format_hint=query_format_hint,
    )

    agent = create_deep_agent(
        model=get_llm(),
        tools=tools,
        system_prompt=system_prompt,
    )
    log.info("agent.build.complete", tenant_id=tenant_id, tool_count=len(tools))
    return agent
