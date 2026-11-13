"""A tiny YAML-subset parser, used only when PyYAML is unavailable.

The project is zero-dependency by design; config files use a small
corner of YAML and this parser covers exactly that corner:

- comments (# ...) and blank lines
- nested mappings by indentation
- block sequences (- item), including sequences of mappings
- flow sequences ([a, b]) and flow mappings ({a: 1})
- scalars: plain / single- / double-quoted strings, ints, floats,
  true/false, null / ~

Anchors, multiline strings and tags are NOT supported; with
PyYAML installed the full language is available instead
(radar/config.py prefers it). Both parsers are tested against
config.example.yaml for identical output.
"""

from __future__ import annotations

import re


def _strip_comment(line: str) -> str:
    in_s = in_d = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_d:
            in_s = not in_s
        elif ch == '"' and not in_s and (i == 0 or line[i - 1] != "\\"):
            in_d = not in_d
        elif ch == "#" and not in_s and not in_d and (i == 0 or line[i - 1] in " \t"):
            return line[:i]
    return line


def _scalar(text: str):
    text = text.strip()
    if text in ("", "~", "null", "Null", "NULL"):
        return None
    if text in ("true", "True", "TRUE"):
        return True
    if text in ("false", "False", "FALSE"):
        return False
    if len(text) >= 2 and text[0] == text[-1] == '"':
        return text[1:-1].replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")
    if len(text) >= 2 and text[0] == text[-1] == "'":
        return text[1:-1].replace("''", "'")
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        return [_scalar(part) for part in _split_flow(inner)] if inner else []
    if text.startswith("{") and text.endswith("}"):
        inner = text[1:-1].strip()
        out = {}
        for part in _split_flow(inner):
            key, _, value = part.partition(":")
            out[_scalar(key)] = _scalar(value)
        return out
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return text


def _split_flow(inner: str) -> list[str]:
    parts, depth, in_s, in_d, current = [], 0, False, False, ""
    for ch in inner:
        if ch == "'" and not in_d:
            in_s = not in_s
        elif ch == '"' and not in_s:
            in_d = not in_d
        elif not in_s and not in_d:
            if ch in "[{":
                depth += 1
            elif ch in "]}":
                depth -= 1
            elif ch == "," and depth == 0:
                parts.append(current)
                current = ""
                continue
        current += ch
    if current.strip():
        parts.append(current)
    return parts


_KEY_RE = re.compile(r"^([^:\s][^:]*?):(\s+(.*))?$")


def _tokenize(text: str) -> list[tuple[int, str]]:
    lines = []
    for raw in text.splitlines():
        line = _strip_comment(raw).rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        lines.append((indent, line.strip()))
    return lines


def _parse_block(lines: list[tuple[int, str]], i: int, indent: int):
    """Parse the block starting at lines[i] with the given indent.
    Returns (value, next_index)."""
    if i >= len(lines):
        return None, i
    if lines[i][1].startswith("- ") or lines[i][1] == "-":
        seq = []
        while i < len(lines) and lines[i][0] == indent and (
                lines[i][1].startswith("- ") or lines[i][1] == "-"):
            content = lines[i][1][1:].strip()
            if not content:
                value, i = _parse_block(lines, i + 1, lines[i + 1][0] if i + 1 < len(lines) else indent + 1)
                seq.append(value)
                continue
            m = _KEY_RE.match(content)
            if m and not content.startswith(("[", "{", '"', "'")):
                # mapping inside a sequence item: reframe this line as
                # the first key at a virtual deeper indent
                virtual = indent + 2
                sub = [(virtual, content)]
                j = i + 1
                while j < len(lines) and lines[j][0] > indent:
                    sub.append((lines[j][0], lines[j][1]))
                    j += 1
                value, _ = _parse_block(sub, 0, virtual)
                seq.append(value)
                i = j
            else:
                seq.append(_scalar(content))
                i += 1
        return seq, i
    mapping = {}
    while i < len(lines) and lines[i][0] == indent and not lines[i][1].startswith("- "):
        m = _KEY_RE.match(lines[i][1])
        if not m:
            raise ValueError(f"yamlmini: cannot parse line: {lines[i][1]!r}")
        key = _scalar(m.group(1))
        rest = m.group(3)
        if rest:
            mapping[key] = _scalar(rest)
            i += 1
        elif i + 1 < len(lines) and lines[i + 1][0] > indent:
            value, i = _parse_block(lines, i + 1, lines[i + 1][0])
            mapping[key] = value
        else:
            mapping[key] = None
            i += 1
    return mapping, i


def loads(text: str):
    lines = _tokenize(text)
    if not lines:
        return {}
    value, _ = _parse_block(lines, 0, lines[0][0])
    return value
