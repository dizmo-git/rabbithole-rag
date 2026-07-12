import asyncio
import html
import re
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import requests
from concurrent.futures import ThreadPoolExecutor

from backend.models import Chunk, Platform, PostOrigin, SourceType
from backend.ingestors.base import BaseIngestor

BASE_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"
MAX_WORKERS = 10


class HNIngestor(BaseIngestor):

    async def ingest(self, url: str, source_id: str) -> list[Chunk]:
        parsed = urlparse(url)
        root_id = parse_qs(parsed.query)["id"][0]

        loop = asyncio.get_running_loop()
        tree = await loop.run_in_executor(
            None, self.fetch_tree, root_id
        )  # blocking, keep off the event loop

        if tree is None:
            return []

        return self.flatten_tree(tree, [], source_id)

    def fetch_item(self, item_id: str):
        resp = requests.get(BASE_URL.format(item_id), timeout=5)
        resp.raise_for_status()
        return resp.json()

    def fetch_tree(self, item_id: str):
        item = self.fetch_item(item_id)
        if item is None:
            return None

        kids = item.get("kids", [])
        if kids:
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                children = list(executor.map(self.fetch_tree, kids))
            item["children"] = [c for c in children if c is not None]

        return item

    def flatten_tree(
        self, node: dict, ancestor_ids: list[str], source_id: str
    ) -> list[Chunk]:
        chunks: list[Chunk] = []

        raw_text = node.get("text") or node.get("title") or ""
        text = html.unescape(re.sub(r"<[^>]+>", " ", raw_text)).strip()

        this_id = None
        if (
            text
        ):  # dead/deleted nodes have no text - skip the chunk, still walk their kids
            this_id = str(uuid4())
            chunks.append(
                Chunk(
                    id=this_id,
                    source_id=source_id,
                    source_type=SourceType.POST,
                    chunk_index=0,  # one chunk per HN item for now
                    content=text,
                    origin=PostOrigin(
                        platform=Platform.HN,
                        external_id=str(node["id"]),
                        author=node.get("by"),
                        origin_date=datetime.fromtimestamp(
                            node["time"], tz=timezone.utc
                        ),
                        permalink=f"https://news.ycombinator.com/item?id={node['id']}",
                        ancestor_ids=ancestor_ids,
                    ),
                )
            )

        next_ancestors = ancestor_ids + [this_id] if this_id else ancestor_ids
        for child in node.get("children", []):
            chunks.extend(self.flatten_tree(child, next_ancestors, source_id))

        return chunks
