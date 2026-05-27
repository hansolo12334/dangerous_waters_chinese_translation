#!/usr/bin/env python3
"""Export scenario text blocks from all missions into translation JSON files."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    repository = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-dir", type=Path, default=repository.parent / "Dangerous Waters")
    parser.add_argument(
        "--output-dir", type=Path, default=repository / "translations" / "scenario_export"
    )
    arguments = parser.parse_args()
    scenario_dir = arguments.game_dir / "Scenario"
    files = sorted(
        path
        for pattern in ("*.ms", "*.mp", "*.mc")
        for path in scenario_dir.glob(pattern)
    )
    for source in files:
        subprocess.run(
            [
                sys.executable,
                "-B",
                str(Path(__file__).with_name("scenario_text_tool.py")),
                "extract",
                str(source),
                str(arguments.output_dir / f"{source.stem}.json"),
            ],
            check=True,
        )
    print(f"Exported scenario text from {len(files)} files to: {arguments.output_dir}")


if __name__ == "__main__":
    main()
