from atlas.config import Source
from atlas.feeds import NewsItem
from atlas.poller import MAX_POSTS_PER_POLL, Poller

SRC = Source(key="se", name="SE", type="rss", url="https://example.org/feed")


def items(*ids):
    return [NewsItem(id=i, title=f"Item {i}", link=f"https://example.org/{i}") for i in ids]


class Harness:
    def __init__(self, storage):
        self.feed = []
        self.sent = []

        async def fetch(source):
            return list(self.feed)

        async def send(sub, source, item):
            self.sent.append((sub.channel_id, item.id))

        self.poller = Poller(storage, {SRC.key: SRC}, fetch, send)


async def test_first_poll_primes_without_posting(storage):
    h = Harness(storage)
    await storage.subscribe(1, 100, "se", None)
    h.feed = items("b", "a")
    assert await h.poller.poll_all() == 0
    assert h.sent == []
    assert await storage.is_primed("se")


async def test_new_items_posted_oldest_first_to_every_channel(storage):
    h = Harness(storage)
    await storage.subscribe(1, 100, "se", None)
    await storage.subscribe(2, 200, "se", 55)
    h.feed = items("a")
    await h.poller.poll_all()

    h.feed = items("c", "b", "a")
    assert await h.poller.poll_all() == 4
    assert h.sent == [(100, "b"), (100, "c"), (200, "b"), (200, "c")]

    h.sent.clear()
    assert await h.poller.poll_all() == 0


async def test_posts_are_capped_but_all_marked_seen(storage):
    h = Harness(storage)
    await storage.subscribe(1, 100, "se", None)
    h.feed = []
    await h.poller.poll_all()

    ids = [str(i) for i in range(20, 0, -1)]
    h.feed = items(*ids)
    assert await h.poller.poll_all() == MAX_POSTS_PER_POLL
    assert [i for _, i in h.sent] == ["16", "17", "18", "19", "20"]
    assert await storage.unseen("se", ids) == set()


async def test_unsubscribed_sources_are_not_fetched(storage):
    h = Harness(storage)
    calls = []

    async def fetch(source):
        calls.append(source.key)
        return []

    h.poller.fetch = fetch
    await h.poller.poll_all()
    assert calls == []


async def test_failing_source_does_not_break_others(storage):
    other = Source(key="ok", name="OK", type="rss", url="https://example.org/ok")
    sent = []

    async def fetch(source):
        if source.key == "se":
            raise RuntimeError("boom")
        return items("x")

    async def send(sub, source, item):
        sent.append(item.id)

    poller = Poller(storage, {"se": SRC, "ok": other}, fetch, send)
    await storage.subscribe(1, 100, "se", None)
    await storage.subscribe(1, 100, "ok", None)
    await storage.mark_seen("ok", [], prime=True)
    assert await poller.poll_all() == 1
    assert sent == ["x"]
