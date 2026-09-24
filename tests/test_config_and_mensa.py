from pathlib import Path

import pytest

from atlas.cogs.mensa import format_price
from atlas.config import load_catalog
from atlas.mensa import parse_canteens, parse_meals

ROOT = Path(__file__).resolve().parents[1]


def test_bundled_sources_file_is_valid():
    catalog = load_catalog(ROOT / "sources.yaml")
    assert {"paluno", "sse", "informatik", "ude-se"} <= catalog.sources.keys()
    assert catalog.sources["ude-se"].keywords  # SE filter on the central feed
    assert all(s.url.startswith("https://") for s in catalog.sources.values())
    assert catalog.links and catalog.mensa_points


def test_duplicate_keys_rejected(tmp_path):
    f = tmp_path / "s.yaml"
    f.write_text(
        "sources:\n"
        "  - {key: a, name: A, url: 'https://x'}\n"
        "  - {key: a, name: B, url: 'https://y'}\n"
    )
    with pytest.raises(ValueError, match="duplicate"):
        load_catalog(f)


def test_unknown_type_rejected(tmp_path):
    f = tmp_path / "s.yaml"
    f.write_text("sources:\n  - {key: a, name: A, type: json, url: 'https://x'}\n")
    with pytest.raises(ValueError, match="unknown type"):
        load_catalog(f)


def test_parse_openmensa_payloads():
    canteens = parse_canteens([{"id": 42, "name": "Mensa Essen", "city": "Essen", "address": None}])
    assert canteens[0].id == 42 and canteens[0].address == ""

    meals = parse_meals([
        {"id": 1, "name": " Currywurst ", "category": "Grill", "prices": {"students": 3.2}, "notes": ["vegan"]},
        {"id": 2, "name": "Salat", "category": None, "prices": None, "notes": None},
    ])
    assert meals[0].name == "Currywurst" and meals[0].student_price == 3.2
    assert meals[1].category == "Sonstiges" and meals[1].student_price is None
    assert format_price(3.2) == "3,20 €" and format_price(None) == ""
