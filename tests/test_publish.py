"""Logic tests for radar/publish.py. No network access."""

import json
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from radar import publish

SAMPLE = {
    "date": "2026-11-12",
    "slot": "morning",
    "published_at": "2026-11-12T06:00:00+09:00",
    "title": "热点雷达 · 早报",
    "items": [
        {
            "level": "must",
            "title": "示例模型发布",
            "body": " body with <brackets> & symbols ",
            "action": "值得试。",
            "sources": ["官方"],
            "links": [],
            "is_new": True,
        },
        {
            "level": "seed",
            "title": "小苗头",
            "body": "单源，先记一笔。",
            "action": "仅记录。",
            "sources": ["Product Hunt"],
            "links": [],
            "is_new": True,
        },
    ],
    "updates": ["老话题仍在榜"],
    "missing": ["X 未直读"],
    "pending_checks": [],
}


def _write_edition(tmpdir, edition):
    tmp_path = Path(tmpdir)
    editions_dir = tmp_path / "editions"
    editions_dir.mkdir()
    (editions_dir / "2026-11-12-morning.json").write_text(
        json.dumps(edition, ensure_ascii=False), encoding="utf-8")
    return editions_dir


def test_build_writes_all_outputs():
    tmpdir = tempfile.mkdtemp()
    editions_dir = _write_edition(tmpdir, SAMPLE)
    out_dir = Path(tmpdir) / "site"
    written = publish.build("https://example.com/triple-sigma", out_dir, editions_dir)
    names = {p.relative_to(out_dir).as_posix() for p in written}
    assert names == {
        "style.css", "index.html", "archive.html", "feed.xml", "atom.xml",
        "editions/2026-11-12-morning.html",
        "favicon.svg", "favicon-32.png", "apple-touch-icon.png", "banner.png",
    }
    assert "示例模型发布" in (out_dir / "index.html").read_text(encoding="utf-8")


def test_feeds_parse_and_carry_full_text():
    tmpdir = tempfile.mkdtemp()
    editions_dir = _write_edition(tmpdir, SAMPLE)
    out_dir = Path(tmpdir) / "site"
    publish.build("https://example.com/triple-sigma", out_dir, editions_dir)
    ET.parse(out_dir / "feed.xml")
    ET.parse(out_dir / "atom.xml")
    feed = (out_dir / "feed.xml").read_text(encoding="utf-8")
    assert "示例模型发布" in feed
    assert "https://example.com/triple-sigma/editions/2026-11-12-morning.html" in feed
    assert "&lt;brackets&gt;" in feed  # body is escaped inside CDATA, not raw HTML


def test_edition_page_has_permanent_link_and_caveat():
    tmpdir = tempfile.mkdtemp()
    edition = dict(SAMPLE)
    edition["items"] = [dict(SAMPLE["items"][0], unverified="名字待核实。")]
    editions_dir = _write_edition(tmpdir, edition)
    out_dir = Path(tmpdir) / "site"
    publish.build("https://example.com/triple-sigma", out_dir, editions_dir)
    page = (out_dir / "editions" / "2026-11-12-morning.html").read_text(encoding="utf-8")
    assert "未核实" in page and "名字待核实" in page
    assert "archive.html" in page
