#!/usr/bin/env python3
"""Build a consolidated Dangerous Waters Chinese localization package from YAML."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import yaml


SCENARIO_SUFFIXES = {".ms", ".mp", ".mc"}


def main() -> None:
    repository = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=repository / "config" / "localization.yaml",
        help="YAML workflow configuration.",
    )
    parser.add_argument("--install", action="store_true", help="Copy built files into game_dir.")
    arguments = parser.parse_args()

    config = load_config(arguments.config)
    game_dir = resolve_path(config.get("game_dir", repository.parent / "Dangerous Waters"), repository)
    output_dir = resolve_path(config.get("output_dir", repository / "build" / "localized"), repository)
    package_dir = output_dir / "package"
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir(parents=True, exist_ok=True)

    runtime_config = config.get("runtime", {})
    scenario_config = config.get("scenarios", {})
    usni_config = config.get("usni", {})
    static_config = config.get("static_graphics", {})

    runtime_output = output_dir / "runtime"
    if runtime_config.get("enabled", True):
        build_runtime(repository, game_dir, runtime_output, runtime_config)
        copy_runtime_to_package(runtime_output, package_dir)

    if scenario_config.get("enabled", True):
        build_scenarios(repository, game_dir, output_dir, package_dir, scenario_config)

    if usni_config.get("enabled", True):
        build_usni(repository, game_dir, output_dir, package_dir, usni_config)

    if static_config.get("mainmenu", {}).get("enabled", False):
        build_mainmenu(repository, game_dir, output_dir, package_dir, static_config["mainmenu"])

    install_enabled = arguments.install or config.get("install", {}).get("enabled", False)
    if install_enabled:
        install_package(package_dir, game_dir)

    print(f"Localization package written to: {package_dir}")
    if not install_enabled:
        print("Use --install or set install.enabled: true to copy the package into the game directory.")


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise TypeError(f"{path} must contain a YAML mapping")
    return data


def resolve_path(value, repository: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else repository / path


def resolve_path_list(values, repository: Path) -> list[Path]:
    if values is None:
        return []
    if isinstance(values, (str, Path)):
        values = [values]
    return [resolve_path(value, repository) for value in values]


def run(command: list[str]) -> None:
    print(">", " ".join(f'"{part}"' if " " in part else part for part in command))
    subprocess.run(command, check=True)


def build_runtime(repository: Path, game_dir: Path, output: Path, config: dict) -> None:
    command = [
        sys.executable,
        "-B",
        str(repository / "scripts" / "build_utf8_fui_hook_poc.py"),
        "--game-dir",
        str(game_dir),
        "--output-dir",
        str(output),
    ]
    apptext_source = config.get("apptext_source")
    if apptext_source:
        command += ["--apptext-source", str(resolve_path(apptext_source, repository))]
    shared_source = config.get("shared_source")
    if shared_source:
        command += ["--shared-source", str(resolve_path(shared_source, repository))]
    wqy_pcf = config.get("wqy_pcf")
    if wqy_pcf:
        command += ["--wqy-pcf", str(resolve_path(wqy_pcf, repository))]
    if "cjk_glyph_size" in config:
        command += ["--cjk-glyph-size", str(config["cjk_glyph_size"])]
    if "cjk_advance_extra" in config:
        command += ["--cjk-advance-extra", str(config["cjk_advance_extra"])]
    if "cjk_skip_outline_layers" in config:
        command += [
            "--cjk-skip-outline-layers"
            if config["cjk_skip_outline_layers"]
            else "--no-cjk-skip-outline-layers"
        ]
    if "cjk_max_source_height" in config:
        command += ["--cjk-max-source-height", str(config["cjk_max_source_height"])]

    apptext_translations = resolve_path_list(config.get("apptext_translations"), repository)
    if apptext_translations:
        command += ["--translations", *[str(path) for path in apptext_translations]]
    font_text = resolve_path_list(config.get("font_text"), repository)
    if font_text:
        command += ["--font-text", *[str(path) for path in font_text]]
    run(command)


def copy_runtime_to_package(runtime_output: Path, package_dir: Path) -> None:
    copy_file(runtime_output / "dinput8.dll", package_dir / "dinput8.dll")
    copy_file(runtime_output / "AppTextE.dll", package_dir / "AppTextE.dll")
    copy_file(runtime_output / "Graphics" / "shared.ndx", package_dir / "Graphics" / "shared.ndx")
    copy_file(runtime_output / "Graphics" / "shared.grp", package_dir / "Graphics" / "shared.grp")


def build_scenarios(
    repository: Path, game_dir: Path, output_dir: Path, package_dir: Path, config: dict
) -> None:
    source_dir = resolve_path(config.get("source_dir", game_dir / "Scenario"), repository)
    suffix = config.get("suffix", "_zh")
    translations = resolve_translation_paths(resolve_path_list(config.get("translations"), repository))
    if not translations:
        print("No scenario translations found; skipping scenario patching.")
        return
    scenario_output_dir = output_dir / "scenarios"
    scenario_output_dir.mkdir(parents=True, exist_ok=True)
    for translation in translations:
        source_stem = translation.stem.removesuffix(suffix)
        candidates = [
            path for path in source_dir.glob(f"{source_stem}.*") if path.suffix.lower() in SCENARIO_SUFFIXES
        ]
        if len(candidates) != 1:
            raise ValueError(f"Expected one scenario source for {translation.name}: {candidates}")
        patched = scenario_output_dir / candidates[0].name
        run(
            [
                sys.executable,
                "-B",
                str(repository / "scripts" / "scenario_text_tool.py"),
                "patch",
                str(candidates[0]),
                str(translation),
                str(patched),
            ]
        )
        copy_file(patched, package_dir / "Scenario" / patched.name)


def build_usni(repository: Path, game_dir: Path, output_dir: Path, package_dir: Path, config: dict) -> None:
    translations = resolve_path_list(config.get("translations"), repository)
    if not translations:
        print("No USNI translations configured; skipping USNI package.")
        return
    usni_output = output_dir / "usni"
    run(
        [
            sys.executable,
            "-B",
            str(repository / "scripts" / "usni_text_tool.py"),
            "--game-dir",
            str(game_dir),
            "--output-dir",
            str(usni_output),
            "--translations",
            *[str(path) for path in translations],
        ]
    )
    copy_file(usni_output / "Graphics" / "usnidata.ndx", package_dir / "Graphics" / "usnidata.ndx")
    copy_file(usni_output / "Graphics" / "usnidata.grp", package_dir / "Graphics" / "usnidata.grp")


def build_mainmenu(repository: Path, game_dir: Path, output_dir: Path, package_dir: Path, config: dict) -> None:
    mainmenu_output = output_dir / "mainmenu"
    run(
        [
            sys.executable,
            "-B",
            str(repository / "scripts" / "build_mainmenu_poc.py"),
            "--game-dir",
            str(game_dir),
            "--output-dir",
            str(mainmenu_output),
        ]
    )
    copy_file(mainmenu_output / "Graphics" / "mainmenu.ndx", package_dir / "Graphics" / "mainmenu.ndx")
    copy_file(mainmenu_output / "Graphics" / "mainmenu.grp", package_dir / "Graphics" / "mainmenu.grp")


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
            resolved.append(absolute)
    return resolved


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def install_package(package_dir: Path, game_dir: Path) -> None:
    for source in package_dir.rglob("*"):
        if source.is_file():
            destination = game_dir / source.relative_to(package_dir)
            copy_file(source, destination)
    print(f"Installed localization package into: {game_dir}")


if __name__ == "__main__":
    main()
