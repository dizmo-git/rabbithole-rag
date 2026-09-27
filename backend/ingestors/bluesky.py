import asyncio
from collections import deque
from datetime import datetime
from urllib.parse import urlparse
from uuid import uuid4

import requests

from backend.models import Chunk, Platform, PostOrigin, SourceType
from backend.ingestors.base import BaseIngestor

API_URL = "https://public.api.bsky.app/xrpc/{}"
MAX_REPLIES = 100  # default cap on replies per thread, root and parents not counted
THREAD_DEPTH = 10  # how deep getPostThread returns the reply tree
PARENT_HEIGHT = 20  # ancestors kept when the link points at a reply
REQUEST_TIMEOUT = 10

THREAD_VIEW_POST = "app.bsky.feed.defs#threadViewPost"
EMBED_EXTERNAL = "app.bsky.embed.external#view"
EMBED_IMAGES = "app.bsky.embed.images#view"


class BlueskyIngestor(BaseIngestor):

    def __init__(self, max_replies: int = MAX_REPLIES):
        self.max_replies = max_replies

    async def ingest(self, url: str, source_id: str) -> list[Chunk]:
        loop = asyncio.get_running_loop()
        thread = await loop.run_in_executor(
            None, self.fetch_thread, url
        )  # blocking, keep off the event loop

        if thread.get("$type") != THREAD_VIEW_POST:
            return []  # notFound/blocked root

        return self.flatten_thread(thread, source_id)

    def parse_url(self, url: str) -> tuple[str, str]:
        parts = urlparse(url).path.strip("/").split("/")
        if len(parts) != 4 or parts[0] != "profile" or parts[2] != "post":
            raise ValueError(f"Not a Bluesky post URL: {url}")
        return parts[1], parts[3]

    def resolve_did(self, actor: str) -> str:
        if actor.startswith("did:"):
            return actor
        resp = requests.get(
            API_URL.format("com.atproto.identity.resolveHandle"),
            params={"handle": actor},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()["did"]

    def fetch_thread(self, url: str) -> dict:
        actor, rkey = self.parse_url(url)
        did = self.resolve_did(actor)
        resp = requests.get(
            API_URL.format("app.bsky.feed.getPostThread"),
            params={
                "uri": f"at://{did}/app.bsky.feed.post/{rkey}",
                "depth": THREAD_DEPTH,
                "parentHeight": PARENT_HEIGHT,
            },
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()["thread"]

    def flatten_thread(self, thread: dict, source_id: str) -> list[Chunk]:
        chunks: list[Chunk] = []

        # parents come nearest-first, walk them root-first
        parents = []
        node = thread.get("parent")
        while node and node.get("$type") == THREAD_VIEW_POST:
            parents.append(node)
            node = node.get("parent")
        parents.reverse()

        ancestor_ids: list[str] = []
        for node in parents + [thread]:
            chunk = self.build_chunk(node, ancestor_ids, source_id)
            if chunk:
                chunks.append(chunk)
                ancestor_ids = ancestor_ids + [chunk.id]

        # breadth-first, most liked siblings first, so a cut keeps the top-level discussion
        queue = deque((r, ancestor_ids) for r in self.sorted_replies(thread))
        kept = 0
        while queue and kept < self.max_replies:
            node, node_ancestors = queue.popleft()
            chunk = self.build_chunk(node, node_ancestors, source_id)
            if chunk:  # empty posts are skipped but their replies still walked
                chunks.append(chunk)
                node_ancestors = node_ancestors + [chunk.id]
                kept += 1
            queue.extend((r, node_ancestors) for r in self.sorted_replies(node))

        total = self.count_replies(thread)
        print(f"BlueskyIngestor: kept {kept} of {total} replies for {thread['post']['uri']}")
        return chunks

    def sorted_replies(self, node: dict) -> list[dict]:
        replies = [
            r for r in node.get("replies", []) if r.get("$type") == THREAD_VIEW_POST
        ]
        return sorted(replies, key=lambda r: r["post"].get("likeCount", 0), reverse=True)

    def count_replies(self, node: dict) -> int:
        return sum(1 + self.count_replies(r) for r in self.sorted_replies(node))

    def build_chunk(
        self, node: dict, ancestor_ids: list[str], source_id: str
    ) -> Chunk | None:
        post = node["post"]
        text = self.extract_text(post)
        if not text:
            return None

        record = post.get("record", {})
        author_did = post["author"]["did"]
        rkey = post["uri"].rsplit("/", 1)[-1]

        return Chunk(
            id=str(uuid4()),
            source_id=source_id,
            source_type=SourceType.POST,
            chunk_index=0,  # posts are short, one chunk per post
            content=text,
            origin=PostOrigin(
                platform=Platform.BLUESKY,
                external_id=post["uri"],
                author=post["author"].get("handle"),
                origin_date=datetime.fromisoformat(
                    record.get("createdAt") or post["indexedAt"]
                ),
                permalink=f"https://bsky.app/profile/{author_did}/post/{rkey}",
                ancestor_ids=ancestor_ids,
            ),
        )

    def extract_text(self, post: dict) -> str:
        parts = [post.get("record", {}).get("text", "")]

        embed = post.get("embed") or {}
        if embed.get("$type") == EMBED_EXTERNAL:
            external = embed.get("external", {})
            parts += [external.get("title", ""), external.get("description", "")]
        elif embed.get("$type") == EMBED_IMAGES:
            parts += [img.get("alt", "") for img in embed.get("images", [])]

        return "\n".join(p.strip() for p in parts if p and p.strip())
