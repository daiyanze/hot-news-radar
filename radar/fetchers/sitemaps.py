"""Directory sitemaps fetcher: new tools appearing in AI directories (L2).

Borrowed from new-term-radar's sitemap signal: when several AI tool
directories add a page for the same new tool, that tool is entering
the diffusion layer.

Since 0.5.0 the signal is a snapshot diff, not a lastmod window: the
fetcher keeps every tool-page URL it has seen per directory in
`state/sitemap-seen.json` and only reports URLs that were not in the
previous snapshot — so the same tool is never reported twice. The
first run for a directory only builds its baseline and reports
nothing for it (named in the result note).

All directories together count as ONE source for resonance (they
copy each other); the per-directory name is kept in metrics so the
agent can see which directory listed the tool.
"""

from __future__ import annotations

import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote

from . import common

SM = "{http://www.sitemaps.org/schemas/sitemap/0.9}"

SOURCE = "sitemaps"
LAYER = 2

# URLs that vanished from a directory are forgotten after this long,
# so state files stay bounded.
RETENTION_DAYS = 90

DEFAULT_SITES = [
    {"name": "futurepedia", "url": "https://www.futurepedia.io/sitemap_tools.xml",
     "pattern": r"/tool/([^/]+)$", "max_age_days": 7},
    {"name": "toolify", "url": "https://www.toolify.ai/sitemap.xml",
     "shard_pattern": r"sitemap_tools_(\d+)\.xml$", "shards_to_read": 1,
     "pattern": r"toolify\.ai/tool/([^/]+)/?$"},
    {"name": "dang.ai", "url": "https://dang.ai/sitemap.xml",
     "pattern": r"dang\.ai/([^/]+)$", "skip": r"^(about|advertise|blog|pricing|login|signup)$"},
]


def _slug_name(slug: str) -> str:
    return re.sub(r"[-_/]+", " ", unquote(slug)).strip()


def parse_index(xml_text: str, shard_pattern: str) -> list[str]:
    """Sitemap index -> shard URLs matching the pattern.

    A numeric capture group sorts shards by that number (newest
    last); without one, document order is kept (named sections).
    """
    root = ET.fromstring(xml_text)
    entries = []
    for idx, node in enumerate(root.iter(f"{SM}sitemap")):
        loc = node.findtext(f"{SM}loc") or ""
        m = re.search(shard_pattern, loc)
        if not m:
            continue
        key = int(m.group(1)) if m.groups() and m.group(1).isdigit() else None
        entries.append((key, idx, loc))
    if entries and all(key is not None for key, _, _ in entries):
        entries.sort(key=lambda e: (e[0], e[1]))
    return [loc for _, _, loc in entries]


def parse_urlset(xml_text: str, site: dict, now: datetime,
                 cap: bool = True) -> list[dict]:
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
            if lastmod is not None and lastmod.tzinfo is None:
                lastmod = lastmod.replace(tzinfo=timezone.utc)
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
    items = [item for _, item in entries]
    return items[:site.get("limit", 20)] if cap else items


def diff_items(items: list[dict], seen: dict, now: datetime):
    """Snapshot diff (pure, unit-tested).

    `seen` maps URL -> first-seen date (ISO). Returns
    (fresh_items, updated_seen, baseline): on a site's first run
    (empty `seen`) everything is recorded and nothing is reported.
    URLs absent from the current snapshot are dropped once they are
    older than RETENTION_DAYS.
    """
    baseline = not seen
    today = now.date().isoformat()
    updated = dict(seen)
    fresh = []
    for item in items:
        url = item["url"]
        if url not in updated:
            updated[url] = today
            if not baseline:
                fresh.append(item)
    current = {item["url"] for item in items}
    horizon = (now - timedelta(days=RETENTION_DAYS)).date().isoformat()
    updated = {url: first for url, first in updated.items()
               if url in current or first >= horizon}
    return fresh, updated, baseline


def _load_state(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_state(path: str, state: dict) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=1, sort_keys=True)


def _site_items(site: dict, now: datetime) -> list[dict]:
    xml = common.get_text(site["url"])
    root_tag = ET.fromstring(xml).tag
    if not root_tag.endswith("sitemapindex"):
        return parse_urlset(xml, site, now, cap=False)
    patterns = site.get("shard_patterns") or [site.get("shard_pattern", r"\.xml$")]
    take = site.get("shards_to_read", 1)
    items = []
    for pattern in patterns:
        for shard_url in parse_index(xml, pattern)[-take:]:
            items.extend(parse_urlset(common.get_text(shard_url), site, now,
                                      cap=False))
    return items


def fetch(config: dict, now=None) -> dict:
    now = now or datetime.now(timezone.utc)
    cfg = config.get("sources", {}).get("sitemaps", {})
    sites = cfg.get("sites", DEFAULT_SITES)
    state_path = cfg.get("state_file", "state/sitemap-seen.json")
    state = _load_state(state_path)
    items, failed, baselines, succeeded = [], [], [], 0
    for site in sites:
        try:
            collected = _site_items(site, now)
        except (common.FetchError, ET.ParseError):
            failed.append(site["name"])
            continue
        succeeded += 1
        fresh, updated, baseline = diff_items(
            collected, state.get(site["name"], {}), now)
        state[site["name"]] = updated
        if baseline:
            baselines.append(f"{site['name']}({len(updated)})")
        items.extend(fresh[:site.get("limit", 20)])
    if succeeded:
        _save_state(state_path, state)
    notes = []
    if failed:
        notes.append(f"failed sites: {', '.join(failed)}")
    if baselines:
        notes.append(f"baseline built (first run, nothing reported): "
                     f"{', '.join(baselines)}")
    if not succeeded:
        return common.missing(SOURCE, LAYER,
                              f"all sitemaps failed: {', '.join(failed)}")
    return common.ok(SOURCE, LAYER, items, "; ".join(notes))
