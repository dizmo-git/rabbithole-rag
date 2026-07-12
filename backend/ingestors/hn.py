from backend.models import Chunk

from backend.ingestors.base import BaseIngestor


class HNIngestor(BaseIngestor):

    async def ingest(self, url: str, notebook_id: str) -> list[Chunk]:
        print(f"HNIngestor {url} {notebook_id}")
        return []
