# entrada por consola.
#
#   python -m gd_tp_porter MiPack.rar
#   python -m gd_tp_porter MiPack.rar --reference ./sheets_vanilla_2.2
#   python -m gd_tp_porter ./MiPack_carpeta_ya_extraida -o ./MiPack_2.2
#
# python -m gd_tp_porter --help para ver todas las opciones.

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
            "portea un texture pack de Geometry Dash de la era 2.1 para que "
            "ande en 2.2: separa los iconos de player/ship/robot/etc en los "
            "sheets individuales que pide 2.2, y arregla un par de bugs de "
            "plist que aparecen en packs reales. nunca toca sprites in-game."
        ),
    )
    p.add_argument(
        "input",
        type=Path,
        help="el pack: un .zip/.rar, O una carpeta que ya tiene los .png/.plist sueltos.",
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="carpeta de salida del pack ya porteado (por defecto: <nombre>_2.2 al lado del input)",
    )
    p.add_argument(
        "--zip",
        action="store_true",
        help="ademas genera un .zip de la carpeta de salida, listo para compartir",
    )
    p.add_argument(
        "--reference",
        type=Path,
        default=None,
        help="carpeta opcional con una copia vanilla de Resources de 2.2 (.png/.plist "
        "sueltos). se usa SOLO para rellenar un plist que falta por completo "
        "(ej: GJ_GameSheet04 sin .plist), y solo cuando el png del pack mide "
        "exactamente lo mismo que el de la referencia -- nunca para el sheet in-game.",
    )
    p.add_argument(
        "--keep-legacy-hacks",
        action="store_true",
        help="no borrar los hacks viejos de fondo custom (GDBackground.dll) que ya "
        "no hacen falta y no andan en 2.2",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    input_path: Path = args.input

    if not input_path.exists():
        print(f"error: {input_path} no existe", file=sys.stderr)
        return 1

    cleanup_tmp = None
    try:
        if input_path.is_file():
            cleanup_tmp = tempfile.TemporaryDirectory(prefix="gd_tp_porter_")
            extract_dir = Path(cleanup_tmp.name)
            print(f"Extrayendo {input_path.name} ...")
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
        print(f"Salida:    {output_dir}")
        print()

        report = port_pack(
            source_dir=pack_root,
            output_dir=output_dir,
            reference_dir=args.reference,
            keep_legacy_hacks=args.keep_legacy_hacks,
        )

        print(report.render())
        print()
        print(f"Listo. el pack porteado quedo en: {output_dir}")

        if args.zip:
            zip_path = zip_output(output_dir, output_dir.with_suffix(""))
            print(f"Zipeado en: {zip_path}")

        return 0
    finally:
        if cleanup_tmp is not None:
            cleanup_tmp.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
