"""Minimal OpenMensa API v2 client (https://docs.openmensa.org/api/v2/)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import aiohttp

from atlas.config import MensaPoint
from atlas.feeds import FETCH_TIMEOUT, USER_AGENT

API = "https://openmensa.org/api/v2"


@dataclass(frozen=True)
class Canteen:
    id: int
    name: str
    city: str = ""
    address: str = ""


@dataclass(frozen=True)
class Meal:
    name: str
    category: str
    student_price: float | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)


def parse_canteens(data: list[dict]) -> list[Canteen]:
    return [
        Canteen(
            id=int(c["id"]),
            name=c.get("name", ""),
            city=c.get("city") or "",
            address=c.get("address") or "",
        )
        for c in data
    ]


def parse_meals(data: list[dict]) -> list[Meal]:
    return [
        Meal(
            name=m.get("name", "").strip(),
            category=(m.get("category") or "Sonstiges").strip(),
            student_price=(m.get("prices") or {}).get("students"),
            notes=tuple(m.get("notes") or ()),
        )
        for m in data
    ]


async def _get_json(session: aiohttp.ClientSession, url: str, params: dict | None = None):
    async with session.get(
        url, params=params, timeout=FETCH_TIMEOUT, headers={"User-Agent": USER_AGENT}
    ) as resp:
        if resp.status == 404:
            return None
        resp.raise_for_status()
        return await resp.json()


async def canteens_near(
    session: aiohttp.ClientSession, points: tuple[MensaPoint, ...], radius_km: float
) -> list[Canteen]:
    found: dict[int, Canteen] = {}
    for p in points:
        data = await _get_json(
            session,
            f"{API}/canteens",
            {"near[lat]": p.lat, "near[lng]": p.lng, "near[dist]": radius_km},
        )
        for c in parse_canteens(data or []):
            found.setdefault(c.id, c)
    return list(found.values())


async def meals(session: aiohttp.ClientSession, canteen_id: int, day: date) -> list[Meal] | None:
    """Meals for a day, or None if OpenMensa has no plan (closed / not published)."""
    data = await _get_json(session, f"{API}/canteens/{canteen_id}/days/{day.isoformat()}/meals")
    return None if data is None else parse_meals(data)
