#!/usr/bin/env python3
"""Patch USNI reference .txt files inside Graphics/usnidata archives."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def translation_text(translation: dict) -> str:
    if "text" in translation:
        return translation["text"]
    if "lines" in translation:
        return "\n".join(translation["lines"])
    raise KeyError('translation must contain either "text" or "lines"')


def resolve_translation_paths(paths: list[Path]) -> list[Path]:
    resolved: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        candidates = sorted(path.glob("*.json")) if path.is_dir() else [path]
        for candidate in candidates:
            absolute = candidate.resolve()
            if absolute in seen:
                continue
            seen.add(absolute)
            resolved.append(candidate)
    return resolved


def main() -> None:
    repository = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-dir", type=Path, default=repository.parent / "Dangerous Waters")
    parser.add_argument("--output-dir", type=Path, default=repository / "build" / "usni_text_poc")
    parser.add_argument(
        "--translations",
        type=Path,
        nargs="+",
        default=[repository / "translations" / "usni" / "TourvilleClassDD_zh.json"],
    )
    arguments = parser.parse_args()

    output = arguments.output_dir.resolve()
    assets_dir = output / "assets"
    graphics_dir = output / "Graphics"
    assets_dir.mkdir(parents=True, exist_ok=True)
    graphics_dir.mkdir(parents=True, exist_ok=True)

    archive = graphics_dir / "usnidata"
    source_archive = arguments.game_dir / "Graphics" / "usnidata"
    shutil.copyfile(source_archive.with_suffix(".ndx"), archive.with_suffix(".ndx"))
    shutil.copyfile(source_archive.with_suffix(".grp"), archive.with_suffix(".grp"))

    grp = repository / "grp" / "bin" / "grp.exe"
    patched = []
    translation_paths = resolve_translation_paths(arguments.translations)
    if not translation_paths:
        raise ValueError("No translation JSON files were found")
    for translation_path in translation_paths:
        translation = json.loads(translation_path.read_text(encoding="utf-8"))
        file_name = translation["file"]
        text = translation_text(translation)
        output_file = assets_dir / file_name
        output_file.write_text(text, encoding="utf-8", newline="")
        subprocess.run(
            [str(grp), str(archive), "-unlink", file_name, "-add", str(output_file)],
            check=True,
        )
        patched.append(file_name)
    subprocess.run([str(grp), str(archive), "-repack", "-test", patched[0]], check=True)
    print(f"USNI text package written to: {output}")
    print(f"Patched files: {', '.join(patched)}")


if __name__ == "__main__":
    main()
