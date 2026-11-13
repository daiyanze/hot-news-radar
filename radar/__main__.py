"""CLI entry point.

One-command use (what most people want):

  python -m radar            Scan now; the edition is picked from
                             the local hour (before noon = morning,
                             otherwise evening). After
                             `pip install -e .` the same works as
                             plain `radar`.

Explicit commands:

  scan [--edition morning|evening]   Run all fetchers for one
                                     edition, write the candidate
                                     file, print per-source status.
                                     Grading/reporting stays with
                                     the agent (SKILL.md).
  review                             List topics whose 14-day
                                     review is due.

Config is YAML or JSON (see radar/config.py); state is the topic
store JSON.
"""

from __future__ import annotations

import argparse
from datetime import datetime

from . import store as store_mod


def auto_edition(now: datetime | None = None) -> str:
    """Edition by local hour: morning before noon, evening after."""
    now = now or datetime.now()
    return "morning" if now.hour < 12 else "evening"


def _run_scan(args) -> int:
    from . import scan as scan_mod
    config = scan_mod.load_config(getattr(args, "config_cmd", None) or args.config)
    edition = args.edition or auto_edition()
    report = scan_mod.run_scan(edition, config)
    for line in scan_mod.summary_lines(report):
        print(line)
    print(f"候选文件：{report['_file']}")
    print("下一步：把候选文件和 skills/tripple-signals/SKILL.md 交给你的 agent 出报告。")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="radar", description="tripple-signals radar")
    parser.add_argument("--state", default=store_mod.DEFAULT_STATE_PATH,
                        help="Path to the topic store JSON")
    parser.add_argument("--config", default=None,
                        help="Path to config (YAML or JSON); default: search "
                             "config.yaml / config.json / config.example.*")
    sub = parser.add_subparsers(dest="command")

    p_scan = sub.add_parser("scan", help="Run the fetch layer for one edition")
    p_scan.add_argument("--edition", choices=["morning", "evening"], default=None,
                        help="Default: picked from the local hour")
    # Also accepted after the subcommand (argparse globals must come
    # first); resolved in _run_scan.
    p_scan.add_argument("--config", dest="config_cmd", default=None,
                        help="Path to config (YAML or JSON)")

    sub.add_parser("review", help="List topics due for their 14-day review")

    args = parser.parse_args(argv)

    if args.command == "review":
        data = store_mod.load_store(args.state)
        due = store_mod.due_for_review(data)
        if not due:
            print("No topics due for review.")
            return 0
        for topic in due:
            print(f"- {topic['name']} (first seen {topic['first_seen']}, "
                  f"sources: {', '.join(topic['sources'])})")
        return 0

    # No subcommand (or explicit `scan`): the one-command path.
    if args.command in (None, "scan"):
        if not hasattr(args, "edition"):
            args.edition = None
        return _run_scan(args)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
