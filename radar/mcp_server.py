"""MCP server entry point (placeholder).

Roadmap step 2: once the fetch layer exists, expose three tools over
MCP so any MCP-capable agent can call them:

  scan(edition)   -> raw candidates from all layered sources
  report(edition) -> the graded, deduped report for one edition
  review()        -> topics due for the 14-day check

Until then this module intentionally refuses to start, rather than
pretending to serve tools it does not have.
"""

from __future__ import annotations


def main() -> int:
    raise SystemExit(
        "radar MCP server is not implemented yet (skeleton 0.1.0). "
        "See README roadmap."
    )


if __name__ == "__main__":
    main()
