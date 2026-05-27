#!/usr/bin/env python3
"""Extract and safely patch Dangerous Waters RT_STRING resources."""

from __future__ import annotations

import argparse
import csv
import json
import re
import struct
from dataclasses import dataclass
from pathlib import Path


RT_STRING = 6
FORMAT_TOKEN = re.compile(r"%(?:[-+0 #]*\d*(?:\.\d+)?[hlL]?)?[a-zA-Z%]")


@dataclass
class StringBlock:
    resource_id: int
    offset: int
    size: int
    strings: list[str]


class PeStringResources:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.data = bytearray(path.read_bytes())
        pe_offset = struct.unpack_from("<I", self.data, 0x3C)[0]
        section_count = struct.unpack_from("<H", self.data, pe_offset + 6)[0]
        optional_size = struct.unpack_from("<H", self.data, pe_offset + 20)[0]
        optional_offset = pe_offset + 24
        magic = struct.unpack_from("<H", self.data, optional_offset)[0]
        data_directory_offset = optional_offset + (96 if magic == 0x10B else 112)
        resource_rva = struct.unpack_from("<I", self.data, data_directory_offset + 16)[0]
        self.sections: list[tuple[int, int, int]] = []
        for index in range(section_count):
            offset = optional_offset + optional_size + index * 40
            virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from(
                "<IIII", self.data, offset + 8
            )
            self.sections.append((virtual_address, max(virtual_size, raw_size), raw_offset))
        self.resource_base = self.rva_to_offset(resource_rva)

    def rva_to_offset(self, rva: int) -> int:
        for virtual_address, size, raw_offset in self.sections:
            if virtual_address <= rva < virtual_address + size:
                return raw_offset + rva - virtual_address
        raise ValueError(f"RVA not in any section: 0x{rva:x}")

    def blocks(self) -> list[StringBlock]:
        blocks: list[StringBlock] = []

        def walk(relative_offset: int, identifiers: list[int]) -> None:
            offset = self.resource_base + relative_offset
            named_count, id_count = struct.unpack_from("<HH", self.data, offset + 12)
            for index in range(named_count + id_count):
                name, child = struct.unpack_from("<II", self.data, offset + 16 + index * 8)
                identifier = name & 0xFFFF
                if child & 0x80000000:
                    walk(child & 0x7FFFFFFF, identifiers + [identifier])
                elif identifiers and identifiers[0] == RT_STRING:
                    data_rva, size = struct.unpack_from(
                        "<II", self.data, self.resource_base + child
                    )
                    strings = decode_block(self.data, self.rva_to_offset(data_rva))
                    blocks.append(
                        StringBlock(identifiers[1], self.rva_to_offset(data_rva), size, strings)
                    )

        walk(0, [])
        return sorted(blocks, key=lambda block: block.resource_id)

    def entries(self) -> dict[int, str]:
        entries: dict[int, str] = {}
        for block in self.blocks():
            for index, text in enumerate(block.strings):
                if text:
                    entries[(block.resource_id - 1) * 16 + index] = text
        return entries

    def patch(self, translations: dict[int, str]) -> None:
        pending = set(translations)
        for block in self.blocks():
            strings = list(block.strings)
            changed = False
            for index, source in enumerate(strings):
                string_id = (block.resource_id - 1) * 16 + index
                if string_id not in translations:
                    continue
                replacement = translations[string_id]
                validate_placeholders(string_id, source, replacement)
                strings[index] = replacement
                pending.remove(string_id)
                changed = True
            if not changed:
                continue
            encoded = encode_block(strings)
            if len(encoded) > block.size:
                raise ValueError(
                    f"resource block {block.resource_id} grows from {block.size} "
                    f"to {len(encoded)} bytes; shorten translations or rebuild resources"
                )
            self.data[block.offset : block.offset + block.size] = encoded.ljust(block.size, b"\0")
        if pending:
            raise ValueError(f"string IDs not found: {sorted(pending)}")


def decode_block(data: bytes | bytearray, offset: int) -> list[str]:
    strings: list[str] = []
    cursor = offset
    for _ in range(16):
        length = struct.unpack_from("<H", data, cursor)[0]
        cursor += 2
        strings.append(data[cursor : cursor + length * 2].decode("utf-16le"))
        cursor += length * 2
    return strings


def encode_block(strings: list[str]) -> bytes:
    output = bytearray()
    for text in strings:
        encoded = text.encode("utf-16le")
        output.extend(struct.pack("<H", len(encoded) // 2))
        output.extend(encoded)
    return bytes(output)


def validate_placeholders(string_id: int, source: str, replacement: str) -> None:
    original = FORMAT_TOKEN.findall(source)
    translated = FORMAT_TOKEN.findall(replacement)
    if original != translated:
        raise ValueError(
            f"string {string_id} changes format tokens: {original} -> {translated}"
        )


def extract_command(input_path: Path, output_path: Path) -> None:
    entries = PeStringResources(input_path).entries()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.writer(output, delimiter="\t")
        writer.writerow(["id", "source", "translation"])
        for string_id, source in sorted(entries.items()):
            writer.writerow([string_id, source, ""])
    print(f"{input_path}: exported {len(entries)} strings -> {output_path}")


def patch_command(input_path: Path, translations_path: Path, output_path: Path) -> None:
    raw = json.loads(translations_path.read_text(encoding="utf-8"))
    translations = {int(string_id): str(text) for string_id, text in raw.items()}
    resources = PeStringResources(input_path)
    resources.patch(translations)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(resources.data)
    print(f"{input_path}: patched {len(translations)} strings -> {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    extract = subparsers.add_parser("extract")
    extract.add_argument("input", type=Path)
    extract.add_argument("output", type=Path)
    patch = subparsers.add_parser("patch")
    patch.add_argument("input", type=Path)
    patch.add_argument("translations", type=Path)
    patch.add_argument("output", type=Path)
    arguments = parser.parse_args()
    if arguments.command == "extract":
        extract_command(arguments.input, arguments.output)
    else:
        patch_command(arguments.input, arguments.translations, arguments.output)


if __name__ == "__main__":
    main()
