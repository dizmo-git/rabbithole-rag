from backend.models import Chunk

from backend.ingestors.base import BaseIngestor


class RedditIngestor(BaseIngestor):

    async def ingest(self, url: str, notebook_id: str) -> list[Chunk]:
        print(f"RedditIngestor {url} {notebook_id}")
        return []
