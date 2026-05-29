from app.connectors.base import BaseConnector
from app.connectors.mongodb import MongoConnector
from app.connectors.postgres import PostgresConnector

CONNECTOR_REGISTRY = {
    "postgres": PostgresConnector,
    "mongodb": MongoConnector,
}


def get_connector(db_type: str, conn_string: str) -> BaseConnector:
    if db_type not in CONNECTOR_REGISTRY:
        raise ValueError(
            f"Unsupported db_type '{db_type}'. "
            f"Supported types: postgres, mongodb"
        )
    return CONNECTOR_REGISTRY[db_type](conn_string)
