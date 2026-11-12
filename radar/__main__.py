"""CLI entry point: python -m radar <command>

Commands:
  review   List topics whose 14-day review is due (works today).
  scan     Placeholder for the fetch layer (roadmap step 1 in README).
           Judgement and reporting live in skills/hot-news-radar/SKILL.md
           and are performed by an agent, not by this CLI.
"""

from __future__ import annotations

import argparse
import sys

from . import store as store_mod


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="radar", description="Hot news radar")
    parser.add_argument("--state", default=store_mod.DEFAULT_STATE_PATH,
                        help="Path to the topic store JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("review", help="List topics due for their 14-day review")
    sub.add_parser("scan", help="Fetch-layer placeholder (not implemented yet)")

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
        print("Fetch layer is not implemented yet (skeleton 0.1.0). "
              "Run an agent with skills/hot-news-radar/SKILL.md instead.",
              file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
