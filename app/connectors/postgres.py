import psycopg2
import psycopg2.extras
import re
from psycopg2 import pool

from app.connectors.base import BaseConnector
from app.logging import get_logger

log = get_logger(__name__)

# Statements that modify data or schema — blocked unconditionally.
# We use a blocklist so any new read-only syntax (CTEs, LATERAL, etc.) works by default.
_DANGEROUS_STATEMENTS = re.compile(
    r"^\s*("
    r"INSERT|UPDATE|DELETE|MERGE|UPSERT"
    r"|CREATE|ALTER|DROP|TRUNCATE"
    r"|GRANT|REVOKE"
    r"|COPY"
    r"|DO"
    r"|CALL"
    r"|SET|RESET"
    r"|BEGIN|START|COMMIT|END|ROLLBACK|SAVEPOINT|RELEASE"
    r"|LOCK|VACUUM|CLUSTER|REINDEX|REFRESH"
    r"|COMMENT|SECURITY\s+LABEL"
    r"|LISTEN|NOTIFY|UNLISTEN"
    r"|PREPARE|EXECUTE|DEALLOCATE"
    r"|DECLARE|FETCH|MOVE|CLOSE"
    r"|REASSIGN|IMPORT|DISCARD"
    r")\b",
    re.IGNORECASE,
)

# Even inside a CTE or subquery, these tokens should never appear
_DANGEROUS_TOKENS = re.compile(
    r"\b(INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|DROP\s+|TRUNCATE\s+|CREATE\s+|ALTER\s+)\b",
    re.IGNORECASE,
)


def _is_safe_query(query: str) -> tuple[bool, str]:
    """Check if a SQL query is safe (read-only). Returns (is_safe, reason)."""
    stripped = query.strip()

    if not stripped:
        return False, "Empty query"

    # Remove SQL comments before checking
    no_comments = re.sub(r"--[^\n]*", "", stripped)
    no_comments = re.sub(r"/\*.*?\*/", "", no_comments, flags=re.DOTALL)
    no_comments = no_comments.strip()

    if not no_comments:
        return False, "Query is only comments"

    # Check if the statement starts with a dangerous keyword
    if _DANGEROUS_STATEMENTS.match(no_comments):
        return False, "Statement type is not allowed (write/DDL operation)"

    # Check for dangerous tokens anywhere in the query (catches INSERT inside CTEs, etc.)
    match = _DANGEROUS_TOKENS.search(no_comments)
    if match:
        return False, f"Query contains forbidden operation: {match.group(0).strip()}"

    # Check for multiple statements (semicolons that aren't inside strings)
    # Simple heuristic: split on ; and check if more than one non-empty statement
    parts = [p.strip() for p in no_comments.split(";") if p.strip()]
    if len(parts) > 1:
        return False, "Multiple statements not allowed"

    return True, ""


class PostgresConnector(BaseConnector):
    def __init__(self, conn_string: str):
        self._pool = pool.SimpleConnectionPool(minconn=1, maxconn=5, dsn=conn_string)

    def _get_conn(self):
        return self._pool.getconn()

    def _put_conn(self, conn):
        self._pool.putconn(conn)

    def test_connection(self) -> bool:
        conn = None
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            log.debug("connector.postgres.test_connection.success")
            return True
        except Exception as e:
            log.warning("connector.postgres.test_connection.failed", error=str(e))
            return False
        finally:
            if conn:
                self._put_conn(conn)

    def get_schema(self) -> dict:
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT table_name, column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    ORDER BY table_name, ordinal_position
                    """
                )
                columns_rows = cur.fetchall()

                cur.execute(
                    """
                    SELECT
                        tc.table_name,
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                        AND ccu.table_schema = tc.table_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                        AND tc.table_schema = 'public'
                    """
                )
                fk_rows = cur.fetchall()
        finally:
            self._put_conn(conn)

        schema: dict = {}
        for row in columns_rows:
            table_name = row["table_name"]
            if table_name not in schema:
                schema[table_name] = {
                    "type": "table",
                    "columns": [],
                    "foreign_keys": [],
                    "sample_fields": [],
                }
            schema[table_name]["columns"].append(
                {
                    "name": row["column_name"],
                    "type": row["data_type"],
                    "nullable": row["is_nullable"] == "YES",
                }
            )
            schema[table_name]["sample_fields"].append(row["column_name"])

        for row in fk_rows:
            table_name = row["table_name"]
            if table_name in schema:
                ref = f"{row['foreign_table_name']}.{row['foreign_column_name']}"
                schema[table_name]["foreign_keys"].append(
                    {
                        "column": row["column_name"],
                        "references": ref,
                    }
                )

        log.debug(
            "connector.postgres.get_schema.complete",
            table_count=len(schema),
        )
        return schema

    def execute(self, query: str) -> list[dict]:
        is_safe, reason = _is_safe_query(query)
        if not is_safe:
            raise ValueError(f"Query blocked: {reason}")

        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query)
                rows = cur.fetchmany(200)
                result = [dict(row) for row in rows]
                log.debug("connector.postgres.execute.complete", row_count=len(result))
                return result
        except Exception:
            conn.rollback()
            raise
        finally:
            self._put_conn(conn)
