"""Menus of the Studierendenwerk Essen-Duisburg canteens (stw-edu.de)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import aiohttp
from bs4 import BeautifulSoup, Tag

from atlas.feeds import FETCH_TIMEOUT, USER_AGENT, clean_text

MENU_URL = "https://www.stw-edu.de/gastronomie/speisen/"


@dataclass(frozen=True)
class Campus:
    label: str
    ort: str

    @property
    def url(self) -> str:
        return f"{MENU_URL}?ort={self.ort}"


CAMPUSES: dict[str, Campus] = {
    "essen": Campus(label="Mensa Campus Essen", ort="mensa-campus-essen"),
    "duisburg": Campus(label="Mensa Campus Duisburg", ort="mensa-campus-duisburg"),
}

# Diet tags come from the article's `mensa_type-<slug>` CSS classes.
DIET_LABELS = {
    "vegan": "🌱 vegan",
    "vegetarisch": "🥕 vegetarisch",
    "mit-fisch": "🐟 Fisch",
    "mit-gefluegel": "🐔 Geflügel",
    "mit-rindfleisch": "🐄 Rind",
    "mit-schweinefleisch": "🐖 Schwein",
    "mit-lammfleisch": "🐑 Lamm",
    "mit-alkohol": "🍷 Alkohol",
}

_PRICE_RE = re.compile(r"(\d+),(\d{2})\s*€")
_CODES_RE = re.compile(r"^\(([^()]*)\)$")


@dataclass(frozen=True)
class Meal:
    name: str
    category: str
    student_price: float | None = None
    other_price: float | None = None
    diet: tuple[str, ...] = ()
    codes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Menu:
    date_label: str | None
    meals: list[Meal]
    week_pdfs: dict[str, str]


def parse_price(text: str) -> float | None:
    match = _PRICE_RE.search(text)
    return float(f"{match.group(1)}.{match.group(2)}") if match else None


def _parse_article(article: Tag) -> Meal | None:
    name_tag = article.find("h2")
    if name_tag is None:
        return None
    name = clean_text(name_tag.get_text())

    # All labels of a dish card are `.elementor-heading-title` elements, in page
    # order: counter, name, additive/allergen codes, "Stud.", price, "Nicht-Stud.",
    # price, then the collapsed nutrition/allergen/score details.
    texts = [clean_text(t.get_text()) for t in article.select(".elementor-heading-title")]
    category = texts[0] if texts and texts[0] != name else "Sonstiges"

    student_price = other_price = None
    codes: list[str] = []
    for i, text in enumerate(texts):
        if text.rstrip(".") == "Stud" and i + 1 < len(texts):
            student_price = parse_price(texts[i + 1])
        elif text.rstrip(".") == "Nicht-Stud" and i + 1 < len(texts):
            other_price = parse_price(texts[i + 1])
            break
        elif match := _CODES_RE.match(text):
            codes.extend(c.strip() for c in match.group(1).split(",") if c.strip())

    diet: list[str] = []
    for el in [article, *article.find_all(class_=re.compile(r"^mensa_type-"))]:
        for cls in el.get("class", []):
            if cls.startswith("mensa_type-"):
                slug = cls.removeprefix("mensa_type-")
                label = DIET_LABELS.get(slug, slug.replace("-", " "))
                if label not in diet:
                    diet.append(label)

    return Meal(
        name=name,
        category=category,
        student_price=student_price,
        other_price=other_price,
        diet=tuple(diet),
        codes=tuple(codes),
    )


def parse_menu(html: str) -> Menu:
    """Parse the dishes shown on a stw-edu.de menu page (the page's current day)."""
    soup = BeautifulSoup(html, "html.parser")

    date_label = None
    date_select = soup.find("select", attrs={"aria-label": "Datum"})
    if date_select is not None:
        selected = date_select.find("option", selected=True)
        if selected is not None and selected.get("value"):
            date_label = clean_text(selected["value"])

    meals = [m for a in soup.select("article.speisen-grid__item") if (m := _parse_article(a))]

    week_pdfs = {}
    for key, label in (("cfg-link-diese-woche", "diese Woche"), ("cfg-link-naechste-woche", "nächste Woche")):
        tag = soup.find(id=key)
        if tag is not None and (url := tag.get_text(strip=True)):
            week_pdfs[label] = url

    return Menu(date_label=date_label, meals=meals, week_pdfs=week_pdfs)


async def fetch_menu(session: aiohttp.ClientSession, campus: Campus) -> Menu:
    async with session.get(
        campus.url, timeout=FETCH_TIMEOUT, headers={"User-Agent": USER_AGENT}
    ) as resp:
        resp.raise_for_status()
        html = await resp.text(errors="replace")
    return parse_menu(html)
