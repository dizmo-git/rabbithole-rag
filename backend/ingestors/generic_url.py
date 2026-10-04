"""
Generic web page ingestor, the fallback for any link no platform ingestor claims.

Fetches the page with requests and hands the raw bytes to trafilatura, which finds the
main content (article body, docs text, ...) and drops navigation, menus, sidebars,
footers, cookie banners, scripts and styles. What comes out is plain text, so no HTML
tags or markdown escapes reach the embeddings. That text is split like file sources and
every chunk gets a "[title · host · date]" header, so a chunk from the middle of a long
article still says what it's from.

Pages that only render with JavaScript (Notion, SPAs, docsify) give an empty shell to a
plain fetch. When that happens - less than MIN_TEXT_CHARS of text, or a bot-wall status
like 403 - the page is rendered in a headless browser instead (browser.py, the Edge or
Chrome already installed) and extracted the same way. Most article/news/wiki/docs sites
still send their full HTML, so the browser rarely starts.

Failures raise IngestError with a message for the user; routers/sources.ingest_link
marks the source "failed" and the sidebar shows why. Sites that block headless browsers
too (Medium, Stack Overflow) end up there as "blocks automated access", there is no
stealth/evasion here on purpose.
"""

import asyncio
from datetime import datetime, timezone
from urllib.parse import urlparse
from uuid import uuid4

import requests
import trafilatura
from langchain_text_splitters import RecursiveCharacterTextSplitter
from trafilatura.settings import Document

from backend.ingestors.base import BaseIngestor, IngestError
from backend.models import Chunk, Platform, PostOrigin, SourceType

REQUEST_TIMEOUT = 15
# A descriptive UA, not a fake browser one: Wikipedia answers a spoofed Chrome UA with
# 403 but lets this through, and no other site tried treated the two differently.
# browser.py sends it too.
USER_AGENT = "rabbithole-rag/1.0 (+https://github.com/dizmo-git/rabbithole-rag)"
HTML_TYPES = ("text/html", "application/xhtml+xml")

# Less text than this means a JS shell or a bot-check page, not content. Measured: the
# Notion shell gives 88 chars, Cloudflare's check page 119, real pages thousands.
MIN_TEXT_CHARS = 200
# What plain clients often get from bot walls and JS checks (Cloudflare, ...), where a
# real browser may still get through. Other errors (404, 500, DNS) fail straight away.
BROWSER_RETRY_STATUSES = {401, 403, 429, 503}

# Blog/news comment sections are mostly noise. Tables stay: they hold real data on
# Wikipedia and docs pages. Old table-layout sites (paulgraham.com) still extract, just
# without paragraph breaks. favor_precision was tried and dropped real headings without
# cutting the leftovers it was meant for ("More recent articles" lists).
INCLUDE_COMMENTS = False
INCLUDE_TABLES = True

MAX_CHUNK_CHARS = 1800  # same splitter settings as chroma.chunk_and_save for files
CHUNK_OVERLAP = 250


class RetryInBrowser(IngestError):
    """The plain fetch was refused in a way a real browser might get past."""


def with_scheme(url: str) -> str:
    url = url.strip()
    return url if "://" in url else f"https://{url}"


def is_web_url(url: str) -> bool:
    """http(s) link with a host, also accepted without a scheme ("example.com/post")."""
    url = url.strip()
    if any(ch.isspace() for ch in url):  # "not a url" would parse with host "not a url"
        return False
    parsed = urlparse(with_scheme(url))
    return parsed.scheme in ("http", "https") and bool(parsed.hostname)


def http_error(status: int) -> IngestError:
    """User-facing error for an HTTP error status (also used by browser.py)."""
    if status in (404, 410):
        return IngestError(f"Page not found (HTTP {status})")
    if status in BROWSER_RETRY_STATUSES:
        return RetryInBrowser(f"The site blocks automated access (HTTP {status})")
    return IngestError(f"The site answered with an error (HTTP {status})")


def parse_date(value: str | None) -> datetime | None:
    # trafilatura gives "YYYY-MM-DD"; a bad value must not crash the background task
    try:
        return datetime.fromisoformat(value).replace(tzinfo=timezone.utc) if value else None
    except ValueError:
        return None


def text_len(doc: Document | None) -> int:
    return len((doc.text or "").strip()) if doc else 0


def render_in_browser(url: str) -> tuple[str, bytes, str]:
    # imported here: Playwright is only needed for the rare JS-only page
    try:
        from backend.ingestors.browser import render_page
    except ImportError:
        raise IngestError(
            "This page needs JavaScript to render, and Playwright is not installed "
            "(pip install playwright)"
        )
    return render_page(url)


