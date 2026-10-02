"""
Telegram public channel ingestor.

Scrapes the web preview at https://t.me/s/<channel>, so no API key or account is
needed. That page renders ~20 posts per request (oldest first); older pages come from
?before=<smallest post id on the current page>. Channels with the preview disabled (and
missing ones) answer with a 302 to t.me/<channel> instead.

Channel posts are a timeline, not a reply tree, and vary wildly in size, so instead of
the one-chunk-per-post rule HN/Bluesky use, posts are chunked adaptively:

  0. article continuations: Telegram caps a text post at 4096 chars, so long articles
     get published as several posts in a row. A post right after one that is near the
     limit continues it, and the parts are merged back into one article,
  1. tiny / media-only posts right after another post get glued onto that post
     ("👆", a photo with no caption, an emoji reaction to your own post),
  2. long posts (and replies to an earlier fetched post) stand alone; anything longer
     than MAX_CHUNK_CHARS is split like file sources are,
  3. short consecutive posts are grouped while they're close in time, small enough,
     and - if the semantic gate is on - about the same topic according to embeddings.

The knobs for these rules live in a ChunkingProfile. There's one per ChunkingStyle:
"dense" (default, essay/analysis channels) and "news" (rapid headline feeds), picked
per source via the `style` param of /sources/addlink/.

Replies keep thread structure: the reply's chunk gets the parent post's chunk in
ancestor_ids, so routers/query.py (get_thread_ancestors / build_context) pulls the parent
in as "[forum thread]" context exactly like for HN/Bluesky.

Every chunk records the posts it covers in PostOrigin.permalinks, which is what lets
citations link back to each original post (per piece, when a unit gets split).
"""

import asyncio
import math
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from urllib.parse import urlparse
from uuid import uuid4

import requests
from bs4 import BeautifulSoup, Tag
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.ingestors.base import BaseIngestor
from backend.models import Chunk, Platform, PostOrigin, SourceType

# --- fetching ---------------------------------------------------------------------
HOSTS = {"t.me", "www.t.me", "telegram.me", "www.telegram.me"}
PREVIEW_URL = "https://t.me/s/{}"
DEFAULT_MAX_POSTS = 200  # used when the upload request doesn't say how many posts
MAX_POSTS_LIMIT = 2000  # hard cap, also enforced by the /sources/addlink/ query param
REQUEST_DELAY = 1.0  # seconds between page requests, t.me rate limits with 429s
REQUEST_TIMEOUT = 10
MAX_RETRIES = 2  # retries per page on 429, after that we keep what we already have
MAX_RETRY_WAIT = 60  # cap on a Retry-After we're willing to sleep through
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)

# Public usernames: 5-32 chars, letter first (a few legacy 4-char ones exist).
CHANNEL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{3,31}$")
# First path segments on t.me that are not channels (invites, private links, ...).
RESERVED_PATHS = {
    "joinchat", "c", "addstickers", "addemoji", "addlist", "addtheme", "share",
    "proxy", "socks", "login", "iv", "setlanguage", "boost", "contact", "invoice",
}

# --- chunking --------------------------------------------------------------------
# All lengths count embeddable text only (body, link previews, files, polls), not the
# header line or "[Photo]"-style placeholders.


class ChunkingStyle(str, Enum):
    DENSE = "dense"  # essays / analysis: few, long posts, short posts are follow-ups
    NEWS = "news"  # rapid feeds: many short unrelated headlines, each its own story


@dataclass(frozen=True)
class ChunkingProfile:
    """Per-channel-style knobs. Meant to be exposed as frontend options later."""

    # rule 0, article continuation: a post continues the previous one when that one's
    # body is near Telegram's 4096-char cap. Time alone isn't enough - Analityka_Kush
    # posts unrelated long articles 30s apart, but split parts are always 3994-4406
    # chars and the part after a shorter post never continues it.
    continuation_min_chars: int = 3500  # previous post body at least this long...
    continuation_gap_min: float = 2  # ...and this post at most this many minutes later

    # rule 1, attaching: posts with no letters at all (emoji, bare photo) always attach
    # to the previous post if close enough; short text posts only if attach_short_text.
    tiny_chars: int = 40  # "short text" threshold for attach_short_text
    attach_gap_min: float = 10  # max minutes after the previous post to attach
    attach_short_text: bool = True  # dense: "Continued below 👇" is a follow-up;
    # news: "NDX = ALL-TIME HIGH" is its own headline, so False there

    # rule 2: posts at least this long always get their own chunk
    standalone_chars: int = 600

    # rule 3, grouping short posts
    max_group_gap_min: float = 30  # max minutes between consecutive posts in one group
    max_group_posts: int = 6
    group_target_chars: int = 1200  # stop growing a group past this (< MAX_CHUNK_CHARS)
    semantic_grouping: bool = True  # also needs the global SEMANTIC_GROUPING switch
    semantic_threshold: float = 0.2  # min centred cosine(post, group centroid) to join


