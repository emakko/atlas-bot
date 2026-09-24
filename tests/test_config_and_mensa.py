from pathlib import Path

import pytest

from atlas.cogs.mensa import format_price
from atlas.config import load_catalog
from atlas.mensa import CAMPUSES

ROOT = Path(__file__).resolve().parents[1]


def test_bundled_sources_file_is_valid():
    catalog = load_catalog(ROOT / "sources.yaml")
    assert {"paluno", "sse", "informatik", "ude-se"} <= catalog.sources.keys()
    assert catalog.sources["ude-se"].keywords  # SE filter on the central feed
    assert all(s.url.startswith("https://") for s in catalog.sources.values())
    assert catalog.links


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


def test_campus_urls():
    assert CAMPUSES["essen"].url == "https://www.stw-edu.de/gastronomie/speisen/?ort=mensa-campus-essen"
    assert CAMPUSES["duisburg"].url == "https://www.stw-edu.de/gastronomie/speisen/?ort=mensa-campus-duisburg"
    assert format_price(3.2) == "3,20 €" and format_price(None) == ""
