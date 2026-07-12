from urllib.parse import urlparse

from backend.ingestors.base import BaseIngestor
from backend.ingestors.generic_url import GenericURLIngestor
from backend.ingestors.hn import HNIngestor
from backend.ingestors.reddit import RedditIngestor

INGESTOR_REGISTRY: dict[str, type[BaseIngestor]] = {
    "hn": HNIngestor,
    "reddit": RedditIngestor,
    "generic_url": GenericURLIngestor,
}


def get_ingestor(url: str) -> BaseIngestor:
    source_type = detect_source_type(url)
    ingestor_cls = INGESTOR_REGISTRY.get(source_type, GenericURLIngestor)
    return ingestor_cls()


def detect_source_type(url: str) -> str:
    host = urlparse(url).netloc.lower()

    if "news.ycombinator.com" in host:
        return "hn"
    if "reddit.com" in host:
        return "reddit"
    if "twitter.com" in host or "x.com" in host:
        return "twitter"

    return "generic_url"
