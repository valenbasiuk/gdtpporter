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
from pathlib import Path

from .extract import ExtractionError
from .porter import port_input


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

    try:
        output_dir, report, zip_path = port_input(
            input_path,
            output_dir=args.output,
            reference_dir=args.reference,
            keep_legacy_hacks=args.keep_legacy_hacks,
            make_zip=args.zip,
        )
    except ExtractionError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    print(report.render())
    print()
    print(f"Listo. el pack porteado quedo en: {output_dir}")
    if zip_path is not None:
        print(f"Zipeado en: {zip_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
