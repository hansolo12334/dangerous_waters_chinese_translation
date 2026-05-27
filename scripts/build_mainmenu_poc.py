#!/usr/bin/env python3
"""Build Chinese four-state main-menu button images and repack the archive."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from wqy_pcf import PcfBitmapFont

BUTTON_LABELS = {
    "MissionEditor_x575y340.bmp": ("任务编辑器", 210, 17),
    "missions_x510y140.bmp": ("任务", 170, 17),
    "campaign_x560y190.bmp": ("战役", 190, 17),
    "multiplayer_x560y240.bmp": ("联机对战", 190, 17),
    "playerslog_x550y390.bmp": ("玩家日志", 215, 17),
    "options_x510y440.bmp": ("选项", 155, 17),
    "quickmission_x585y285.bmp": ("快速任务", 205, 17),
    "usniref_x460y485.bmp": ("海军资料库", 215, 17),
    "exit_x550y555.bmp": ("退出", 64, 174),
}
STATE_COLORS = [(250, 238, 194), (215, 255, 255), (92, 112, 112), (218, 255, 255)]


def main() -> None:
    repository = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-dir", type=Path, default=repository.parent / "Dangerous Waters")
    parser.add_argument("--output-dir", type=Path, default=repository / "build" / "mainmenu_zh")
    parser.add_argument(
        "--wqy-pcf",
        type=Path,
        default=repository / "assets" / "wqy-bitmapsong" / "wenquanyi_12pt.pcf",
    )
    arguments = parser.parse_args()
    font = PcfBitmapFont(arguments.wqy_pcf)
    graphics = arguments.game_dir / "Graphics"
    archive_dir = arguments.output_dir / "Graphics"
    asset_dir = arguments.output_dir / "assets"
    archive_dir.mkdir(parents=True, exist_ok=True)
    asset_dir.mkdir(parents=True, exist_ok=True)
    archive = archive_dir / "mainmenu"
    shutil.copyfile(graphics / "mainmenu.ndx", archive.with_suffix(".ndx"))
    shutil.copyfile(graphics / "mainmenu.grp", archive.with_suffix(".grp"))
    grp = repository / "grp" / "bin" / "grp.exe"
    for button_name, (label, erase_width, text_left) in BUTTON_LABELS.items():
        subprocess.run(
            [str(grp), str(archive), "-unpack", button_name, str(asset_dir), "-force"],
            check=False,
            stdout=subprocess.DEVNULL,
        )
        button_path = asset_dir / button_name
        if not button_path.exists():
            raise FileNotFoundError(button_path)
        render_button(button_path, label, erase_width, text_left, font)
        subprocess.run(
            [str(grp), str(archive), "-unlink", button_name, "-add", str(button_path)],
            check=True,
        )
    subprocess.run([str(grp), str(archive), "-repack", "-test", *BUTTON_LABELS], check=True)
    print(f"Chinese main-menu archive written to: {archive_dir}")


def render_button(
    path: Path, label: str, erase_width: int, text_left: int, font: PcfBitmapFont
) -> None:
    image = Image.open(path).convert("RGB")
    frame_height = image.height // 4
    mask = render_label_mask(label, font)
    panel_width = min(image.width - 12, max(erase_width, mask.width + 20))
    panel_left = max(0, text_left - 10)
    for frame, color in enumerate(STATE_COLORS):
        top = frame * frame_height
        panel = Image.new("RGB", (panel_width, 29), (3, 11, 15))
        image.paste(panel, (panel_left, top + 5))
        glyph_top = top + 9
        glow = mask.filter(ImageFilter.GaussianBlur(2))
        glow_layer = Image.new("RGB", image.size, (26, 100, 108))
        color_layer = Image.new("RGB", image.size, color)
        image.paste(glow_layer, (0, 0), position_mask(glow, text_left, glyph_top, image.size))
        image.paste(color_layer, (0, 0), position_mask(mask, text_left, glyph_top, image.size))
    image.save(path)


def render_label_mask(label: str, font: PcfBitmapFont) -> Image.Image:
    glyph_size = 20
    gap = 2
    mask = Image.new("L", (len(label) * glyph_size + (len(label) - 1) * gap, glyph_size), 0)
    for index, character in enumerate(label):
        glyph = font.glyph(character).resize((glyph_size, glyph_size), Image.Resampling.NEAREST)
        mask.paste(glyph, (index * (glyph_size + gap), 0))
    return mask


def position_mask(mask: Image.Image, left: int, top: int, size: tuple[int, int]) -> Image.Image:
    positioned = Image.new("L", size, 0)
    positioned.paste(mask, (left, top))
    return positioned


if __name__ == "__main__":
    main()
