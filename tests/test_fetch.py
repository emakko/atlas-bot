import aiohttp
from aiohttp import web
from aiohttp.test_utils import TestServer

from atlas.config import Source
from atlas.feeds import fetch_items

from tests.test_feeds import PAGE, RSS


async def test_fetch_rss_and_html_over_http():
    app = web.Application()
    app.router.add_get("/feed.rss", lambda r: web.Response(body=RSS, content_type="application/rss+xml"))
    app.router.add_get("/informatik/news_archiv", lambda r: web.Response(text=PAGE, content_type="text/html"))

    async with TestServer(app) as server, aiohttp.ClientSession() as session:
        base = str(server.make_url("")).rstrip("/")
        rss = Source(key="r", name="R", type="rss", url=f"{base}/feed.rss", keywords=("paluno",))
        page = Source(
            key="h", name="H", type="html", url=f"{base}/informatik/news_archiv",
            link_pattern=r"/informatik/news/", min_title_len=20,
        )
        rss_items = await fetch_items(session, rss)
        html_items = await fetch_items(session, page)

    assert [i.title for i in rss_items] == ["Neues Software-Labor für Studierende"]
    assert [i.link for i in html_items] == [
        f"{base}/informatik/news/2026-09-21-hackathon",
        "https://www.uni-due.de/informatik/news/2026-09-10-preis",
    ]
