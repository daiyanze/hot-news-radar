"""tripple-signals: static site generator (P1).

Reads structured editions from ``editions/YYYY-MM-DD-{pilot,morning,evening}.json``
(the single source of truth; the chat report is rendered from the same file)
and generates a dependency-free static site under ``site/``:

  site/index.html            latest edition, full text
  site/editions/<slug>.html  one permanent page per edition
  site/archive.html          every edition, newest first
  site/feed.xml              RSS 2.0, one item per edition, full text in content:encoded
  site/atom.xml              Atom 1.0, same content
  site/style.css             minimal newspaper styling, no JS

Stdlib only. Base URL defaults to the GitHub Pages address from ROADMAP.md
and can be overridden with --base-url (changing domain later = one flag).

Usage:
    python -m radar.publish [--base-url https://example.com/tripple-signals]
"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EDITIONS_DIR = ROOT / "editions"
OUT_DIR = ROOT / "site"
ASSETS_DIR = ROOT / "assets"
# Brand files copied verbatim into the generated site root.
BRAND_FILES = ("favicon.svg", "favicon-32.png", "apple-touch-icon.png", "banner.png")
DEFAULT_BASE_URL = "https://daiyanze.github.io/tripple-signals"

SLOT_ORDER = {"pilot": 0, "morning": 1, "evening": 2}
LEVEL_LABEL = {"must": "🔥 必看", "watch": "👀 关注", "seed": "🌱 苗头"}
LEVEL_ORDER = {"must": 0, "watch": 1, "seed": 2}


def slug_of(edition: dict) -> str:
    return f"{edition['date']}-{edition['slot']}"


def edition_url(base_url: str, edition: dict) -> str:
    return f"{base_url.rstrip('/')}/editions/{slug_of(edition)}.html"


def parse_published_at(value: str) -> datetime:
    return datetime.fromisoformat(value)


def load_editions(editions_dir: Path = EDITIONS_DIR) -> list[dict]:
    editions = []
    for path in sorted(editions_dir.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            edition = json.load(f)
        edition["_path"] = path
        editions.append(edition)
    editions.sort(key=lambda e: (e["date"], SLOT_ORDER.get(e["slot"], 9)))
    return editions


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def item_html(item: dict) -> str:
    parts = [f"<h3>{esc(item['title'])}</h3>", f"<p>{esc(item['body'])}</p>"]
    if item.get("unverified"):
        parts.append(f"<p class=\"caveat\">⚠️ 未核实：{esc(item['unverified'])}</p>")
    if item.get("sources"):
        parts.append(f"<p class=\"sources\">来源：{esc('、'.join(item['sources']))}</p>")
    if item.get("links"):
        links = " · ".join(
            f"<a href=\"{esc(url)}\">{esc(url)}</a>" for url in item["links"]
        )
        parts.append(f"<p class=\"sources\">链接：{links}</p>")
    if item.get("action"):
        parts.append(f"<p class=\"action\">建议动作：{esc(item['action'])}</p>")
    return "\n".join(parts)


def edition_body_html(edition: dict, base_url: str) -> str:
    items = sorted(edition["items"], key=lambda i: LEVEL_ORDER.get(i["level"], 9))
    sections: list[str] = []
    current_level = None
    for item in items:
        label = LEVEL_LABEL.get(item["level"], item["level"])
        if item["level"] != current_level:
            if current_level is not None:
                sections.append("</section>")
            sections.append(f"<section><h2>{esc(label)}</h2>")
            current_level = item["level"]
        badge = " 🆕" if item.get("is_new") else ""
        body_parts = item_html(item).split("\n")
        # item_html() starts with the <h3> title line; add the 🆕 badge there.
        body_parts[0] = body_parts[0].replace("</h3>", f"{badge}</h3>", 1)
        sections.append("<article>" + "\n".join(body_parts) + "</article>")
    if current_level is not None:
        sections.append("</section>")
    if edition.get("updates"):
        sections.append("<section><h2>📈 老话题状态</h2><ul>" + "".join(
            f"<li>{esc(u)}</li>" for u in edition["updates"]) + "</ul></section>")
    if edition.get("pending_checks"):
        sections.append("<section><h2>待核查</h2><ul>" + "".join(
            f"<li>{esc(u)}</li>" for u in edition["pending_checks"]) + "</ul></section>")
    if edition.get("missing"):
        sections.append("<section><h2>⚠️ 本期缺失</h2><ul>" + "".join(
            f"<li>{esc(u)}</li>" for u in edition["missing"]) + "</ul></section>")
    return "\n".join(sections)


CSS = """body{font-family:Georgia,'Songti SC','Noto Serif CJK SC',serif;max-width:720px;margin:0 auto;padding:24px 16px;color:#1a1a1a;background:#fdfbf7;line-height:1.7}
a{color:#1a5fb4}h1{font-size:1.6em;border-bottom:2px solid #1a1a1a;padding-bottom:8px}
h2{font-size:1.2em;margin-top:1.8em}h3{font-size:1.05em;margin-bottom:.2em}
.meta{color:#666;font-size:.9em}.sources{color:#666;font-size:.9em}
.action{color:#444}.caveat{color:#8a5a00;background:#fff4d6;padding:6px 10px}
nav{margin:16px 0;font-size:.95em}article{margin-bottom:1.6em}
footer{margin-top:48px;border-top:1px solid #ccc;padding-top:12px;color:#666;font-size:.85em}
"""

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — tripple-signals</title>
<link rel="icon" type="image/svg+xml" href="{asset_prefix}favicon.svg">
<link rel="icon" type="image/png" sizes="32x32" href="{asset_prefix}favicon-32.png">
<link rel="apple-touch-icon" href="{asset_prefix}apple-touch-icon.png">
<meta property="og:title" content="tripple-signals">
<meta property="og:description" content="全网热点信号 · 多源共振才算热点">
<meta property="og:image" content="{base_url}/banner.png">
<link rel="stylesheet" href="{css_path}">
<link rel="alternate" type="application/rss+xml" title="tripple-signals" href="{base_url}/feed.xml">
<link rel="alternate" type="application/atom+xml" title="tripple-signals" href="{base_url}/atom.xml">
</head>
<body>
<header><h1><img src="{asset_prefix}favicon.svg" alt="" style="height:1.2em;vertical-align:-0.24em;margin-right:.3em"><a href="{base_url}/" style="color:inherit;text-decoration:none">tripple-signals</a></h1>
<p class="meta">全网热点信号 · 可用 RSS / Atom 订阅</p></header>
<nav><a href="{base_url}/">最新一期</a> · <a href="{base_url}/archive.html">归档</a> · <a href="{base_url}/feed.xml">RSS</a> · <a href="{base_url}/atom.xml">Atom</a></nav>
<main>
<h1>{title}</h1>
<p class="meta">{published}</p>
{body}
</main>
<footer>tripple-signals · 每期报告由 agent 扫描 + 判断生成；数字均带出处，未核实处如实标注。</footer>
</body>
</html>
"""


def render_page(title: str, published: str, body: str, base_url: str, css_path: str) -> str:
    asset_prefix = css_path[: -len("style.css")] if css_path.endswith("style.css") else ""
    return PAGE_TEMPLATE.format(
        title=esc(title), published=esc(published), body=body,
        base_url=base_url.rstrip("/"), css_path=css_path, asset_prefix=asset_prefix)


def rfc2822(value: str) -> str:
    return format_datetime(parse_published_at(value).astimezone(timezone.utc))


def cdata(text: str) -> str:
    return "<![CDATA[" + text.replace("]]>", "]]]]><![CDATA[>") + "]]>"


def build_rss(editions: list[dict], base_url: str) -> str:
    items = []
    for edition in reversed(editions):
        url = edition_url(base_url, edition)
        content = edition_body_html(edition, base_url)
        items.append(
            "<item>\n"
            f"<title>{esc(edition['title'])} {esc(edition['date'])}</title>\n"
            f"<link>{esc(url)}</link>\n"
            f"<guid isPermaLink=\"true\">{esc(url)}</guid>\n"
            f"<pubDate>{rfc2822(edition['published_at'])}</pubDate>\n"
            f"<description>{esc(edition['title'])}</description>\n"
            f"<content:encoded>{cdata(content)}</content:encoded>\n"
            "</item>"
        )
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<rss version=\"2.0\" xmlns:content=\"http://purl.org/rss/1.0/modules/content/\">\n"
        "<channel>\n"
        "<title>tripple-signals</title>\n"
        f"<link>{esc(base_url.rstrip('/'))}/</link>\n"
        "<description>全网热点信号</description>\n"
        "<language>zh-CN</language>\n" + "\n".join(items) + "\n</channel>\n</rss>\n"
    )


def build_atom(editions: list[dict], base_url: str) -> str:
    entries = []
    for edition in reversed(editions):
        url = edition_url(base_url, edition)
        updated = parse_published_at(edition["published_at"]).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        content = edition_body_html(edition, base_url)
        entries.append(
            "<entry>\n"
            f"<title>{esc(edition['title'])} {esc(edition['date'])}</title>\n"
            f"<link href=\"{esc(url)}\"/>\n"
            f"<id>{esc(url)}</id>\n"
            f"<updated>{esc(updated)}</updated>\n"
            f"<content type=\"html\">{esc(content)}</content>\n"
            "</entry>"
        )
    latest = max(parse_published_at(e["published_at"]) for e in editions).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<feed xmlns=\"http://www.w3.org/2005/Atom\">\n"
        "<title>tripple-signals</title>\n"
        f"<link href=\"{esc(base_url.rstrip('/'))}/\"/>\n"
        f"<link rel=\"self\" href=\"{esc(base_url.rstrip('/'))}/atom.xml\"/>\n"
        f"<id>{esc(base_url.rstrip('/'))}/</id>\n"
        f"<updated>{esc(latest)}</updated>\n" + "\n".join(entries) + "\n</feed>\n"
    )


def build(base_url: str, out_dir: Path = OUT_DIR,
          editions_dir: Path = EDITIONS_DIR) -> list[Path]:
    editions = load_editions(editions_dir)
    if not editions:
        raise SystemExit("no editions found in editions/")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "editions").mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    def write(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        written.append(path)

    def write_bytes(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        written.append(path)

    write(out_dir / "style.css", CSS)
    for name in BRAND_FILES:
        src = ASSETS_DIR / name
        if src.exists():
            write_bytes(out_dir / name, src.read_bytes())
    latest = editions[-1]
    for edition in editions:
        slug = slug_of(edition)
        published = parse_published_at(edition["published_at"]).strftime("%Y-%m-%d %H:%M JST")
        page = render_page(
            edition["title"], published,
            edition_body_html(edition, base_url), base_url, "../style.css")
        write(out_dir / "editions" / f"{slug}.html", page)

    latest_published = parse_published_at(latest["published_at"]).strftime("%Y-%m-%d %H:%M JST")
    index_body = edition_body_html(latest, base_url)
    index_body += "<hr><p><a href=\"archive.html\">查看全部归档 →</a></p>"
    write(out_dir / "index.html", render_page(
        latest["title"], latest_published, index_body, base_url, "style.css"))

    archive_items = "".join(
        f"<li><a href=\"editions/{slug_of(e)}.html\">{esc(e['title'])} {esc(e['date'])}</a> "
        f"<span class=\"meta\">{esc(e['published_at'])}</span></li>"
        for e in reversed(editions)
    )
    write(out_dir / "archive.html", render_page(
        "归档", f"共 {len(editions)} 期",
        f"<ul>{archive_items}</ul>", base_url, "style.css"))

    write(out_dir / "feed.xml", build_rss(editions, base_url))
    write(out_dir / "atom.xml", build_atom(editions, base_url))
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the tripple-signals static site.")
    parser.add_argument("--base-url", default=os.environ.get("TRIPPLE_SIGNALS_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--out", default=str(OUT_DIR))
    args = parser.parse_args(argv)
    written = build(args.base_url, Path(args.out))
    for path in written:
        print(f"wrote {path.relative_to(ROOT)}")
    print(f"{len(written)} files, {len(load_editions())} editions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
