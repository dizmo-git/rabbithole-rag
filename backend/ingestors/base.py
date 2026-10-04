from abc import ABC, abstractmethod

from backend.models import Chunk


class IngestError(Exception):
    """Ingestion failed for a reason the user should see. routers/sources.ingest_link
    stores the message in Source.error and marks the source "failed", so write it for
    the user ("The site blocks automated access"), not for a log."""


class BaseIngestor(ABC):
    @abstractmethod
    async def ingest(self, url: str, source_id: str) -> list[Chunk]: ...
