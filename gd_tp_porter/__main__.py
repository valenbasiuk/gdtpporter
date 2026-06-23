"""Command-line entry point.

    python -m gd_tp_porter MyPack.rar
    python -m gd_tp_porter MyPack.rar --reference ./vanilla_2.2_sheets
    python -m gd_tp_porter ./MyPack_extracted_folder -o ./MyPack_2.2

Run `python -m gd_tp_porter --help` for all options.
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from .extract import ExtractionError, extract_archive, find_pack_root
from .porter import port_pack, zip_output


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gd_tp_porter",
        description=(
            "Port a Geometry Dash 2.1-era texture pack so it works on 2.2: "
            "splits player/ship/robot/etc icons into the per-icon sheets "
            "2.2 expects, and repairs a couple of known plist bugs found in "
            "real-world packs. Never touches in-game gameplay sprites."
        ),
    )
    p.add_argument(
        "input",
        type=Path,
        help="Path to the pack: a .zip/.rar archive, OR a folder that "
        "already contains the loose .png/.plist files.",
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output folder for the ported pack (default: <input-name>_2.2 "
        "next to the input).",
    )
    p.add_argument(
        "--zip",
        action="store_true",
        help="Also produce a .zip of the output folder, ready to share.",
    )
    p.add_argument(
        "--reference",
        type=Path,
        default=None,
        help="Optional folder with a known-good vanilla 2.2 Resources copy "
        "(loose .png/.plist files). Used ONLY to backfill a plist that's "
        "missing entirely (e.g. GJ_GameSheet04 with no .plist), and only "
        "when the pack's PNG is pixel-identical in size to the reference's "
        "— never for the in-game gameplay sheet.",
    )
    p.add_argument(
        "--keep-legacy-hacks",
        action="store_true",
        help="Don't remove old fan-made background-swap hack files "
        "(GDBackground.dll) that predate native custom-background support "
        "and aren't compatible with 2.2.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    input_path: Path = args.input

    if not input_path.exists():
        print(f"error: {input_path} does not exist", file=sys.stderr)
        return 1

    cleanup_tmp = None
    try:
        if input_path.is_file():
            cleanup_tmp = tempfile.TemporaryDirectory(prefix="gd_tp_porter_")
            extract_dir = Path(cleanup_tmp.name)
            print(f"Extracting {input_path.name} ...")
            try:
                extract_archive(input_path, extract_dir)
            except ExtractionError as e:
                print(f"error: {e}", file=sys.stderr)
                return 1
            pack_root = find_pack_root(extract_dir)
            default_name = input_path.stem
        else:
            pack_root = find_pack_root(input_path)
            default_name = input_path.name

        output_dir = args.output or input_path.parent / f"{default_name}_2.2"

        print(f"Pack root: {pack_root}")
        print(f"Output:    {output_dir}")
        print()

        report = port_pack(
            source_dir=pack_root,
            output_dir=output_dir,
            reference_dir=args.reference,
            keep_legacy_hacks=args.keep_legacy_hacks,
        )

        print(report.render())
        print()
        print(f"Done. Ported pack is at: {output_dir}")

        if args.zip:
            zip_path = zip_output(output_dir, output_dir.with_suffix(""))
            print(f"Zipped to: {zip_path}")

        return 0
    finally:
        if cleanup_tmp is not None:
            cleanup_tmp.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
