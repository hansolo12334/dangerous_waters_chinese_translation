#!/usr/bin/env python3
"""Build the UTF-8 hook package with translated scenario mission text."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> None:
    repository = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-dir", type=Path, default=repository.parent / "Dangerous Waters")
    parser.add_argument("--output-dir", type=Path, default=repository / "build" / "mission_zh_poc")
    parser.add_argument(
        "--scenario-translations",
        type=Path,
        nargs="+",
        default=[repository / "translations" / "scenarios" / "SM08_zh.json"],
        help="Scenario translation JSON files named like SM08_zh.json.",
    )
    arguments = parser.parse_args()
    output_dir = arguments.output_dir.resolve()
    scenario_translations = [path.resolve() for path in arguments.scenario_translations]
    utf8_output = output_dir / "runtime"
    subprocess.run(
        [
            sys.executable,
            "-B",
            str(Path(__file__).with_name("build_utf8_fui_hook_poc.py")),
            "--game-dir",
            str(arguments.game_dir),
            "--output-dir",
            str(utf8_output),
            "--translations",
            str(repository / "translations" / "poc_exit_zh.json"),
            str(repository / "translations" / "poc_apptext_zh.json"),
            "--font-text",
            *[str(path) for path in scenario_translations],
        ],
        check=True,
    )
    translations_output = output_dir / "translations"
    translations_output.mkdir(parents=True, exist_ok=True)
    for scenario_translation in scenario_translations:
        source_stem = scenario_translation.stem.removesuffix("_zh")
        source_candidates = list((arguments.game_dir / "Scenario").glob(f"{source_stem}.*"))
        source_candidates = [
            source for source in source_candidates if source.suffix.lower() in {".ms", ".mp", ".mc"}
        ]
        if len(source_candidates) != 1:
            raise ValueError(
                f"Expected exactly one scenario source for {scenario_translation.name}: {source_candidates}"
            )
        scenario_output = utf8_output / "Scenario" / source_candidates[0].name
        subprocess.run(
            [
                sys.executable,
                "-B",
                str(Path(__file__).with_name("scenario_text_tool.py")),
                "patch",
                str(source_candidates[0]),
                str(scenario_translation),
                str(scenario_output),
            ],
            check=True,
        )
        shutil.copyfile(scenario_translation, translations_output / scenario_translation.name)
    print(f"Mission localization PoC written to: {utf8_output}")
    print("Copy its dinput8.dll, AppTextE.dll, Graphics folder and Scenario folder into the game directory.")


if __name__ == "__main__":
    main()
