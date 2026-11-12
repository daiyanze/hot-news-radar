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

from .fetchers import FETCHERS

STOPWORDS = {"the", "a", "an", "of", "for", "to", "in", "on", "with", "and",
             "launches", "launch", "releases", "release", "announces", "new",
             "ai", "llm", "model", "models", "using", "show", "hn"}


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
        if len(sources) < 2:
            continue
        key = tuple(sorted(i["name"] for i in items))
        if key in seen:
            continue
        seen.add(key)
        groups.append({"token": tok, "sources": sorted(sources),
                       "items": [{"source": i["source"], "name": i["name"],
                                  "url": i["url"]} for i in items]})
    return groups


def load_config(path: str | None = None) -> dict:
    for candidate in [path, "config.json", "config.example.json"]:
        if candidate and os.path.exists(candidate):
            with open(candidate, encoding="utf-8") as fh:
                return json.load(fh)
    return {}


def run_scan(edition: str, config: dict, now: datetime | None = None,
             out_dir: str = "state") -> dict:
    now = now or datetime.now(timezone.utc)
    results = []
    for module in FETCHERS:
        try:
            results.append(module.fetch(config, now))
        except Exception as exc:  # a fetcher bug must not kill the scan
            from .fetchers.common import missing
            results.append(missing(module.SOURCE, module.LAYER, f"fetcher error: {exc}"))
    report = {
        "edition": edition,
        "scanned_at": now.isoformat(),
        "sources": results,
        "resonance": resonance_groups(results),
        "missing": [r["source"] for r in results if r["status"] == "missing"],
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
    return lines
