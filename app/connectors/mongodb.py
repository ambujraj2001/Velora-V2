import json
import re
from typing import Any

from bson import ObjectId
from pymongo import MongoClient

from app.connectors.base import BaseConnector
from app.logging import get_logger

log = get_logger(__name__)

# MongoDB operations that write data — blocked in query filter/pipeline
_DANGEROUS_MONGO_KEYS = re.compile(
    r"\$(set|unset|inc|push|pull|pop|rename|addToSet|mul|min|max|"
    r"currentDate|bit|out|merge|unionWith)",
    re.IGNORECASE,
)

# Top-level keys that indicate write intent
_DANGEROUS_TOP_KEYS = {"delete", "drop", "update", "insert", "remove", "rename", "createIndex", "dropIndex"}


def _infer_type(value: Any) -> str:
    if value is None:
        return "null"
    return type(value).__name__


def _convert_objectids(doc: dict) -> dict:
    result = {}
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, dict):
            result[key] = _convert_objectids(value)
        elif isinstance(value, list):
            result[key] = [
                str(v) if isinstance(v, ObjectId) else v for v in value
            ]
        else:
            result[key] = value
    return result


def _is_safe_mongo_query(parsed: dict) -> tuple[bool, str]:
    """Check if a MongoDB query is safe (read-only). Returns (is_safe, reason)."""
    # Check for dangerous top-level keys
    for key in parsed:
        if key.lower() in _DANGEROUS_TOP_KEYS:
            return False, f"Operation '{key}' is not allowed (write operation)"

    # Check the entire JSON string for dangerous $ operators
    raw = json.dumps(parsed)
    match = _DANGEROUS_MONGO_KEYS.search(raw)
    if match:
        return False, f"Operator '{match.group(0)}' is not allowed (write operation)"

    # Check aggregate pipeline for $out or $merge stages
    pipeline = parsed.get("pipeline", parsed.get("aggregate", []))
    if isinstance(pipeline, list):
        for stage in pipeline:
            if isinstance(stage, dict):
                if "$out" in stage or "$merge" in stage:
                    return False, "$out/$merge stages are not allowed (they write data)"

    return True, ""


class MongoConnector(BaseConnector):
    def __init__(self, conn_string: str):
        self.client = MongoClient(conn_string, serverSelectionTimeoutMS=5000)
        self.db = self.client.get_default_database()

    def test_connection(self) -> bool:
        try:
            self.client.admin.command("ping")
            return True
        except Exception:
            return False

    def get_schema(self) -> dict:
        schema: dict = {}
        for collection_name in self.db.list_collection_names():
            samples = list(self.db[collection_name].find().limit(5))
            field_types: dict[str, set[str]] = {}

            for doc in samples:
                for field, value in doc.items():
                    if field not in field_types:
                        field_types[field] = set()
                    field_types[field].add(_infer_type(value))

            columns = []
            sample_fields = []
            for field_name, types in sorted(field_types.items()):
                type_str = ", ".join(sorted(t for t in types if t != "null")) or "unknown"
                nullable = "null" in types
                columns.append(
                    {
                        "name": field_name,
                        "type": type_str,
                        "nullable": nullable,
                    }
                )
                sample_fields.append(field_name)

            schema[collection_name] = {
                "type": "collection",
                "columns": columns,
                "foreign_keys": [],
                "sample_fields": sample_fields,
            }

        return schema

    def execute(self, query: str) -> list[dict]:
        try:
            parsed = json.loads(query)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON query: {exc}") from exc

        if "collection" not in parsed:
            raise ValueError('Query must include "collection" key')

        # Safety check
        is_safe, reason = _is_safe_mongo_query(parsed)
        if not is_safe:
            raise ValueError(f"Query blocked: {reason}")

        collection_name = parsed["collection"]

        # Support aggregate pipelines
        pipeline = parsed.get("pipeline") or parsed.get("aggregate")
        if pipeline and isinstance(pipeline, list):
            log.debug("connector.mongodb.aggregate", collection=collection_name)
            cursor = self.db[collection_name].aggregate(pipeline)
            results = [_convert_objectids(doc) for doc in cursor]
            return results[:200]

        # Standard find query
        filter_doc = parsed.get("filter", {})
        projection = parsed.get("projection", None)
        sort = parsed.get("sort", None)
        limit = min(parsed.get("limit", 50), 200)

        cursor = self.db[collection_name].find(filter_doc, projection)
        if sort:
            if isinstance(sort, dict):
                sort = list(sort.items())
            cursor = cursor.sort(sort)
        cursor = cursor.limit(limit)

        return [_convert_objectids(doc) for doc in cursor]
