from atlas.feeds import NewsItem, clean_text, matches_keywords, parse_html_links, parse_rss

RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>UDE aktuell</title>
<item>
  <title>Neues Software-Labor f&#252;r Studierende</title>
  <link>https://www.uni-due.de/2026-09-20-software-labor</link>
  <guid>https://www.uni-due.de/2026-09-20-software-labor</guid>
  <description>&lt;p&gt;Das &lt;b&gt;paluno&lt;/b&gt; er&#246;ffnet ein Labor.&lt;/p&gt;</description>
  <pubDate>Sun, 20 Sep 2026 10:00:00 +0200</pubDate>
</item>
<item>
  <title>Semesterstart im Oktober</title>
  <link>https://www.uni-due.de/2026-09-18-semesterstart</link>
</item>
</channel></rss>"""

PAGE = """
<html><body>
<nav><a href="/informatik/">Start</a><a href="/informatik/studium">Studium</a></nav>
<main>
  <a href="/informatik/news_archiv">Aktuelle News aus der Fakultät für Informatik</a>
  <a href="/informatik/news/2026-09-21-hackathon">Hackathon der Fakultät für Informatik war ein voller Erfolg</a>
  <a href="https://www.uni-due.de/informatik/news/2026-09-10-preis#top">  Best Paper Award
     für Forschende im Software Engineering </a>
  <a href="/informatik/news/2026-09-21-hackathon">Hackathon der Fakultät für Informatik war ein voller Erfolg</a>
  <a href="https://twitter.com/ude_informatik">Folgen Sie uns auf Twitter für aktuelle News</a>
  <a href="mailto:info@uni-due.de">Schreiben Sie uns eine E-Mail mit Fragen</a>
</main>
</body></html>
"""


def test_parse_rss():
    items = parse_rss(RSS)
    assert [i.title for i in items] == ["Neues Software-Labor für Studierende", "Semesterstart im Oktober"]
    first = items[0]
    assert first.id == "https://www.uni-due.de/2026-09-20-software-labor"
    assert first.summary == "Das paluno eröffnet ein Labor."
    assert first.published is not None and first.published.hour == 8  # UTC
    assert items[1].id == "https://www.uni-due.de/2026-09-18-semesterstart"
    assert items[1].published is None


def test_parse_html_links_filters_navigation_and_duplicates():
    items = parse_html_links(
        PAGE,
        "https://www.uni-due.de/informatik/news_archiv",
        link_pattern=r"^https?://www\.uni-due\.de/informatik/",
        min_title_len=20,
    )
    assert [i.link for i in items] == [
        "https://www.uni-due.de/informatik/news/2026-09-21-hackathon",
        "https://www.uni-due.de/informatik/news/2026-09-10-preis",
    ]
    assert items[1].title == "Best Paper Award für Forschende im Software Engineering"


def test_parse_html_links_without_pattern_keeps_external_links():
    items = parse_html_links(PAGE, "https://www.uni-due.de/informatik/news_archiv", min_title_len=20)
    assert "https://twitter.com/ude_informatik" in [i.link for i in items]
    assert not any(i.link.startswith("mailto:") for i in items)


def test_keywords():
    item = NewsItem(id="1", title="Neues Labor", link="", summary="Das PALUNO eröffnet")
    assert matches_keywords(item, ())
    assert matches_keywords(item, ("paluno",))
    assert not matches_keywords(item, ("Chemie",))


def test_clean_text_truncates():
    assert clean_text("<p>a   b</p>") == "a b"
    assert clean_text("x" * 50, limit=10) == "x" * 9 + "…"
