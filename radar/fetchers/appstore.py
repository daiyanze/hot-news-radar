"""App Store charts fetcher: top-grossing and top-free apps (L2).

Apple's marketing-tools RSS JSON is free and keyless. Charts are a
money signal (new-term-radar reads the top-grossing chart the same
way): an AI app climbing the grossing chart is demand with revenue
attached, not just chatter.
"""

from __future__ import annotations

from . import common

SOURCE = "app_store"
LAYER = 2


def parse(payload: dict, chart: str) -> list[dict]:
    """Pure parser for the Apple charts response (unit-tested)."""
    items = []
    results = (payload.get("feed") or {}).get("results") or []
    for rank, app in enumerate(results, start=1):
        if not app.get("name"):
            continue
        genres = [g.get("name") for g in app.get("genres") or []]
        items.append({
            "source": SOURCE,
            "name": app["name"],
            "url": app.get("url", ""),
            "metrics": {"chart": chart, "rank": rank,
                        "artist": app.get("artistName"), "genres": genres},
            "detail": "",
        })
    return items


LEGACY_CHARTS = {"top-grossing": "topgrossingapplications",
                 "top-free": "topfreeapplications"}


def parse_legacy(payload: dict, chart: str) -> list[dict]:
    """Pure parser for the legacy itunes.apple.com RSS JSON."""
    items = []
    entries = (payload.get("feed") or {}).get("entry") or []
    for rank, app in enumerate(entries, start=1):
        name = ((app.get("im:name") or {}).get("label") or "").strip()
        if not name:
            continue
        link = ""
        for link_obj in app.get("link") or []:
            if isinstance(link_obj, dict):
                link = (link_obj.get("attributes") or {}).get("href") or link
        category = ((app.get("category") or {}).get("attributes") or {}).get("label")
        items.append({
            "source": SOURCE,
            "name": name,
            "url": link,
            "metrics": {"chart": chart, "rank": rank,
                        "artist": ((app.get("im:artist") or {}).get("label")),
                        "genres": [category] if category else []},
            "detail": "",
        })
    return items


def fetch(config: dict, now=None) -> dict:
    cfg = config.get("sources", {}).get("app_store", {})
    country = cfg.get("country", "us")
    limit = cfg.get("limit", 25)
    items, failed, legacy = [], [], []
    for chart in cfg.get("charts", ["top-grossing", "top-free"]):
        url = (f"https://rss.marketingtools.apple.com/api/v2/{country}/apps/"
               f"{chart}/{limit}/apps.json")
        try:
            items.extend(parse(common.get_json(url), chart))
            continue
        except common.FetchError:
            pass
        # The marketing-tools endpoint is flaky (intermittent 502);
        # fall back to the legacy iTunes RSS JSON for the same chart.
        legacy_name = LEGACY_CHARTS.get(chart)
        if legacy_name:
            try:
                payload = common.get_json(
                    f"https://itunes.apple.com/{country}/rss/{legacy_name}/limit={limit}/json")
                items.extend(parse_legacy(payload, chart))
                legacy.append(chart)
                continue
            except common.FetchError:
                pass
        failed.append(chart)
    if not items:
        return common.missing(SOURCE, LAYER, f"all charts failed: {', '.join(failed)}")
    notes = []
    if legacy:
        notes.append(f"via legacy iTunes feed: {', '.join(legacy)}")
    if failed:
        notes.append(f"failed charts: {', '.join(failed)}")
    return common.ok(SOURCE, LAYER, items, "; ".join(notes))
