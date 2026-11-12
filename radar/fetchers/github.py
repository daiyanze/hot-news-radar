"""GitHub fetcher: breakout repos via the Search API + Trending page.

Two signals, per the methodology:
- Breakout: repos created within `max_age_days` whose stars/day clears
  the configured bar (search API, exact numbers).
- Trending: today's github.com/trending list with "stars today"
  (HTML scrape, best-effort; failure degrades to the search signal
  alone, it never blocks the source).
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from . import common

SOURCE = "github"
LAYER = 1


def parse_search(payload: dict, now: datetime, cfg: dict) -> list[dict]:
    """Pure parser for the GitHub search response (unit-tested)."""
    max_age = cfg.get("max_age_days", 14)
    min_per_day = cfg.get("min_stars_per_day", 200)
    min_delta = cfg.get("min_stars_delta", 400)
    items = []
    for repo in payload.get("items", []):
        created = datetime.fromisoformat(repo["created_at"].replace("Z", "+00:00"))
        age_days = max((now - created).days, 0)
        stars = repo.get("stargazers_count", 0)
        per_day = stars / max(age_days, 1)
        breakout = age_days <= max_age and (per_day >= min_per_day or stars >= min_delta)
        items.append({
            "source": SOURCE,
            "name": repo["full_name"],
            "url": repo["html_url"],
            "metrics": {"stars": stars, "age_days": age_days,
                        "stars_per_day": round(per_day, 1), "breakout": breakout},
            "detail": repo.get("description") or "",
        })
    return items


def parse_trending(html: str) -> list[dict]:
    """Best-effort parse of github.com/trending (unit-tested)."""
    items = []
    for block in re.findall(r'<article class="Box-row".*?</article>', html, re.S):
        m = re.search(r'href="/([^"/]+/[^"/]+)"', block)
        if not m:
            continue
        stars_today = re.search(r"([\d,]+) stars today", block)
        total = re.search(r'href="/[^"]+/stargazers"[^>]*>\s*([\d,]+)', block)
        items.append({
            "source": SOURCE,
            "name": m.group(1),
            "url": f"https://github.com/{m.group(1)}",
            "metrics": {"stars_today": int(stars_today.group(1).replace(",", "")) if stars_today else None,
                        "stars": int(total.group(1).replace(",", "")) if total else None,
                        "trending": True},
            "detail": "",
        })
    return items


def fetch(config: dict, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    cfg = config.get("sources", {}).get("github", {})
    since = (now - timedelta(days=cfg.get("max_age_days", 14))).date().isoformat()
    query = quote(f"created:>={since} stars:>=50")
    url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=30"
    try:
        payload = common.get_json(url, headers={"Accept": "application/vnd.github+json"})
        items = parse_search(payload, now, cfg)
    except common.FetchError as exc:
        return common.missing(SOURCE, LAYER, str(exc))
    note = ""
    try:
        trending = parse_trending(common.get_text("https://github.com/trending?since=daily"))
        known = {i["name"] for i in items}
        items.extend(t for t in trending if t["name"] not in known)
    except common.FetchError as exc:
        note = f"trending page unavailable ({exc}); search signal only"
    return common.ok(SOURCE, LAYER, items, note)
