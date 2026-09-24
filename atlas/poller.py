"""Polling logic: find new items for subscribed sources and hand them to a sender."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from atlas.config import Source
from atlas.feeds import NewsItem
from atlas.storage import Storage, Subscription

log = logging.getLogger(__name__)

# Upper bound per source and poll, so a page redesign can't flood a channel.
MAX_POSTS_PER_POLL = 5

Fetcher = Callable[[Source], Awaitable[list[NewsItem]]]
Sender = Callable[[Subscription, Source, NewsItem], Awaitable[None]]


class Poller:
    def __init__(
        self,
        storage: Storage,
        sources: dict[str, Source],
        fetch: Fetcher,
        send: Sender,
    ) -> None:
        self.storage = storage
        self.sources = sources
        self.fetch = fetch
        self.send = send

    async def poll_all(self) -> int:
        """Poll every source that has at least one subscription. Returns posts sent."""
        posted = 0
        for key in sorted(await self.storage.subscribed_source_keys()):
            source = self.sources.get(key)
            if source is None:
                log.warning("Subscription references unknown source %r", key)
                continue
            try:
                posted += await self.poll_source(source)
            except Exception:
                log.exception("Polling %s failed", key)
        return posted

    async def poll_source(self, source: Source) -> int:
        items = await self.fetch(source)
        ids = [i.id for i in items]

        # First time we see a source, remember what's there without posting it,
        # so subscribing doesn't dump the whole archive into the channel.
        if not await self.storage.is_primed(source.key):
            await self.storage.mark_seen(source.key, ids, prime=True)
            log.info("Primed %s with %d items", source.key, len(ids))
            return 0

        unseen = await self.storage.unseen(source.key, ids)
        new_items = [i for i in items if i.id in unseen]
        if not new_items:
            return 0

        # Items arrive newest first; post the newest few, oldest of those first.
        to_post = list(reversed(new_items[:MAX_POSTS_PER_POLL]))
        subs = await self.storage.subscriptions(source_key=source.key)
        posted = 0
        for sub in subs:
            for item in to_post:
                try:
                    await self.send(sub, source, item)
                    posted += 1
                except Exception:
                    log.exception("Sending %s to channel %s failed", item.link, sub.channel_id)

        await self.storage.mark_seen(source.key, [i.id for i in new_items])
        return posted
