#!/usr/bin/env python3
"""Export all Dangerous Waters application and station text resources."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


TARGETS = {
    "AppTextE.tsv": "AppTextE.dll",
    "688I_TextE.tsv": r"Interfaces\688I\textE.dll",
    "AkulaII_TextE.tsv": r"Interfaces\AkulaII\textE.dll",
    "FFG_TextE.tsv": r"Interfaces\FFG\TextE.dll",
    "Kilo_TextE.tsv": r"Interfaces\Kilo\TextE.dll",
    "Kilo_TextCE.tsv": r"Interfaces\Kilo\TextCE.dll",
    "MH60_TextE.tsv": r"Interfaces\MH60\TextE.dll",
    "P3_TextE.tsv": r"Interfaces\P3\textE.dll",
    "ssn21_TextE.tsv": r"Interfaces\ssn21\TextE.dll",
}


def main() -> None:
    repository = Path(__file__).resolve().parent.parent
    default_game_dir = repository.parent / "Dangerous Waters"
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-dir", type=Path, default=default_game_dir)
    parser.add_argument(
        "--output-dir", type=Path, default=repository / "translations" / "export"
    )
    arguments = parser.parse_args()
    tool = Path(__file__).with_name("dw_string_tool.py")
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    for output_name, relative_input in TARGETS.items():
        input_path = arguments.game_dir / relative_input
        if not input_path.exists():
            raise FileNotFoundError(input_path)
        subprocess.run(
            [
                sys.executable,
                "-B",
                str(tool),
                "extract",
                str(input_path),
                str(arguments.output_dir / output_name),
            ],
            check=True,
        )


if __name__ == "__main__":
    main()
