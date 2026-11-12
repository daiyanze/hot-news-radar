"""CLI entry point: python -m radar <command>

Commands:
  scan --edition morning|evening   Run all fetchers, write the
                                   candidate file, print per-source
                                   status. Grading/reporting stays
                                   with the agent (SKILL.md).
  review                           List topics whose 14-day review
                                   is due.
"""

from __future__ import annotations

import argparse
import sys

from . import store as store_mod


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="radar", description="Hot news radar")
    parser.add_argument("--state", default=store_mod.DEFAULT_STATE_PATH,
                        help="Path to the topic store JSON")
    parser.add_argument("--config", default=None, help="Path to config JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="Run the fetch layer for one edition")
    p_scan.add_argument("--edition", choices=["morning", "evening"], required=True)

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

    if args.command == "scan":
        from . import scan as scan_mod
        config = scan_mod.load_config(args.config)
        report = scan_mod.run_scan(args.edition, config)
        for line in scan_mod.summary_lines(report):
            print(line)
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
