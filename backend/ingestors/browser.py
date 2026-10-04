"""
Headless browser rendering for pages that need JavaScript (Notion, SPAs, docsify), the
fallback of generic_url.GenericURLIngestor. Only imported when that fallback runs.

Drives the Edge or Chrome already installed through Playwright (channel="msedge" /
"chrome"), so there's no 180-280 MB browser download; Edge ships with every Windows 11.
Playwright's own Chromium is the last resort, it only exists after
`playwright install chromium` (Linux/macOS without Chrome).

Uses Playwright's *sync* API, called through loop.run_in_executor. With --reload on
Windows uvicorn runs the app on a SelectorEventLoop, which can't start subprocesses, so
the async API would fail there; a worker thread gets a fresh default (Proactor) loop.

Every call launches a fresh browser with a throwaway profile (none of the user's cookies)
and the same descriptive User-Agent as the plain fetch. No stealth tricks: sites that
block headless browsers are reported as blocked.
"""

import time

from playwright.sync_api import Browser, Page, Playwright, sync_playwright
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from backend.ingestors.base import IngestError
from backend.ingestors.generic_url import USER_AGENT, http_error

CHANNELS = ("msedge", "chrome", None)  # None = Playwright's own Chromium
GOTO_TIMEOUT_MS = 30_000
# Apps like Notion keep connections open and never go network-idle, so idle is only a
# first wait, then we wait until the page text stops changing. Measured: Notion's text
# appears ~2s after DOMContentLoaded and settles by ~4s, docsify by ~1.5s.
NETWORK_IDLE_TIMEOUT_MS = 5_000
SETTLE_QUIET_S = 1.0  # text length unchanged this long -> done
SETTLE_TIMEOUT_S = 8.0
SETTLE_POLL_MS = 250
# Cloudflare's JS check ("Just a moment..." / "Verification successful. Waiting for ...")
# reloads the page by itself once it passes, give it this long
CHALLENGE_TIMEOUT_MS = 15_000
SKIP_RESOURCES = {"image", "media", "font"}  # not needed for text, saves time

NOT_A_CHECK_PAGE_JS = """() => document.title !== "Just a moment..."
    && !(document.body && document.body.innerText.includes("Verification successful"))"""
TEXT_LEN_JS = "() => document.body ? document.body.innerText.length : 0"


def render_page(url: str) -> tuple[str, bytes, str]:
    """Returns (url after redirects, rendered HTML, browser name). Raises IngestError."""
    with sync_playwright() as p:
        browser, name = launch_browser(p)
        try:
            page = browser.new_context(user_agent=USER_AGENT).new_page()
            page.route(
                "**/*",
                lambda route: route.abort()
                if route.request.resource_type in SKIP_RESOURCES
                else route.continue_(),
            )
            # status of the main document, updated when the page navigates again (e.g.
            # after a bot check), so we judge the page we end up on
            statuses: list[int] = []
            page.on(
                "response",
                lambda r: statuses.append(r.status)
                if r.request.is_navigation_request() and r.frame == page.main_frame
                else None,
            )

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=GOTO_TIMEOUT_MS)
            except PlaywrightTimeout:
                raise IngestError("The page took too long to load")
            except PlaywrightError as e:  # DNS failure, refused connection, ...
                raise IngestError(f"The browser could not open the page ({first_line(e)})")

            wait_until_settled(page)
            if not page.evaluate(NOT_A_CHECK_PAGE_JS):
                try:
                    page.wait_for_function(NOT_A_CHECK_PAGE_JS, timeout=CHALLENGE_TIMEOUT_MS)
                except PlaywrightTimeout:
                    raise IngestError("The site's bot check didn't let the browser through")
                wait_until_settled(page)

            if statuses and statuses[-1] >= 400:
                raise http_error(statuses[-1])
            return page.url, page.content().encode(), name
        finally:
            browser.close()


def launch_browser(p: Playwright) -> tuple[Browser, str]:
    for channel in CHANNELS:
        try:
            return p.chromium.launch(channel=channel, headless=True), channel or "chromium"
        except PlaywrightError:
            continue  # not installed, try the next one
    raise IngestError(
        "This page needs JavaScript to render, and no Edge or Chrome was found. Install "
        "one of them, or run `playwright install chromium`"
    )


def wait_until_settled(page: Page) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=NETWORK_IDLE_TIMEOUT_MS)
    except PlaywrightTimeout:
        pass  # live connections, see NETWORK_IDLE_TIMEOUT_MS

    last, quiet_since = -1, time.monotonic()
    deadline = time.monotonic() + SETTLE_TIMEOUT_S
    while time.monotonic() < deadline:
        try:
            length = page.evaluate(TEXT_LEN_JS)
        except PlaywrightError:  # the page is navigating (bot check reload), keep waiting
            length = -1
        now = time.monotonic()
        if length != last:
            last, quiet_since = length, now
        elif length > 0 and now - quiet_since >= SETTLE_QUIET_S:
            return
        page.wait_for_timeout(SETTLE_POLL_MS)


def first_line(e: Exception) -> str:
    # Playwright errors carry a multi-line call log, the first line is the reason
    return str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__
