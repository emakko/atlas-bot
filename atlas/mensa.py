"""Menus of the Studierendenwerk Essen-Duisburg canteens (stw-edu.de)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import aiohttp

from atlas.feeds import FETCH_TIMEOUT, USER_AGENT

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


@dataclass(frozen=True)
class Meal:
    name: str
    category: str
    student_price: float | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)


def parse_menu(html: str, day: date) -> list[Meal]:
    """Extract the meals served on `day` from a stw-edu.de menu page."""
    raise NotImplementedError("needs the real page structure")


async def fetch_menu(session: aiohttp.ClientSession, campus: Campus, day: date) -> list[Meal]:
    async with session.get(
        campus.url, timeout=FETCH_TIMEOUT, headers={"User-Agent": USER_AGENT}
    ) as resp:
        resp.raise_for_status()
        html = await resp.text(errors="replace")
    return parse_menu(html, day)
