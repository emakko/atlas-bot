from pathlib import Path

import pytest

from atlas.cogs.links import PO_CHOICES, po_embed
from atlas.config import load_catalog

ROOT = Path(__file__).resolve().parents[1]


def test_bundled_po_documents():
    catalog = load_catalog(ROOT / "sources.yaml")
    assert set(catalog.po_documents) == {"new", "old"}
    assert catalog.po_documents["new"].url.endswith("mhb_ws_26_27_po_2026.pdf")
    assert catalog.po_documents["old"].url.endswith("8-34-5-ws23.pdf")


def test_po_choices_match_mensa_style():
    assert [(c.name, c.value) for c in PO_CHOICES] == [("Neu – PO 2026", "new"), ("Alt – PO 2023", "old")]


def test_po_embed_new():
    catalog = load_catalog(ROOT / "sources.yaml")
    embed = po_embed(catalog, "new")
    assert embed.title == "Neu – PO 2026 – B.Sc. Software Engineering"
    assert embed.description == (
        "[PO 2026 – Modulhandbuch WS 26/27]"
        "(https://www.uni-due.de/imperia/md/images/informatik/bmse/mhb_ws_26_27_po_2026.pdf)"
    )
    # Exactly one link: no linked title, no extra fields.
    assert embed.url is None and not embed.fields


def test_po_embed_old():
    catalog = load_catalog(ROOT / "sources.yaml")
    embed = po_embed(catalog, "old")
    assert "8-34-5-ws23.pdf" in embed.description
    assert embed.url is None and not embed.fields


def test_po_embed_missing_config(tmp_path):
    f = tmp_path / "s.yaml"
    f.write_text("sources: []\n")
    embed = po_embed(load_catalog(f), "new")
    assert embed.description == "Not configured." and embed.url is None and not embed.fields


def test_unknown_po_version_rejected(tmp_path):
    f = tmp_path / "s.yaml"
    f.write_text("po:\n  documents:\n    newest: {name: X, url: 'https://x'}\n")
    with pytest.raises(ValueError, match="unknown version"):
        load_catalog(f)
