from abc import ABC, abstractmethod

from backend.models import Chunk


class IngestError(Exception):
    """Ingestion failed for a reason the user should see. routers/sources.ingest_link
    stores the message in Source.error and marks the source "failed", so write it for
    the user ("The site blocks automated access"), not for a log."""


class BaseIngestor(ABC):
    # A human-readable name for the source (video title, ...) an ingestor may set during
    # ingest(); routers/sources.ingest_link stores it as Source.filename unless the user
    # already renamed the source. None keeps showing the URL.
    title: str | None = None

    @abstractmethod
    async def ingest(self, url: str, source_id: str) -> list[Chunk]: ...
