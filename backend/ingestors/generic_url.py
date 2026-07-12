from backend.models import Chunk

from backend.ingestors.base import BaseIngestor


class GenericURLIngestor(BaseIngestor):

    async def ingest(self, url: str, notebook_id: str) -> list[Chunk]:
        print(f"GenericURLIngestor {url} {notebook_id}")
        return []
