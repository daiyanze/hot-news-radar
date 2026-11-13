"""Directory sitemaps fetcher: new tools appearing in AI directories (L2).

Borrowed from new-term-radar's sitemap signal: when several AI tool
directories add a page for the same new tool, that tool is entering
the diffusion layer. Each configured site contributes the tool-page
URLs from its sitemap — newest shards of a sitemap index, or the
most recently modified URLs of a plain urlset.

All directories together count as ONE source for resonance (they
copy each other); the per-directory name is kept in metrics so the
agent can see which directory listed the tool.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from . import common

SM = "{http://www.sitemaps.org/schemas/sitemap/0.9}"

SOURCE = "sitemaps"
LAYER = 2

DEFAULT_SITES = [
    {"name": "futurepedia", "url": "https://www.futurepedia.io/sitemap_tools.xml",
     "pattern": r"/tool/([^/]+)$", "max_age_days": 7},
    {"name": "toolify", "url": "https://www.toolify.ai/sitemap.xml",
     "shard_pattern": r"sitemap_tools_(\d+)\.xml$", "shards_to_read": 1,
     "pattern": r"/tool/([^/]+)/?$"},
    {"name": "dang.ai", "url": "https://dang.ai/sitemap.xml",
     "pattern": r"dang\.ai/([^/]+)$", "skip": r"^(about|advertise|blog|pricing|login|signup)$"},
]


def _slug_name(slug: str) -> str:
    return re.sub(r"[-_]+", " ", slug).strip()


def parse_index(xml_text: str, shard_pattern: str) -> list[str]:
    """Sitemap index -> shard URLs matching the pattern, newest last."""
    root = ET.fromstring(xml_text)
    shards = []
    for node in root.iter(f"{SM}sitemap"):
        loc = node.findtext(f"{SM}loc") or ""
        m = re.search(shard_pattern, loc)
        if m:
            shards.append((int(m.group(1)) if m.groups() else 0, loc))
    shards.sort()
    return [loc for _, loc in shards]


def parse_urlset(xml_text: str, site: dict, now: datetime) -> list[dict]:
    """Pure parser: tool-page URLs from one urlset (unit-tested)."""
    pattern = re.compile(site["pattern"])
    skip = re.compile(site["skip"]) if site.get("skip") else None
    max_age = site.get("max_age_days")
    cutoff = now - timedelta(days=max_age) if max_age else None
    entries = []
    root = ET.fromstring(xml_text)
    for node in root.iter(f"{SM}url"):
        loc = node.findtext(f"{SM}loc") or ""
        m = pattern.search(loc)
        if not m:
            continue
        slug = m.group(1)
        if skip and skip.match(slug):
            continue
        lastmod_raw = node.findtext(f"{SM}lastmod")
        lastmod = None
        if lastmod_raw:
            try:
                lastmod = datetime.fromisoformat(lastmod_raw.replace("Z", "+00:00"))
            except ValueError:
                lastmod = None
        if cutoff and lastmod and lastmod < cutoff:
            continue
        entries.append((lastmod, {
            "source": SOURCE,
            "name": _slug_name(slug),
            "url": loc,
            "metrics": {"directory": site["name"],
                        "lastmod": lastmod.date().isoformat() if lastmod else None},
            "detail": "",
        }))
    entries.sort(key=lambda pair: pair[0] or datetime.min.replace(tzinfo=timezone.utc),
                 reverse=True)
    return [item for _, item in entries[:site.get("limit", 20)]]


def fetch(config: dict, now=None) -> dict:
    now = now or datetime.now(timezone.utc)
    cfg = config.get("sources", {}).get("sitemaps", {})
    sites = cfg.get("sites", DEFAULT_SITES)
    items, failed = [], []
    for site in sites:
        try:
            xml = common.get_text(site["url"])
            root_tag = ET.fromstring(xml).tag
            if root_tag.endswith("sitemapindex"):
                shards = parse_index(xml, site.get("shard_pattern", r"\.xml$"))
                take = site.get("shards_to_read", 1)
                for shard_url in shards[-take:]:
                    items.extend(parse_urlset(common.get_text(shard_url), site, now))
            else:
                items.extend(parse_urlset(xml, site, now))
        except (common.FetchError, ET.ParseError):
            failed.append(site["name"])
    if not items:
        return common.missing(SOURCE, LAYER, f"all sitemaps failed: {', '.join(failed)}")
    note = f"failed sites: {', '.join(failed)}" if failed else ""
    return common.ok(SOURCE, LAYER, items, note)
