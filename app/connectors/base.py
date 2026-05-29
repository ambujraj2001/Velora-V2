from abc import ABC, abstractmethod


class BaseConnector(ABC):
    @abstractmethod
    def test_connection(self) -> bool:
        pass

    @abstractmethod
    def get_schema(self) -> dict:
        pass

    @abstractmethod
    def execute(self, query: str) -> list[dict]:
        pass
