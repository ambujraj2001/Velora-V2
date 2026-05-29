import json
import re

from app.logging import get_logger
from app.nvidia import get_llm

log = get_logger(__name__)


def _format_columns(table_schema: dict) -> str:
    lines = []
    for col in table_schema.get("columns", []):
        nullable = "nullable" if col.get("nullable") else "not null"
        lines.append(f"- {col['name']} ({col['type']}, {nullable})")
    return "\n".join(lines) if lines else "(no fields detected)"


def _strip_markdown_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def enrich_table(table_name: str, table_schema: dict, db_type: str) -> dict:
    log.info(
        "onboarding.enrich.begin",
        table_name=table_name,
        db_type=db_type,
        column_count=len(table_schema.get("columns", [])),
    )
    column_list = _format_columns(table_schema)

    prompt = f"""Given this database schema, provide the following in JSON only.
No markdown, no explanation, just the raw JSON object.

Schema:
Table/Collection name: {table_name}
DB type: {db_type}
Fields/Columns:
{column_list}

Respond with exactly this structure:
{{
  "description": "2-3 sentences describing what this stores and its business purpose",
  "business_questions": [
    "3 to 5 questions this table can answer"
  ],
  "sample_queries": [
    {{
      "question": "plain English question",
      "query": "SQL SELECT or MongoDB JSON filter"
    }}
  ]
}}

For Postgres sample_queries: use SQL SELECT statements only.
For MongoDB sample_queries: use JSON filter format only:
  {{"collection": "name", "filter": {{}}, "limit": 50}}
Use only actual column/field names from the schema above."""

    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        content = _strip_markdown_fences(content)
        enriched = json.loads(content)
        log.info(
            "onboarding.enrich.success",
            table_name=table_name,
            sample_queries=len(enriched.get("sample_queries", [])),
        )
        return enriched
    except (json.JSONDecodeError, Exception) as e:
        log.warning(
            "onboarding.enrich.fallback",
            table_name=table_name,
            error=str(e),
        )
        return {
            "description": f"Table {table_name} in the database.",
            "business_questions": [],
            "sample_queries": [],
        }
