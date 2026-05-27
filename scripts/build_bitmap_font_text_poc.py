#!/usr/bin/env python3
"""Build a dynamic Chinese PoC by remapping single-byte bitmap-font slots."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

from wqy_pcf import PcfBitmapFont


GLYPHS = {
    "0": "中",
    "1": "文",
    "2": "动",
    "3": "态",
    "4": "本",
    "5": "测",
    "6": "试",
    "7": "是",
    "8": "否",
    "9": "退",
    "@": "出",
    "#": "游",
    "$": "戏",
    "!": "？",
}
FONT_STEMS = [
    "fru_plain",
    "fru_plain_r1",
    "fru_plain_r3",
    "fru_plain_r4",
    "fru_bold",
    "fru_bold_r1",
    "fru_bold_r3",
    "fru_bold_r4",
    "fru_small",
    "fru_small_r1",
    "fru_small_r3",
    "fru_small_r4",
]


def main() -> None:
    repository = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-dir", type=Path, default=repository.parent / "Dangerous Waters")
    parser.add_argument("--output-dir", type=Path, default=repository / "build" / "bitmap_font_text_poc")
    parser.add_argument(
        "--wqy-pcf",
        type=Path,
        default=repository / "assets" / "wqy-bitmapsong" / "wenquanyi_12pt.pcf",
    )
    arguments = parser.parse_args()
    chinese_font = PcfBitmapFont(arguments.wqy_pcf)

    graphics_dir = arguments.output_dir / "Graphics"
    assets_dir = arguments.output_dir / "assets"
    graphics_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)
    archive = graphics_dir / "shared"
    source_archive = arguments.game_dir / "Graphics" / "shared"
    shutil.copyfile(source_archive.with_suffix(".ndx"), archive.with_suffix(".ndx"))
    shutil.copyfile(source_archive.with_suffix(".grp"), archive.with_suffix(".grp"))

    grp = repository / "grp" / "bin" / "grp.exe"
    for stem in FONT_STEMS:
        for suffix in (".bmp", ".dim"):
            unpack_asset(grp, archive, assets_dir, f"{stem}{suffix}")
        render_font(assets_dir / f"{stem}.bmp", assets_dir / f"{stem}.dim", chinese_font)

    for stem in FONT_STEMS:
        for suffix in (".bmp", ".dim"):
            asset = assets_dir / f"{stem}{suffix}"
            subprocess.run(
                [str(grp), str(archive), "-unlink", asset.name, "-add", str(asset)],
                check=True,
            )
    subprocess.run([str(grp), str(archive), "-repack", "-test", "fru_plain.bmp"], check=True)

    dll_dir = arguments.output_dir
    dll_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            "-B",
            str(Path(__file__).with_name("dw_string_tool.py")),
            "patch",
            str(arguments.game_dir / "AppTextE.dll"),
            str(repository / "translations" / "poc_exit_bitmap_font.json"),
            str(dll_dir / "AppTextE.dll"),
        ],
        check=True,
    )
    mapping = " ".join(f"{token}={glyph}" for token, glyph in GLYPHS.items())
    (arguments.output_dir / "glyph_mapping.txt").write_text(mapping + "\n", encoding="utf-8")
    print(f"Bitmap font text PoC written to: {arguments.output_dir}")
    print(f"Glyph mapping: {mapping}")


def unpack_asset(grp: Path, archive: Path, output_dir: Path, name: str) -> None:
    subprocess.run(
        [str(grp), str(archive), "-unpack", name, str(output_dir), "-force"],
        check=False,
        stdout=subprocess.DEVNULL,
    )
    if not (output_dir / name).exists():
        raise FileNotFoundError(output_dir / name)


def render_font(bitmap_path: Path, dimensions_path: Path, font: "PcfBitmapFont") -> None:
    text = dimensions_path.read_text(encoding="ascii")
    block_width = parse_setting(text, "block_width")
    block_height = parse_setting(text, "block_height")
    image = Image.open(bitmap_path).convert("L")
    for token, glyph in GLYPHS.items():
        code = ord(token)
        left = (code % 16) * block_width
        top = (code // 16) * block_height
        image.paste(0, (left, top, left + block_width, top + block_height))
        glyph_image = font.glyph(glyph)
        if glyph_image.size != (block_width, block_height):
            glyph_image = glyph_image.resize((block_width, block_height), Image.Resampling.NEAREST)
        image.paste(glyph_image, (left, top))
        text = re.sub(
            rf"(?m)^{code}\s+\d+\s*$",
            f"{code} {block_width}",
            text,
        )
    image.save(bitmap_path)
    dimensions_path.write_text(text, encoding="ascii", newline="")


def parse_setting(text: str, name: str) -> int:
    match = re.search(rf"(?m)^{re.escape(name)}:\s*(\d+)\s*$", text)
    if not match:
        raise ValueError(f"Missing {name}")
    return int(match.group(1))


if __name__ == "__main__":
    main()