PROFILES: dict[ChunkingStyle, ChunkingProfile] = {
    ChunkingStyle.DENSE: ChunkingProfile(),
    ChunkingStyle.NEWS: ChunkingProfile(attach_short_text=False),
}
DEFAULT_STYLE = ChunkingStyle.DENSE

# Not style-dependent:
MAX_CHUNK_CHARS = 1800  # same splitter settings as chroma.chunk_and_save for files
CHUNK_OVERLAP = 250
REPLY_SNIPPET_CHARS = 150

# Semantic gate for grouping. Costs one extra local embedding pass over short posts, so
# this global switch is the hardware kill switch: False -> every profile groups by
# time + length only.
#
# Raw cosine is useless here: posts from one channel share language and style, so with
# nomic-embed-text even unrelated news items score 0.72-0.91. The vectors are therefore
# mean-centred (the average of the fetched posts is subtracted) before comparing, which
# strips the shared "channel" direction. Measured on nexta_live/meduzalive: same-story
# pairs 0.21-0.53, unrelated neighbours -0.23..0.19 (mean -0.05). nomic's "clustering: "
# prefix made no difference, so posts are embedded as-is.
SEMANTIC_GROUPING = True
SEMANTIC_DEBUG = False  # print every "semantic #a -> #b: score" comparison (for tuning)
MIN_SEMANTIC_POSTS = 10  # fewer candidates than this -> the mean is meaningless, gate off
EMBED_BATCH = 64


def is_telegram_url(url: str) -> bool:
    return _host(url) in HOSTS


def parse_url(url: str) -> tuple[str, int | None]:
    """Return (channel, anchor post id or None). Raises ValueError for anything that is
    not a public channel or channel post link (invites, private t.me/c/ links, ...).

    Accepted: t.me/<ch>, t.me/s/<ch>, t.me/<ch>/<id>, t.me/s/<ch>/<id> (also on
    telegram.me, with or without scheme; query strings like ?single are ignored).
    """
    if not is_telegram_url(url):
        raise ValueError(f"Not a Telegram URL: {url}")

    parts = [p for p in urlparse(_with_scheme(url)).path.split("/") if p]
    if parts and parts[0] == "s":
        parts = parts[1:]

    if not parts or len(parts) > 2:
        raise ValueError(f"Not a Telegram channel or post URL: {url}")
    channel = parts[0]
    if channel.lower() in RESERVED_PATHS or not CHANNEL_RE.match(channel):
        raise ValueError(f"Not a public Telegram channel: {url}")
    if len(parts) == 2:
        if not parts[1].isdigit():
            raise ValueError(f"Not a Telegram post URL: {url}")
        return channel, int(parts[1])
    return channel, None


def _with_scheme(url: str) -> str:
    return url if "://" in url else f"https://{url}"


def _host(url: str) -> str:
    return urlparse(_with_scheme(url.strip())).netloc.lower()


@dataclass
class TgPost:
    id: int
    channel: str
    permalink: str
    date: datetime  # UTC
    author: str | None  # post signature, else the channel title
    text: str = ""
    forwarded_from: str | None = None
    reply_to_id: int | None = None  # only for replies to a post in the same channel
    reply_snippet: str | None = None
    attachments: list[str] = field(default_factory=list)  # embeddable: links, files, polls
    media: list[str] = field(default_factory=list)  # placeholders: "Photo", "Album: 3 items"
    continues_previous: bool = False  # set by group_posts: next part of a split article

    @property
    def content_len(self) -> int:
        return len(self.text) + sum(len(a) for a in self.attachments)

    @property
    def wordless(self) -> bool:
        """No letters at all: emoji-only, "+", a bare photo/video..."""
        return not any(ch.isalpha() for ch in self.embed_text())

    def embed_text(self) -> str:
        """Just the content, for the semantic gate (no header/placeholders)."""
        return "\n".join([self.text] + self.attachments).strip()

    def header(self) -> str:
        return f"[@{self.channel}/{self.id} · {self.date:%Y-%m-%d %H:%M} UTC]"

    def render(self) -> str:
        """The text that ends up in the chunk. The header keeps post id and date visible
        to the LLM, e.g.:

        [@durov/510 · 2026-05-10 18:42 UTC]
        Forwarded from Some Channel
        In reply to: "first 150 chars of the parent…"
        <body>
        [Album: 2 items]
        [Link (Meduza): title. description]

        Article continuations render without header/forward/reply lines, so the merged
        parts read as one text.
        """
        lines = []
        if not self.continues_previous:
            lines.append(self.header())
            if self.forwarded_from:
                lines.append(f"Forwarded from {self.forwarded_from}")
            if self.reply_snippet:
                lines.append(f'In reply to: "{self.reply_snippet}"')
        if self.text:
            lines.append(self.text)
        if self.media:
            lines.append(" ".join(f"[{m}]" for m in self.media))
        lines += [f"[{a}]" for a in self.attachments]
        return "\n".join(lines)


