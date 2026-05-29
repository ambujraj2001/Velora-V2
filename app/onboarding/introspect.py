from app.connectors.base import BaseConnector


def introspect(connector: BaseConnector) -> dict:
    return connector.get_schema()
