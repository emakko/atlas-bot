"""Fetching and parsing news items from RSS feeds and plain web pages."""

from __future__ import annotations

import calendar
import hashlib
import html
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urldefrag, urljoin

import aiohttp
import feedparser

from atlas.config import Source

USER_AGENT = "AtlasBot/0.1 (+https://github.com/emakko/atlas-bot)"
FETCH_TIMEOUT = aiohttp.ClientTimeout(total=20)
SUMMARY_LIMIT = 300

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class NewsItem:
    id: str
    title: str
    link: str
    summary: str = ""
    published: datetime | None = None


def clean_text(value: str, limit: int | None = None) -> str:
    text = _WS_RE.sub(" ", html.unescape(_TAG_RE.sub(" ", value or ""))).strip()
    if limit and len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text


def _item_id(*parts: str) -> str:
    return hashlib.sha1("\x1f".join(parts).encode()).hexdigest()


def parse_rss(content: bytes) -> list[NewsItem]:
    """Parse an RSS/Atom document. Items are returned in feed order (newest first)."""
    feed = feedparser.parse(content)
    items: list[NewsItem] = []
    for entry in feed.entries:
        title = clean_text(entry.get("title", ""))
        link = entry.get("link", "")
        if not title and not link:
            continue
        struct = entry.get("published_parsed") or entry.get("updated_parsed")
        published = (
            datetime.fromtimestamp(calendar.timegm(struct), tz=timezone.utc) if struct else None
        )
        items.append(
            NewsItem(
                id=entry.get("id") or link or _item_id(title),
                title=title or link,
                link=link,
                summary=clean_text(entry.get("summary", ""), SUMMARY_LIMIT),
                published=published,
            )
        )
    return items


class _LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            self.links.append((self._href, "".join(self._text)))
            self._href = None


def parse_html_links(
    content: str,
    base_url: str,
    link_pattern: str | None = None,
    min_title_len: int = 15,
) -> list[NewsItem]:
    """Treat links on a news overview page as news items, in page order.

    Navigation links are filtered out by requiring a minimum link-text length and,
    optionally, a URL regex. The page itself and duplicate URLs are skipped.
    """
    collector = _LinkCollector()
    collector.feed(content)

    pattern = re.compile(link_pattern) if link_pattern else None
    page_url = urldefrag(base_url).url.rstrip("/")
    seen: set[str] = set()
    items: list[NewsItem] = []
    for href, text in collector.links:
        if not href or href.startswith(("mailto:", "javascript:", "tel:", "#")):
            continue
        url = urldefrag(urljoin(base_url, href.strip())).url
        if not url.startswith(("http://", "https://")) or url.rstrip("/") == page_url:
            continue
        title = clean_text(text)
        if len(title) < min_title_len:
            continue
        if pattern and not pattern.search(url):
            continue
        if url in seen:
            continue
        seen.add(url)
        items.append(NewsItem(id=url, title=title, link=url))
    return items


def matches_keywords(item: NewsItem, keywords: tuple[str, ...]) -> bool:
    if not keywords:
        return True
    haystack = f"{item.title} {item.summary}".casefold()
    return any(k.casefold() in haystack for k in keywords)


async def fetch_items(session: aiohttp.ClientSession, source: Source) -> list[NewsItem]:
    """Download a source and return its (keyword-filtered) items, newest first."""
    async with session.get(
        source.url, timeout=FETCH_TIMEOUT, headers={"User-Agent": USER_AGENT}
    ) as resp:
        resp.raise_for_status()
        if source.type == "rss":
            items = parse_rss(await resp.read())
        else:
            text = await resp.text(errors="replace")
            items = parse_html_links(
                text, str(resp.url), source.link_pattern, source.min_title_len
            )
    return [i for i in items if matches_keywords(i, source.keywords)]
