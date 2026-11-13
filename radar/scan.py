"""Scan orchestration: run all fetchers, group possible cross-source
resonance, persist the candidate file for the agent to judge.

The code gathers and counts; grading stays with the agent (SKILL.md).
Output: state/candidates-<YYYYMMDD>-<edition>.json plus a stdout
summary of per-source status.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from .config import load_config  # re-exported for mcp_server / __main__
from .fetchers import FETCHERS
from .vocab import apply_vocab

__all__ = ["load_config", "run_scan", "summary_lines", "resonance_groups",
           "apply_controls", "topic_weights", "item_time", "tokens"]

STOPWORDS = {"the", "a", "an", "of", "for", "to", "in", "on", "with", "and",
             "launches", "launch", "releases", "release", "announces", "new",
             "ai", "llm", "model", "models", "using", "show", "hn",
             # function words and generic verbs/nouns that headline
             # titles share without naming the same thing — with more
             # sources feeding the grouper (0.3.0), these produced
             # hundreds of junk "resonance" groups
             "how", "what", "why", "when", "where", "which", "who", "whom",
             "this", "that", "these", "those", "there", "here", "your",
             "you", "are", "was", "were", "has", "have", "had", "its",
             "it", "can", "could", "will", "would", "should", "may",
             "might", "must", "from", "into", "over", "under", "after",
             "before", "about", "than", "then", "now", "just", "more",
             "most", "other", "others", "some", "any", "all", "each",
             "get", "gets", "got", "make", "makes", "made", "build",
             "builds", "built", "building", "use", "uses", "used",
             "way", "ways", "thing", "things", "world", "today", "day",
             "week", "year", "years", "time", "people", "work", "works",
             "first", "one", "two", "three", "out", "off", "per",
             "via", "vs", "app", "apps", "tool", "tools", "free",
             "best", "top", "big", "yet", "still", "even", "also",
             "not", "no", "yes", "but", "if", "so", "as", "at", "by"}

# A token shared by more items than this is a theme, not a name.
MAX_TOKEN_ITEMS = 12

# The candidate file is read by an agent; keep only the strongest
# groups (most sources first) instead of hundreds of weak ones.
MAX_GROUPS = 60


def tokens(name: str) -> set[str]:
    words = re.findall(r"[a-z0-9][a-z0-9.\-]{2,}", name.lower())
    return {w.strip(".-") for w in words if w not in STOPWORDS}


def resonance_groups(results: list[dict]) -> list[dict]:
    """Group candidates from >=2 sources sharing a distinctive token.

    Deliberately naive: it surfaces *possible* resonance for the agent
    to confirm, it does not decide that two items are the same topic.
    """
    by_token: dict[str, list[dict]] = {}
    for result in results:
        for item in result["items"]:
            for tok in tokens(item["name"]):
                by_token.setdefault(tok, []).append(item)
    groups, seen = [], set()
    for tok, items in by_token.items():
        sources = {i["source"] for i in items}
        if len(sources) < 2 or len(items) > MAX_TOKEN_ITEMS:
            continue
        key = tuple(sorted(i["name"] for i in items))
        if key in seen:
            continue
        seen.add(key)
        groups.append({"token": tok, "sources": sorted(sources),
                       "items": [{"source": i["source"], "name": i["name"],
                                  "url": i["url"]} for i in items]})
    groups.sort(key=lambda g: (-len(g["sources"]), -len(g["items"]), g["token"]))
    return groups[:MAX_GROUPS]


def topic_weights(config: dict) -> dict:
    """Weighted relevance topics: config `topics` mapping preferred;
    the legacy flat `grading.relevance_topics` list counts weight 1."""
    topics = config.get("topics")
    if isinstance(topics, dict) and topics:
        return {str(k): v for k, v in topics.items()}
    legacy = config.get("grading", {}).get("relevance_topics", [])
    return {str(t): 1 for t in legacy}


def item_time(item: dict) -> datetime | None:
    """Best-effort publication time from a candidate's metrics.

    Only some sources carry a parseable timestamp (arXiv, the RSS
    bundles, Bluesky, Google News…). None is a valid answer — the
    freshness filter must not punish sources for lacking one.
    """
    metrics = item.get("metrics") or {}
    raw = None
    for key in ("published", "created", "pubDate"):
        if metrics.get(key):
            raw = str(metrics[key])
            break
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            return None
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def apply_controls(results: list[dict], config: dict, now: datetime):
    """User controls (0.4.0), applied after fetching, before grouping.

    - keywords.mute: drop matching candidates outright
    - keywords.boost / keywords.alert: tag survivors; alert hits are
      also collected for the report's keyword_alerts section
    - topics (weighted): tag survivors with their topic hits
    - filters.max_age_hours: drop candidates whose parseable
      timestamp is older than the window (no timestamp = kept)

    Matching is case-insensitive substring over name + detail.
    Returns (stats, keyword_alerts). Mutates results in place.
    """
    kw = config.get("keywords") or {}
    mute = [str(k).lower() for k in kw.get("mute") or []]
    boost = [str(k) for k in kw.get("boost") or []]
    alert = [str(k) for k in kw.get("alert") or []]
    topics = topic_weights(config)
    max_age = (config.get("filters") or {}).get("max_age_hours")
    stats = {"muted": 0, "stale": 0, "boost_tagged": 0, "alert_tagged": 0}
    alerts = []
    for result in results:
        kept = []
        for item in result["items"]:
            text = (item.get("name", "") + " " + item.get("detail", "")).lower()
            if any(k in text for k in mute):
                stats["muted"] += 1
                continue
            if max_age:
                when = item_time(item)
                if when and (now - when).total_seconds() > float(max_age) * 3600:
                    stats["stale"] += 1
                    continue
            hits_boost = [k for k in boost if k.lower() in text]
            hits_alert = [k for k in alert if k.lower() in text]
            hits_topics = {t: w for t, w in topics.items() if t.lower() in text}
            if hits_boost:
                item["keyword_hits"] = {**item.get("keyword_hits", {}),
                                        "boost": hits_boost}
                stats["boost_tagged"] += 1
            if hits_alert:
                item["keyword_hits"] = {**item.get("keyword_hits", {}),
                                        "alert": hits_alert}
                stats["alert_tagged"] += 1
                alerts.append({"source": item["source"], "name": item["name"],
                               "url": item["url"], "keywords": hits_alert})
            if hits_topics:
                item["topic_hits"] = hits_topics
            kept.append(item)
        result["items"] = kept
    return stats, alerts


def run_scan(edition: str, config: dict, now: datetime | None = None,
             out_dir: str = "state") -> dict:
    now = now or datetime.now(timezone.utc)
    results = []
    for module in FETCHERS:
        src_cfg = config.get("sources", {}).get(module.SOURCE, {})
        if isinstance(src_cfg, dict) and src_cfg.get("enabled") is False:
            results.append({"source": module.SOURCE, "layer": module.LAYER,
                            "status": "disabled", "items": [],
                            "note": "disabled in config (enabled: false)"})
            continue
        try:
            result = module.fetch(config, now)
        except Exception as exc:  # a fetcher bug must not kill the scan
            from .fetchers.common import missing
            result = missing(module.SOURCE, module.LAYER, f"fetcher error: {exc}")
        max_items = src_cfg.get("max_items") if isinstance(src_cfg, dict) else None
        if max_items and len(result["items"]) > int(max_items):
            result["items"] = result["items"][:int(max_items)]
            note = f"capped at {max_items} by config max_items"
            result["note"] = f"{result['note']}; {note}" if result["note"] else note
        results.append(result)
    stats, alerts = apply_controls(results, config, now)
    vocab_stats = apply_vocab(results, config, now)
    report = {
        "edition": edition,
        "scanned_at": now.isoformat(),
        "sources": results,
        "resonance": resonance_groups(results),
        "keyword_alerts": alerts,
        "controls": stats,
        "vocab": vocab_stats,
        "missing": [r["source"] for r in results if r["status"] == "missing"],
        "disabled": [r["source"] for r in results if r["status"] == "disabled"],
    }
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"candidates-{now:%Y%m%d}-{edition}.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    report["_file"] = out_path
    return report


def summary_lines(report: dict) -> list[str]:
    lines = [f"scan {report['edition']} @ {report['scanned_at']} -> {report['_file']}"]
    for result in report["sources"]:
        lines.append(f"  L{result['layer']} {result['source']:<12} "
                     f"{result['status']:<7} items={len(result['items'])}"
                     + (f" ({result['note']})" if result["note"] else ""))
    lines.append(f"  resonance groups: {len(report['resonance'])}")
    controls = report.get("controls") or {}
    if any(controls.values()):
        lines.append(f"  controls: muted={controls.get('muted', 0)} "
                     f"stale={controls.get('stale', 0)} "
                     f"boost={controls.get('boost_tagged', 0)} "
                     f"alert={controls.get('alert_tagged', 0)}")
    if report.get("keyword_alerts"):
        lines.append(f"  keyword alerts: {len(report['keyword_alerts'])}")
    vocab = report.get("vocab") or {}
    if vocab.get("enabled") is not False and vocab:
        if vocab.get("baseline"):
            lines.append(f"  vocab: baseline built ({vocab.get('size', 0)} names); "
                         "novelty flags start with the next scan")
        else:
            lines.append(f"  vocab: {vocab.get('novel', 0)} novel names "
                         f"(vocab size {vocab.get('size', 0)})")
    return lines
