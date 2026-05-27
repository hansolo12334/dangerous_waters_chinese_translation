#!/usr/bin/env python3
"""Build UTF-8 FUI hook PoC with separate Chinese bitmap-font atlas pages."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

from wqy_pcf import PcfBitmapFont


SLOT_FIRST = 32
SLOT_COUNT = 224


def main() -> None:
    repository = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-dir", type=Path, default=repository.parent / "Dangerous Waters")
    parser.add_argument("--output-dir", type=Path, default=repository / "build" / "utf8_fui_hook_poc")
    parser.add_argument(
        "--apptext-source",
        type=Path,
        help="Clean AppTextE.dll source; defaults to the current game copy.",
    )
    parser.add_argument(
        "--shared-source",
        type=Path,
        help="Clean Graphics/shared archive stem; defaults to Graphics/back/shared when present.",
    )
    parser.add_argument(
        "--translations",
        type=Path,
        nargs="+",
        default=[repository / "translations" / "poc_exit_zh.json"],
    )
    parser.add_argument(
        "--font-text",
        type=Path,
        nargs="*",
        default=[],
        help="Additional JSON values to include in the Chinese atlas without patching AppTextE.dll.",
    )
    parser.add_argument(
        "--wqy-pcf",
        type=Path,
        default=repository / "assets" / "wqy-bitmapsong" / "wenquanyi_12pt.pcf",
    )
    arguments = parser.parse_args()

    chinese_characters = collect_characters(arguments.translations + arguments.font_text)
    if not chinese_characters:
        raise ValueError("Translation files contain no non-ASCII glyphs")

    output = arguments.output_dir.resolve()
    graphics_dir = output / "Graphics"
    assets_dir = output / "assets"
    generated_dir = output / "native_generated"
    graphics_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)
    generated_dir.mkdir(parents=True, exist_ok=True)

    archive = graphics_dir / "shared"
    source_archive = arguments.shared_source or default_shared_source(arguments.game_dir)
    print(f"Using shared font source archive: {source_archive}")
    shutil.copyfile(source_archive.with_suffix(".ndx"), archive.with_suffix(".ndx"))
    shutil.copyfile(source_archive.with_suffix(".grp"), archive.with_suffix(".grp"))

    mappings = build_font_pages(
        characters=chinese_characters,
        font=PcfBitmapFont(arguments.wqy_pcf),
        assets_dir=assets_dir,
    )
    update_archive(repository / "grp" / "bin" / "grp.exe", archive, assets_dir, mappings)
    write_glyph_map_header(generated_dir / "generated_glyph_map.h", mappings)
    (output / "glyph_map.json").write_text(
        json.dumps(
            {
                character: {"page": page, "slot": slot}
                for character, page, slot in mappings
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    merge_translation_files(arguments.translations, output / "translations_merged.json")
    apptext_source = arguments.apptext_source or arguments.game_dir / "AppTextE.dll"
    subprocess.run(
        [
            sys.executable,
            "-B",
            str(Path(__file__).with_name("dw_string_tool.py")),
            "patch",
            str(apptext_source),
            str(output / "translations_merged.json"),
            str(output / "AppTextE.dll"),
        ],
        check=True,
    )
    build_proxy_dll(repository, generated_dir, output)
    print(f"UTF-8 FUI hook PoC written to: {output}")
    print("Copy dinput8.dll, AppTextE.dll, Graphics/shared.ndx and Graphics/shared.grp into the game directory.")


def collect_characters(paths: list[Path]) -> list[str]:
    characters: set[str] = set()
    for path in paths:
        translations = json.loads(path.read_text(encoding="utf-8"))
        for text in translations.values():
            characters.update(character for character in text if ord(character) >= 0x80)
    return sorted(characters, key=ord)


def default_shared_source(game_dir: Path) -> Path:
    backup = game_dir / "Graphics" / "back" / "shared"
    if backup.with_suffix(".ndx").exists() and backup.with_suffix(".grp").exists():
        return backup
    return game_dir / "Graphics" / "shared"


def merge_translation_files(paths: list[Path], output_path: Path) -> None:
    merged: dict[str, str] = {}
    for path in paths:
        merged.update(json.loads(path.read_text(encoding="utf-8")))
    output_path.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def build_font_pages(
    characters: list[str], font: PcfBitmapFont, assets_dir: Path
) -> list[tuple[str, int, int]]:
    mappings: list[tuple[str, int, int]] = []
    for page_index in range((len(characters) + SLOT_COUNT - 1) // SLOT_COUNT):
        page_characters = characters[page_index * SLOT_COUNT : (page_index + 1) * SLOT_COUNT]
        image = Image.new("L", (256, 256), 0)
        stem = f"dw_zh_{page_index:02d}"
        for offset, character in enumerate(page_characters):
            slot = SLOT_FIRST + offset
            glyph = font.glyph(character)
            if glyph.size != (16, 16):
                glyph = glyph.resize((16, 16), Image.Resampling.NEAREST)
            image.paste(glyph, ((slot % 16) * 16, (slot // 16) * 16))
            mappings.append((character, page_index, slot))
        image.save(assets_dir / f"{stem}.bmp")
        write_dimensions(assets_dir / f"{stem}.dim", stem)
    return mappings


def write_dimensions(path: Path, stem: str) -> None:
    lines = [
        "Version: 2",
        f"font: {stem}",
        "block_width: 16",
        "block_height: 16",
        "def_width: 16",
        "def_height: 16",
        "x_offset: 0",
        "y_offset: 0",
        "spacing: 1",
        "",
    ]
    lines.extend(f"{slot} 16" for slot in range(SLOT_FIRST, 256))
    path.write_text("\r\n".join(lines) + "\r\n", encoding="ascii")


def update_archive(
    grp: Path, archive: Path, assets_dir: Path, mappings: list[tuple[str, int, int]]
) -> None:
    page_count = max(page for _, page, _ in mappings) + 1
    for page_index in range(page_count):
        for suffix in (".bmp", ".dim"):
            asset = assets_dir / f"dw_zh_{page_index:02d}{suffix}"
            subprocess.run(
                [str(grp), str(archive), "-unlink", asset.name, "-add", str(asset)],
                check=True,
            )
    subprocess.run(
        [str(grp), str(archive), "-repack", "-test", "dw_zh_00.bmp"], check=True
    )


def write_glyph_map_header(path: Path, mappings: list[tuple[str, int, int]]) -> None:
    lines = [
        "#pragma once",
        "",
        "struct UnicodeGlyph { unsigned int codepoint; unsigned char page; unsigned char slot; };",
        "static const UnicodeGlyph kUnicodeGlyphs[] = {",
    ]
    lines.extend(
        f"    {{0x{ord(character):04X}u, {page}, {slot}}},"
        for character, page, slot in mappings
    )
    lines.extend(
        [
            "};",
            f"static const unsigned int kUnicodeGlyphCount = {len(mappings)}u;",
            f"static const unsigned int kUnicodeFontPageCount = {max(page for _, page, _ in mappings) + 1}u;",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="ascii")


def build_proxy_dll(repository: Path, generated_dir: Path, output: Path) -> None:
    native = repository / "native" / "dinput8_proxy"
    shutil.copyfile(native / "dinput8_proxy.cpp", generated_dir / "dinput8_proxy.cpp")
    shutil.copyfile(native / "dinput8_proxy.def", generated_dir / "dinput8_proxy.def")
    vswhere = Path(r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe")
    installation = subprocess.check_output(
        [
            str(vswhere),
            "-latest",
            "-products",
            "*",
            "-requires",
            "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
            "-property",
            "installationPath",
        ],
        text=True,
    ).strip()
    vcvars = Path(installation) / "VC" / "Auxiliary" / "Build" / "vcvarsall.bat"
    command = (
        "@echo off\r\n"
        f'call "{vcvars}" x86 >nul\r\n'
        f'cl /nologo /O2 /EHsc- /GR- /MT /DWIN32 /D_WINDOWS '
        f'/I"{generated_dir}" /LD "{generated_dir / "dinput8_proxy.cpp"}" '
        f'/link /DEF:"{generated_dir / "dinput8_proxy.def"}" '
        f'/OUT:"{output / "dinput8.dll"}" user32.lib kernel32.lib\r\n'
    )
    build_command = generated_dir / "build_proxy.cmd"
    build_command.write_text(command, encoding="ascii")
    subprocess.run(["cmd", "/c", str(build_command)], check=True, cwd=generated_dir)


if __name__ == "__main__":
    main()
