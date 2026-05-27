#!/usr/bin/env python3
"""Extract and patch translatable text blocks in Dangerous Waters scenario files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


TEXT_FIELDS = {"DESCRIPTION", "MISSIONTITLE", "TASKINGMESSAGE", "PLAYERTASKING"}


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    extract = subparsers.add_parser("extract")
    extract.add_argument("source", type=Path)
    extract.add_argument("output", type=Path)
    patch = subparsers.add_parser("patch")
    patch.add_argument("source", type=Path)
    patch.add_argument("translations", type=Path)
    patch.add_argument("output", type=Path)
    arguments = parser.parse_args()
    if arguments.command == "extract":
        extract_blocks(arguments.source, arguments.output)
    else:
        patch_blocks(arguments.source, arguments.translations, arguments.output)


def locate_blocks(lines: list[str]) -> list[tuple[str, int, int, int]]:
    counts: dict[str, int] = {}
    blocks: list[tuple[str, int, int, int]] = []
    for index, line in enumerate(lines):
        field = line.strip()
        if field not in TEXT_FIELDS or index + 1 >= len(lines):
            continue
        if lines[index + 1].strip() != "BEGINTEXT":
            continue
        end = index + 2
        while end < len(lines) and lines[end].strip() != "ENDTEXT":
            end += 1
        if end >= len(lines):
            raise ValueError(f"Missing ENDTEXT after {field} at line {index + 1}")
        counts[field] = counts.get(field, 0) + 1
        blocks.append((f"{field}#{counts[field]}", index + 2, end, index))
    return blocks


def extract_blocks(source: Path, output: Path) -> None:
    lines = source.read_text(encoding="utf-8-sig").splitlines()
    translations = {
        key: "\n".join(lines[start:end])
        for key, start, end, _ in locate_blocks(lines)
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(translations, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{source}: extracted {len(translations)} text blocks -> {output}")


def patch_blocks(source: Path, translations_path: Path, output: Path) -> None:
    lines = source.read_text(encoding="utf-8-sig").splitlines()
    translations = json.loads(translations_path.read_text(encoding="utf-8"))
    blocks = {key: (start, end) for key, start, end, _ in locate_blocks(lines)}
    missing = sorted(set(translations) - set(blocks))
    if missing:
        raise ValueError(f"Unknown scenario text blocks: {', '.join(missing)}")
    patched = 0
    for key, (start, end) in sorted(blocks.items(), key=lambda item: item[1][0], reverse=True):
        if key not in translations:
            continue
        replacement = str(translations[key]).splitlines()
        lines[start:end] = replacement
        patched += 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8", newline="")
    print(f"{source}: patched {patched} text blocks -> {output}")


if __name__ == "__main__":
    main()
