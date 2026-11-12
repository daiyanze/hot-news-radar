"""Minimal MCP server (stdio, standard library only).

Exposes two tools so any MCP-capable agent can drive the radar:

  radar_scan   {edition: "morning"|"evening"} -> per-source status
               and the candidate file path (grading stays with the
               calling agent, per SKILL.md)
  radar_review {} -> topics due for the 14-day review

Run: python -m radar.mcp_server
"""

from __future__ import annotations

import json
import sys

from . import scan as scan_mod
from . import store as store_mod

PROTOCOL_VERSION = "2024-11-05"

TOOLS = [
    {
        "name": "radar_scan",
        "description": "Run one edition's fetch layer: scan all layered sources, "
                       "write state/candidates-<date>-<edition>.json, return "
                       "per-source status and possible cross-source resonance.",
        "inputSchema": {
            "type": "object",
            "properties": {"edition": {"type": "string", "enum": ["morning", "evening"]}},
            "required": ["edition"],
        },
    },
    {
        "name": "radar_review",
        "description": "List topics whose 14-day review is due (see methodology).",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def call_tool(name: str, arguments: dict) -> str:
    if name == "radar_scan":
        config = scan_mod.load_config()
        report = scan_mod.run_scan(arguments.get("edition", "morning"), config)
        return "\n".join(scan_mod.summary_lines(report))
    if name == "radar_review":
        data = store_mod.load_store()
        due = store_mod.due_for_review(data)
        if not due:
            return "No topics due for review."
        return "\n".join(f"- {t['name']} (first seen {t['first_seen']})" for t in due)
    raise ValueError(f"unknown tool: {name}")


def handle(message: dict) -> dict | None:
    method = message.get("method")
    msg_id = message.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "hot-news-radar", "version": "0.2.0"}}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = message.get("params", {})
        try:
            text = call_tool(params.get("name", ""), params.get("arguments", {}))
            return {"jsonrpc": "2.0", "id": msg_id, "result": {
                "content": [{"type": "text", "text": text}], "isError": False}}
        except Exception as exc:
            return {"jsonrpc": "2.0", "id": msg_id, "result": {
                "content": [{"type": "text", "text": str(exc)}], "isError": True}}
    if msg_id is not None:
        return {"jsonrpc": "2.0", "id": msg_id,
                "error": {"code": -32601, "message": f"method not found: {method}"}}
    return None  # notification


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = handle(message)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
