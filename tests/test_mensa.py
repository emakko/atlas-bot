from pathlib import Path

import aiohttp
from aiohttp import web
from aiohttp.test_utils import TestServer

from atlas import mensa
from atlas.cogs.mensa import format_price, menu_embed

FIXTURE = (Path(__file__).parent / "fixtures" / "stw_mensa_duisburg.html").read_text(encoding="utf-8")


def test_campus_urls():
    assert mensa.CAMPUSES["essen"].url == "https://www.stw-edu.de/gastronomie/speisen/?ort=mensa-campus-essen"
    assert mensa.CAMPUSES["duisburg"].url == "https://www.stw-edu.de/gastronomie/speisen/?ort=mensa-campus-duisburg"


def test_parse_menu_meals():
    menu = mensa.parse_menu(FIXTURE)
    assert menu.date_label == "Donnerstag, 24.09.2026"
    assert [m.name for m in menu.meals] == [
        'Spaghetti (Bio) "Bolognese"',
        'Indonesische Reispfanne "Nasi Goreng Style" mit Sprossen, Gemüse und Cashewnüssen',
        "Pommes frites",
        "Pizza Stück nach Angebot des Tages",
    ]

    bolognese, nasi, pommes, pizza = menu.meals
    assert bolognese.category == "Essen 2"
    assert bolognese.student_price == 2.79 and bolognese.other_price == 5.20
    assert bolognese.diet == ("🐄 Rind",)
    assert bolognese.codes == ("age", "awe", "f", "i")

    assert nasi.category == "Vegan"
    assert nasi.diet == ("🌱 vegan",)
    assert nasi.codes == ("1", "2", "age", "awe", "f", "hca", "i")

    assert pommes.codes == () and pommes.student_price == 0.68
    assert pizza.diet == ("🐟 Fisch", "🐔 Geflügel", "🐖 Schwein")


def test_parse_menu_week_pdfs():
    menu = mensa.parse_menu(FIXTURE)
    assert menu.week_pdfs == {
        "diese Woche": "https://www.stw-edu.de/mensadaten/pdf/wochenplaene/duisburg/aktuelle_woche.pdf",
        "nächste Woche": "https://www.stw-edu.de/mensadaten/pdf/wochenplaene/duisburg/naechste_woche.pdf",
    }


def test_parse_empty_page():
    menu = mensa.parse_menu("<html><body><p>Keine Speisen</p></body></html>")
    assert menu.meals == [] and menu.date_label is None and menu.week_pdfs == {}


def test_prices():
    assert mensa.parse_price("2,79 €") == 2.79
    assert mensa.parse_price("kostenlos") is None
    assert format_price(3.2) == "3,20 €" and format_price(None) == ""


def test_menu_embed():
    menu = mensa.parse_menu(FIXTURE)
    embed = menu_embed(mensa.CAMPUSES["duisburg"], menu)
    assert embed.title == "Mensa Campus Duisburg – Donnerstag, 24.09.2026"
    names = [f.name for f in embed.fields]
    assert names == ["Essen 2", "Vegan", "Beilage 1", "Pizza Slice", "Wochenplan (PDF)"]
    assert "**2,79 €**" in embed.fields[0].value


async def test_fetch_menu_over_http(monkeypatch):
    app = web.Application()
    seen = {}

    async def handler(request):
        seen["ort"] = request.query.get("ort")
        return web.Response(text=FIXTURE, content_type="text/html")

    app.router.add_get("/gastronomie/speisen/", handler)
    async with TestServer(app) as server, aiohttp.ClientSession() as session:
        monkeypatch.setattr(mensa, "MENU_URL", str(server.make_url("/gastronomie/speisen/")))
        menu = await mensa.fetch_menu(session, mensa.CAMPUSES["duisburg"])
    assert seen["ort"] == "mensa-campus-duisburg"
    assert len(menu.meals) == 4
