"""Rolling name vocabulary: flag entity names seen for the first time.

Borrowed from new-term-radar's core X technique — a name only counts
as a signal when the accounts you watch say it for the first time in
weeks. tripple-signals has no X firehose, so the vocabulary is kept
over the *entity* sources, where a candidate's name is a real thing
(a repo, a model, a tool, an app) rather than a headline: the first
scan in which such a name appears in the candidate stream, it is
tagged `"novel": true`.

State lives in `state/vocab.json` as {source:name -> last-seen date}.
A name not seen for `vocab.window_days` (default 60) falls out of
the vocabulary and counts as novel again. The very first run only
builds the vocabulary and flags nothing, so novelty means "new
since you started watching", never "new to the internet".

Text sources (headlines, posts) are deliberately not tracked: their
names are sentences, not entities, and novelty there stays the
agent's judgement call.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

ENTITY_SOURCES = {"github", "huggingface", "hf_spaces", "openrouter",
                  "civitai", "producthunt", "sitemaps", "app_store"}

DEFAULT_WINDOW_DAYS = 60
DEFAULT_STATE_FILE = "state/vocab.json"


def _load(path: str):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def apply_vocab(results: list[dict], config: dict, now: datetime) -> dict:
    """Tag novel entity names in place; persist the vocabulary.

    Returns stats for the report: {"baseline": bool, "novel": int,
    "size": int} — or {"enabled": False} when turned off in config.
    """
    cfg = config.get("vocab") or {}
    if cfg.get("enabled") is False:
        return {"enabled": False}
    window = int(cfg.get("window_days", DEFAULT_WINDOW_DAYS))
    path = cfg.get("state_file", DEFAULT_STATE_FILE)
    baseline = not os.path.exists(path)
    today = now.date().isoformat()
    horizon = (now - timedelta(days=window)).date().isoformat()
    vocab = {k: v for k, v in _load(path).items() if str(v) >= horizon}
    novel = 0
    for result in results:
        if result["source"] not in ENTITY_SOURCES:
            continue
        for item in result["items"]:
            key = f"{result['source']}:{item['name'].strip().lower()}"
            if key not in vocab and not baseline:
                item["novel"] = True
                novel += 1
            vocab[key] = today
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(vocab, fh, ensure_ascii=False, indent=1, sort_keys=True)
    return {"baseline": baseline, "novel": novel, "size": len(vocab)}