@dataclass
class Unit:
    """A run of posts that will become one chunk (or several, if it's too long)."""

    posts: list[TgPost]
    closed: bool  # standalone units take no more posts, except attachments/continuations
    vectors: list[list[float]] = field(default_factory=list)  # for the semantic centroid

    @property
    def chars(self) -> int:
        return sum(p.content_len for p in self.posts)


class TelegramIngestor(BaseIngestor):

    def __init__(
        self, max_posts: int = DEFAULT_MAX_POSTS, style: ChunkingStyle = DEFAULT_STYLE
    ):
        self.max_posts = max(1, min(max_posts, MAX_POSTS_LIMIT))
        self.style = style
        self.profile = PROFILES[style]
        self.stats: Counter[str] = Counter()

    async def ingest(self, url: str, source_id: str) -> list[Chunk]:
        self.stats = Counter()
        channel, anchor_id = parse_url(url)

        loop = asyncio.get_running_loop()
        posts = await loop.run_in_executor(
            None, self.fetch_posts, channel, anchor_id
        )  # blocking, keep off the event loop
        if not posts:
            print(f"TelegramIngestor: no posts fetched for {url}")
            return []

        self.mark_continuations(posts)  # before embedding, continuations need no vector
        vectors = await self.embed_candidates(posts)
        units = self.group_posts(posts, vectors)
        chunks = self.build_chunks(units, source_id)

        s = self.stats
        print(
            f"TelegramIngestor: @{channel} {len(posts)} posts "
            f"(#{posts[0].id}..#{posts[-1].id}) -> {len(chunks)} chunks | "
            f"style {self.style.value} | continued {s['continued']}, grouped {s['grouped']}, "
            f"attached {s['attached']}, dropped {s['dropped']}, split {s['split']} | "
            f"semantic {'on' if vectors is not None else 'off'}"
        )
        return chunks

    # --- fetching -----------------------------------------------------------------

    def fetch_posts(self, channel: str, anchor_id: int | None) -> list[TgPost]:
        """Page backwards from the newest post (or from anchor_id, inclusive) until we
        have max_posts posts or the channel runs out. Returns them oldest first."""
        posts: dict[int, TgPost] = {}
        before = anchor_id + 1 if anchor_id is not None else None
        first = True

        while len(posts) < self.max_posts:
            if not first:
                time.sleep(REQUEST_DELAY)
            first = False

            html = self.fetch_page(channel, before)
            if html is None:
                break
            page = self.parse_page(html)
            new = [
                p for p in page
                if p.id not in posts and (before is None or p.id < before)
            ]
            if not new:  # reached the start of the channel
                break
            posts.update((p.id, p) for p in new)
            before = min(p.id for p in new)
            if before <= 1:
                break

        # the last page can overshoot, keep the newest max_posts (closest to the anchor)
        newest = sorted(posts.values(), key=lambda p: p.id, reverse=True)
        return sorted(newest[: self.max_posts], key=lambda p: p.id)

    def fetch_page(self, channel: str, before: int | None) -> str | None:
        params = {"before": before} if before else None
        for attempt in range(MAX_RETRIES + 1):
            resp = requests.get(
                PREVIEW_URL.format(channel),
                params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=REQUEST_TIMEOUT,
                allow_redirects=False,
            )
            if resp.status_code == 429:
                if attempt == MAX_RETRIES:
                    print("TelegramIngestor: still rate limited, keeping what we have")
                    return None
                wait = self.retry_after(resp)
                print(f"TelegramIngestor: rate limited, retrying in {wait}s")
                time.sleep(wait)
                continue
            if resp.is_redirect:
                print(
                    f"TelegramIngestor: t.me/s/{channel} redirects - the channel doesn't "
                    "exist, is private, or has its web preview disabled"
                )
                return None
            resp.raise_for_status()
            return resp.text
        return None

    def retry_after(self, resp: requests.Response) -> int:
        try:
            return min(int(resp.headers.get("Retry-After", 5)), MAX_RETRY_WAIT)
        except ValueError:
            return 5

    # --- parsing ------------------------------------------------------------------

    def parse_page(self, html: str) -> list[TgPost]:
        soup = BeautifulSoup(html, "html.parser")
        title = soup.select_one(".tgme_channel_info_header_title")
        channel_title = title.get_text(strip=True) if title else None

        posts = []
        for msg in soup.select("div.tgme_widget_message[data-post]"):
            post = self.parse_message(msg, channel_title)
            if post:
                posts.append(post)
        return posts

    def parse_message(self, msg: Tag, channel_title: str | None) -> TgPost | None:
        channel, _, post_id = str(msg["data-post"]).rpartition("/")
        date_link = msg.select_one("a.tgme_widget_message_date")
        time_el = date_link.select_one("time[datetime]") if date_link else None
        if not post_id.isdigit() or date_link is None or time_el is None:
            return None  # not a regular post

        signature = msg.select_one(".tgme_widget_message_from_author")
        post = TgPost(
            id=int(post_id),
            channel=channel,
            permalink=str(date_link["href"]),
            date=datetime.fromisoformat(str(time_el["datetime"])).astimezone(timezone.utc),
            author=signature.get_text(strip=True) if signature else channel_title,
        )

        # `js-message_text` matters: a reply preview inside the same message has its own
        # `.tgme_widget_message_text`, marked `js-message_reply_text` instead.
        body = msg.select_one(".tgme_widget_message_text.js-message_text")
        if body:
            post.text = self.element_text(body)

        fwd = msg.select_one(".tgme_widget_message_forwarded_from")
        if fwd:
            name = fwd.select_one(".tgme_widget_message_forwarded_from_name")
            post.forwarded_from = (
                name.get_text(strip=True) if name
                else fwd.get_text(" ", strip=True).removeprefix("Forwarded from").strip()
            ) or None

        reply = msg.select_one("a.tgme_widget_message_reply")
        if reply:
            snippet = reply.select_one(".js-message_reply_text")
            if snippet:
                text = snippet.get_text(" ", strip=True)
                if len(text) > REPLY_SNIPPET_CHARS:
                    text = text[:REPLY_SNIPPET_CHARS].rstrip() + "…"
                post.reply_snippet = text or None
            # href is t.me/<channel>/<id>; replies to other channels can't be linked up
            parts = urlparse(str(reply.get("href", ""))).path.strip("/").split("/")
            if len(parts) == 2 and parts[0].lower() == channel.lower() and parts[1].isdigit():
                post.reply_to_id = int(parts[1])

        post.attachments = self.parse_attachments(msg)
        post.media = self.parse_media(msg)
        return post

    def element_text(self, el: Tag) -> str:
        for br in el.find_all("br"):
            br.replace_with("\n")
        text = el.get_text()
        return re.sub(r"\n{3,}", "\n\n", text).strip()

    def parse_attachments(self, msg: Tag) -> list[str]:
        """Attachments that carry text worth embedding."""
        out = []
        for lp in msg.select("a.tgme_widget_message_link_preview"):
            site = self.text_of(lp, ".link_preview_site_name")
            title = self.text_of(lp, ".link_preview_title")
            desc = self.text_of(lp, ".link_preview_description")
            body = ". ".join(p for p in (title, desc) if p)
            if body:
                out.append(f"Link ({site}): {body}" if site else f"Link: {body}")

        for doc in msg.select(".tgme_widget_message_document"):
            title = self.text_of(doc, ".tgme_widget_message_document_title")
            extra = self.text_of(doc, ".tgme_widget_message_document_extra")
            if title:
                out.append(f"File: {title} ({extra})" if extra else f"File: {title}")

        # not seen in the sampled channels, selectors are best-effort
        for poll in msg.select(".tgme_widget_message_poll"):
            question = self.text_of(poll, ".tgme_widget_message_poll_question")
            options = [
                o.get_text(strip=True)
                for o in poll.select(".tgme_widget_message_poll_option_text")
            ]
            if question:
                out.append(f"Poll: {question}" + (f" Options: {'; '.join(options)}" if options else ""))
        return out

    def parse_media(self, msg: Tag) -> list[str]:
        """Placeholders for media we can't read. Albums are a single message on t.me/s,
        their extra items are why post ids skip numbers."""
        album = msg.select_one(".tgme_widget_message_grouped_wrap")
        if album:
            return [f"Album: {len(album.select('.grouped_media_wrap'))} items"]
        labels = [
            (".tgme_widget_message_photo_wrap", "Photo"),
            (".tgme_widget_message_video_player", "Video"),
            (".tgme_widget_message_roundvideo_player", "Video message"),
            (".tgme_widget_message_voice", "Voice message"),
            (".tgme_widget_message_sticker_wrap", "Sticker"),
        ]
        return [label for sel, label in labels if msg.select_one(sel)]

    def text_of(self, el: Tag, selector: str) -> str:
        found = el.select_one(selector)
        return found.get_text(" ", strip=True) if found else ""

    # --- chunking -----------------------------------------------------------------

    def mark_continuations(self, posts: list[TgPost]) -> None:
        """Rule 0: flag posts that continue a split article (see ChunkingProfile).
        Runs before embedding so continuation parts don't get embedded for nothing."""
        prof = self.profile
        for prev, post in zip(posts, posts[1:]):
            if (
                len(prev.text) >= prof.continuation_min_chars
                and minutes_between(prev.date, post.date) <= prof.continuation_gap_min
                and post.content_len > 0
                and post.reply_to_id is None  # a reply is its own message, not a part
                and post.reply_snippet is None
            ):
                post.continues_previous = True

    async def embed_candidates(self, posts: list[TgPost]) -> dict[int, list[float]] | None:
        """Embed the posts that can reach rule 3 (short posts with real text) and
        mean-centre them (see SEMANTIC_GROUPING). Returns None when the gate is off, there
        are too few posts, or embedding failed -> grouping by time + length only."""
        prof = self.profile
        if not (SEMANTIC_GROUPING and prof.semantic_grouping):
            return None
        candidates = [
            p for p in posts
            if not p.continues_previous
            and not p.wordless
            and 0 < p.content_len < prof.standalone_chars
        ]
        if len(candidates) < MIN_SEMANTIC_POSTS:
            print(
                f"TelegramIngestor: only {len(candidates)} short posts, too few for the "
                "semantic gate, grouping by time + length only"
            )
            return None

        # imported here: backend.chroma opens the Chroma client on import
        from backend.chroma import embeddings

        texts = [p.embed_text() for p in candidates]
        loop = asyncio.get_running_loop()
        vectors: list[list[float]] = []
        try:
            for i in range(0, len(texts), EMBED_BATCH):
                batch = texts[i : i + EMBED_BATCH]
                vectors += await loop.run_in_executor(None, embeddings.embed_documents, batch)
        except Exception as e:
            print(f"TelegramIngestor: embedding failed ({e}), grouping by time + length only")
            return None

        mean = centroid(vectors)
        return {
            p.id: [x - m for x, m in zip(v, mean)] for p, v in zip(candidates, vectors)
        }

    def group_posts(
        self, posts: list[TgPost], vectors: dict[int, list[float]] | None
    ) -> list[Unit]:
        """Pass 1: chronological posts -> units. See the module docstring for the rules.
        Expects mark_continuations() to have run."""
        prof = self.profile
        fetched = {p.id for p in posts}
        units: list[Unit] = []

        for post in posts:
            prev = units[-1] if units else None
            gap = minutes_between(prev.posts[-1].date, post.date) if prev else None

            # rule 0: next part of a split article -> back into the article's unit.
            # The part before it is long, so it's always the last post of units[-1].
            if post.continues_previous and prev:
                prev.posts.append(post)
                prev.closed = True
                self.stats["continued"] += 1
                continue

            # rule 1: wordless follow-ups (and, in dense channels, short ones) stick to
            # whatever came right before
            attachable = post.wordless or (
                prof.attach_short_text and post.content_len < prof.tiny_chars
            )
            if attachable:
                if prev and gap is not None and gap <= prof.attach_gap_min:
                    prev.posts.append(post)
                    self.stats["attached"] += 1
                    continue
                if post.content_len == 0:  # nothing to embed, nothing to attach to
                    self.stats["dropped"] += 1
                    continue
                # has some text but no neighbour: treated as a short post below

            # rule 2: long posts and in-range replies stand alone (replies get the
            # parent's chunk as ancestor in build_chunks)
            if post.content_len >= prof.standalone_chars or post.reply_to_id in fetched:
                units.append(Unit([post], closed=True))
                continue

            # rule 3: short posts group up while time / size / topic allow it
            vec = vectors.get(post.id) if vectors else None
            if prev and not prev.closed and gap is not None and self.can_join(prev, post, gap, vec):
                prev.posts.append(post)
                if vec:
                    prev.vectors.append(vec)
                self.stats["grouped"] += 1
            else:
                units.append(Unit([post], closed=False, vectors=[vec] if vec else []))

        return units

    def can_join(self, unit: Unit, post: TgPost, gap: float, vec: list[float] | None) -> bool:
        prof = self.profile
        if gap > prof.max_group_gap_min:
            return False
        if len(unit.posts) >= prof.max_group_posts:
            return False
        if unit.chars + post.content_len > prof.group_target_chars:
            return False
        if vec is not None and unit.vectors:  # semantic gate, vectors are mean-centred
            score = cosine(vec, centroid(unit.vectors))
            if SEMANTIC_DEBUG:
                print(f"TelegramIngestor: semantic #{unit.posts[-1].id} -> #{post.id}: {score:.3f}")
            return score >= prof.semantic_threshold
        return True

    def build_chunks(self, units: list[Unit], source_id: str) -> list[Chunk]:
        """Pass 2: units -> Chunks. Long units are split, and each piece is attributed to
        the posts it actually overlaps (own header, permalink and permalinks), so a piece
        from part 3 of an article cites part 3. Replies get ancestor_ids."""
        chunks: list[Chunk] = []
        first_chunk_of: dict[int, Chunk] = {}  # post id -> first chunk of its unit

        for unit in units:
            lead = unit.posts[0]

            # Posts are processed oldest first, so a parent's chunk always exists already.
            ancestor_ids: list[str] = []
            parent = first_chunk_of.get(lead.reply_to_id) if lead.reply_to_id else None
            if parent and parent.origin:
                ancestor_ids = parent.origin.ancestor_ids + [parent.id]

            # join the rendered posts, remembering where each one sits in the text
            rendered = [p.render() for p in unit.posts]
            spans: list[tuple[int, int]] = []
            pos = 0
            for r in rendered:
                spans.append((pos, pos + len(r)))
                pos += len(r) + 2  # the "\n\n" separator
            text = "\n\n".join(rendered)

            pieces: list[tuple[str, list[TgPost]]] = [(text, unit.posts)]
            if len(text) > MAX_CHUNK_CHARS:
                # leave room for the header line most pieces get prepended below
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=MAX_CHUNK_CHARS - len(lead.header()) - 1,
                    chunk_overlap=CHUNK_OVERLAP,
                    add_start_index=True,
                )
                pieces = []
                for doc in splitter.create_documents([text]):
                    start = doc.metadata.get("start_index", -1)
                    end = start + len(doc.page_content)
                    covered = [
                        p for p, (s, e) in zip(unit.posts, spans) if s < end and e > start
                    ]
                    # start_index is -1 if the splitter couldn't locate the piece
                    pieces.append((doc.page_content, covered if start >= 0 and covered else unit.posts))
                self.stats["split"] += 1

            unit_chunks = []
            for i, (content, covered) in enumerate(pieces):
                first = covered[0]
                # pieces that start mid-post (or in a header-less continuation part) get
                # the header of the post they start in
                if not content.startswith(first.header()):
                    content = f"{first.header()}\n{content}"
                unit_chunks.append(
                    Chunk(
                        id=str(uuid4()),
                        source_id=source_id,
                        source_type=SourceType.POST,
                        chunk_index=i,  # piece of a split unit, 0 otherwise
                        content=content,
                        origin=PostOrigin(
                            platform=Platform.TELEGRAM,
                            external_id=f"{first.channel}/{first.id}",
                            author=first.author,
                            origin_date=first.date,
                            permalink=first.permalink,
                            ancestor_ids=ancestor_ids,
                            permalinks=[p.permalink for p in covered] if len(covered) > 1 else [],
                        ),
                    )
                )
            chunks += unit_chunks
            for p in unit.posts:
                first_chunk_of[p.id] = unit_chunks[0]

        return chunks


def minutes_between(a: datetime, b: datetime) -> float:
    return (b - a).total_seconds() / 60


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def centroid(vectors: list[list[float]]) -> list[float]:
    return [sum(col) / len(vectors) for col in zip(*vectors)]