class GenericURLIngestor(BaseIngestor):

    async def ingest(self, url: str, source_id: str) -> list[Chunk]:
        url = with_scheme(url)
        loop = asyncio.get_running_loop()  # all blocking work below runs in the executor

        how = "plain fetch"
        final_url, doc = url, None
        try:
            final_url, html = await loop.run_in_executor(None, self.fetch_page, url)
            # trafilatura gets the raw bytes and works out the encoding itself (meta
            # charset, then detection). requests' resp.text would fall back to ISO-8859-1
            # when the Content-Type has no charset and garble non-Latin pages.
            doc = await loop.run_in_executor(None, self.extract, html, final_url)
        except RetryInBrowser as e:
            print(f"GenericURLIngestor: {url}: {e}, trying a browser")

        if text_len(doc) < MIN_TEXT_CHARS:
            if doc is not None:
                print(
                    f"GenericURLIngestor: {url} has {text_len(doc)} chars without "
                    "JavaScript, rendering it in a browser"
                )
            final_url, html, browser = await loop.run_in_executor(
                None, render_in_browser, url
            )
            how = f"browser ({browser})"
            doc = await loop.run_in_executor(None, self.extract, html, final_url)
            if doc is None or text_len(doc) < MIN_TEXT_CHARS:
                raise IngestError("No readable text found on this page")

        chunks = self.build_chunks(doc, final_url, source_id)
        print(
            f"GenericURLIngestor: {final_url} -> {len(doc.text)} chars, "
            f"{len(chunks)} chunks via {how} | title {doc.title!r}, date {doc.date}"
        )
        return chunks

    def fetch_page(self, url: str) -> tuple[str, bytes]:
        """Returns (url after redirects, raw HTML). Raises IngestError, or RetryInBrowser
        when a real browser might get through."""
        try:
            # stream: read the headers first, so a link to a PDF or video isn't downloaded
            with requests.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=REQUEST_TIMEOUT,
                stream=True,
            ) as resp:
                if resp.status_code >= 400:
                    raise http_error(resp.status_code)
                content_type = resp.headers.get("Content-Type", "").lower()
                if content_type and not content_type.startswith(HTML_TYPES):
                    raise IngestError(not_a_page_message(content_type))
                return resp.url, resp.content
        except requests.Timeout:  # before ConnectionError: ConnectTimeout is both
            raise IngestError("The site took too long to answer")
        except requests.ConnectionError:
            raise IngestError(f"Could not reach {urlparse(url).hostname}")
        except requests.RequestException as e:
            raise IngestError(f"Could not fetch the page ({type(e).__name__})")

    def extract(self, html: bytes, url: str) -> Document | None:
        return trafilatura.bare_extraction(
            html,
            url=url,
            with_metadata=True,  # title, author, date
            include_comments=INCLUDE_COMMENTS,
            include_tables=INCLUDE_TABLES,
            include_formatting=False,  # markdown mode emits <sup>/<sub> and \[ escapes
            include_links=False,
            include_images=False,
        )

    def build_chunks(self, doc: Document, url: str, source_id: str) -> list[Chunk]:
        host = (urlparse(url).hostname or "").removeprefix("www.")
        # only a date found on the page goes in the header, the fetch time below doesn't
        header = "[" + " · ".join(p for p in (doc.title, host, doc.date) if p) + "]"
        origin_date = parse_date(doc.date) or datetime.now(timezone.utc)

        splitter = RecursiveCharacterTextSplitter(
            # leave room for the header line every piece gets prepended
            chunk_size=MAX_CHUNK_CHARS - len(header) - 1,
            chunk_overlap=CHUNK_OVERLAP,
        )
        return [
            Chunk(
                id=str(uuid4()),
                source_id=source_id,
                source_type=SourceType.POST,
                chunk_index=i,
                content=f"{header}\n{piece}",
                origin=PostOrigin(
                    platform=Platform.WEB,
                    external_id=url,
                    author=doc.author,
                    origin_date=origin_date,  # publication date if found, else fetch time
                    permalink=url,
                    ancestor_ids=[],  # a page is not a thread
                ),
            )
            for i, piece in enumerate(splitter.split_text(doc.text))
        ]


def not_a_page_message(content_type: str) -> str:
    kind = content_type.split(";")[0].strip()
    if kind == "application/pdf":
        return "This link is a PDF, not a web page. Download it and upload it as a file"
    return f"This link points to a {kind} file, not a web page"
