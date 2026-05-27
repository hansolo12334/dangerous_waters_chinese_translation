#!/usr/bin/env python3
"""Build exit-confirmation DLLs that verify dynamic text rendering."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    repository = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-dir", type=Path, default=repository.parent / "Dangerous Waters")
    parser.add_argument("--output-dir", type=Path, default=repository / "build" / "dynamic_text_poc")
    arguments = parser.parse_args()
    tool = Path(__file__).with_name("dw_string_tool.py")
    source = arguments.game_dir / "AppTextE.dll"
    configurations = {
        "ascii": repository / "translations" / "poc_exit_ascii.json",
        "zh": repository / "translations" / "poc_exit_zh.json",
    }
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    for name, configuration in configurations.items():
        destination = arguments.output_dir / name / "AppTextE.dll"
        subprocess.run(
            [
                sys.executable,
                "-B",
                str(tool),
                "patch",
                str(source),
                str(configuration),
                str(destination),
            ],
            check=True,
        )
    print(f"Dynamic text PoCs written to: {arguments.output_dir}")


if __name__ == "__main__":
    main()
