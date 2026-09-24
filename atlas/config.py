from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

SOURCE_TYPES = {"rss", "html"}


@dataclass(frozen=True)
class Source:
    key: str
    name: str
    type: str
    url: str
    group: str = "Other"
    keywords: tuple[str, ...] = ()
    link_pattern: str | None = None
    min_title_len: int = 15


@dataclass(frozen=True)
class Link:
    name: str
    url: str


@dataclass(frozen=True)
class Catalog:
    sources: dict[str, Source]
    links: tuple[Link, ...] = ()


@dataclass(frozen=True)
class Settings:
    token: str
    dev_guild_id: int | None
    db_path: Path
    sources_file: Path
    poll_minutes: float = 15.0
    catalog: Catalog = field(default_factory=lambda: Catalog(sources={}))


def load_catalog(path: Path) -> Catalog:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    sources: dict[str, Source] = {}
    for entry in raw.get("sources", []):
        src = Source(
            key=entry["key"],
            name=entry["name"],
            type=entry.get("type", "rss"),
            url=entry["url"],
            group=entry.get("group", "Other"),
            keywords=tuple(entry.get("keywords", ())),
            link_pattern=entry.get("link_pattern"),
            min_title_len=int(entry.get("min_title_len", 15)),
        )
        if src.type not in SOURCE_TYPES:
            raise ValueError(f"source {src.key!r}: unknown type {src.type!r}")
        if src.key in sources:
            raise ValueError(f"duplicate source key {src.key!r}")
        sources[src.key] = src

    links = tuple(Link(name=l["name"], url=l["url"]) for l in raw.get("links", []))
    return Catalog(sources=sources, links=links)


def load_settings() -> Settings:
    token = os.environ.get("DISCORD_TOKEN", "").strip()
    if not token:
        raise SystemExit("DISCORD_TOKEN is not set (see .env.example)")

    dev_guild = os.environ.get("ATLAS_DEV_GUILD_ID", "").strip()
    sources_file = Path(os.environ.get("ATLAS_SOURCES_FILE", "sources.yaml"))
    return Settings(
        token=token,
        dev_guild_id=int(dev_guild) if dev_guild else None,
        db_path=Path(os.environ.get("ATLAS_DB_PATH", "data/atlas.db")),
        sources_file=sources_file,
        poll_minutes=float(os.environ.get("ATLAS_POLL_MINUTES", "15")),
        catalog=load_catalog(sources_file),
    )
