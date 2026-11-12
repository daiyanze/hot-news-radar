"""Topic store: the radar's structured memory.

The store is a single JSON file (default ``state/seen-topics.json``).
Each topic records when it was first seen, which sources carried it,
and its grade history, so later runs can dedupe ("only report what
changed") and the 14-day review can score each signal source.

No network access happens here; this module is pure bookkeeping.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date, timedelta

DEFAULT_STATE_PATH = os.path.join("state", "seen-topics.json")


def load_store(path: str = DEFAULT_STATE_PATH) -> dict:
    """Load the store, returning an empty one if the file is missing."""
    if not os.path.exists(path):
        return {"topics": []}
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    data.setdefault("topics", [])
    return data


def save_store(store: dict, path: str = DEFAULT_STATE_PATH) -> None:
    """Write the store atomically (temp file + rename)."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(store, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def upsert_topic(
    store: dict,
    name: str,
    sources: list[str],
    grade: str,
    today: date | None = None,
) -> dict:
    """Insert a topic or update it with the latest sighting.

    Returns the topic record. ``first_seen`` never moves once set;
    ``sources`` accumulate; every sighting appends to ``history``.
    """
    today = today or date.today()
    stamp = today.isoformat()
    for topic in store["topics"]:
        if topic["name"] == name:
            topic["last_seen"] = stamp
            for source in sources:
                if source not in topic["sources"]:
                    topic["sources"].append(source)
            topic["history"].append({"date": stamp, "grade": grade})
            if topic.get("review") is None:
                topic["review"] = _empty_review(topic["first_seen"])
            return topic
    topic = {
        "name": name,
        "first_seen": stamp,
        "last_seen": stamp,
        "sources": list(sources),
        "history": [{"date": stamp, "grade": grade}],
        "review": _empty_review(stamp),
    }
    store["topics"].append(topic)
    return topic


def _empty_review(first_seen: str) -> dict:
    return {"due": None, "result": None, "checked_on": None, "_first_seen": first_seen}


def due_for_review(store: dict, today: date | None = None, after_days: int = 14) -> list[dict]:
    """Topics whose 14-day review is due and not yet recorded.

    A topic's review compares its search-interest peak after the report
    day against its own earlier baseline (see methodology.md); this
    function only decides *which* topics are due.
    """
    today = today or date.today()
    due = []
    for topic in store["topics"]:
        review = topic.get("review") or {}
        if review.get("result") is not None:
            continue
        first_seen = date.fromisoformat(topic["first_seen"])
        if today - first_seen >= timedelta(days=after_days):
            due.append(topic)
    return due


def record_review(store: dict, name: str, result: str, today: date | None = None) -> dict:
    """Record a review outcome: "hit" or "miss" (per the 14-day rule)."""
    if result not in ("hit", "miss"):
        raise ValueError("result must be 'hit' or 'miss'")
    today = today or date.today()
    for topic in store["topics"]:
        if topic["name"] == name:
            topic["review"] = {
                "due": None,
                "result": result,
                "checked_on": today.isoformat(),
                "_first_seen": topic["first_seen"],
            }
            return topic
    raise KeyError(f"topic not found: {name}")
