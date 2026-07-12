from abc import ABC, abstractmethod

from backend.models import Chunk


class BaseIngestor(ABC):
    @abstractmethod
    async def ingest(self, url: str, notebook_id: str) -> list[Chunk]: ...
