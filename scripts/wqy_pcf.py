"""Minimal PCF bitmap-font reader for WenQuanYi glyph extraction."""

from __future__ import annotations

import struct
from pathlib import Path

from PIL import Image


class PcfBitmapFont:
    def __init__(self, path: Path) -> None:
        self.data = path.read_bytes()
        self.metrics = self._read_metrics()
        self.offsets, self.bitmap_offset = self._read_bitmaps()
        self.encodings = self._read_encodings()

    def glyph(self, character: str) -> Image.Image:
        glyph_index = self.encodings.get(ord(character))
        if glyph_index is None or glyph_index == 0xFFFF:
            raise ValueError(f"Font contains no glyph for {character!r}")
        left, right, _, ascent, descent = self.metrics[glyph_index]
        width = right - left
        height = ascent + descent
        row_bytes = ((width + 31) // 32) * 4
        source = self.bitmap_offset + self.offsets[glyph_index]
        image = Image.new("L", (width, height), 0)
        for row in range(height):
            bits = int.from_bytes(
                self.data[source + row * row_bytes : source + (row + 1) * row_bytes],
                "big",
            )
            for column in range(width):
                if bits & (1 << (row_bytes * 8 - 1 - column)):
                    image.putpixel((column, row), 255)
        return image

    def _read_metrics(self) -> list[tuple[int, int, int, int, int]]:
        format_value, offset = self._table(0x04)
        if format_value != 0x10E:
            raise ValueError(f"Unsupported PCF metrics format: {format_value:#x}")
        count = struct.unpack_from(">H", self.data, offset + 4)[0]
        values = self.data[offset + 6 : offset + 6 + count * 5]
        return [
            tuple(values[index * 5 + field] - 0x80 for field in range(5))
            for index in range(count)
        ]

    def _read_bitmaps(self) -> tuple[tuple[int, ...], int]:
        format_value, offset = self._table(0x08)
        if format_value != 0x0E:
            raise ValueError(f"Unsupported PCF bitmap format: {format_value:#x}")
        count = struct.unpack_from(">I", self.data, offset + 4)[0]
        offsets = struct.unpack_from(f">{count}I", self.data, offset + 8)
        bitmap_offset = offset + 8 + count * 4 + 16
        return offsets, bitmap_offset

    def _read_encodings(self) -> dict[int, int]:
        format_value, offset = self._table(0x20)
        if format_value != 0x0E:
            raise ValueError(f"Unsupported PCF encoding format: {format_value:#x}")
        min_low, max_low, min_high, max_high, _ = struct.unpack_from(
            ">5H", self.data, offset + 4
        )
        count = (max_low - min_low + 1) * (max_high - min_high + 1)
        indices = struct.unpack_from(f">{count}H", self.data, offset + 14)
        result: dict[int, int] = {}
        stride = max_low - min_low + 1
        for high in range(min_high, max_high + 1):
            for low in range(min_low, max_low + 1):
                result[(high << 8) | low] = indices[
                    (high - min_high) * stride + low - min_low
                ]
        return result

    def _table(self, table_type: int) -> tuple[int, int]:
        magic, count = struct.unpack_from("<II", self.data, 0)
        if magic != 0x70636601:
            raise ValueError("Not a PCF font")
        for index in range(count):
            current_type, format_value, _, offset = struct.unpack_from(
                "<IIII", self.data, 8 + index * 16
            )
            if current_type == table_type:
                return format_value, offset
        raise ValueError(f"PCF table not found: {table_type:#x}")
