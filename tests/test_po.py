from pathlib import Path

import pytest

from atlas.cogs.links import po_embed
from atlas.config import load_catalog

ROOT = Path(__file__).resolve().parents[1]


def test_bundled_po_documents():
    catalog = load_catalog(ROOT / "sources.yaml")
    assert set(catalog.po_documents) == {"new", "old"}
    assert catalog.po_documents["new"].url.endswith("mhb_ws_26_27_po_2026.pdf")
    assert catalog.po_documents["old"].url.endswith("8-34-5-ws23.pdf")
    assert catalog.po_overview == "https://www.uni-due.de/bmse/bsc-ordnungen.php"


def test_po_embed_both_versions_by_default():
    catalog = load_catalog(ROOT / "sources.yaml")
    embed = po_embed(catalog)
    assert [f.name for f in embed.fields] == ["Neu", "Alt"]
    assert "mhb_ws_26_27_po_2026.pdf" in embed.fields[0].value
    assert "bsc-ordnungen.php" in embed.description


def test_po_embed_single_version():
    catalog = load_catalog(ROOT / "sources.yaml")
    embed = po_embed(catalog, "old")
    assert [f.name for f in embed.fields] == ["Alt"]
    assert "8-34-5-ws23.pdf" in embed.fields[0].value


def test_po_embed_missing_config(tmp_path):
    f = tmp_path / "s.yaml"
    f.write_text("sources: []\n")
    embed = po_embed(load_catalog(f), "new")
    assert embed.fields[0].value == "Not configured." and embed.description is None


def test_unknown_po_version_rejected(tmp_path):
    f = tmp_path / "s.yaml"
    f.write_text("po:\n  documents:\n    newest: {name: X, url: 'https://x'}\n")
    with pytest.raises(ValueError, match="unknown version"):
        load_catalog(f)
