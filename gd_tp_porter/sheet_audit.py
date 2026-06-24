# revisa y arregla los sheets de menu/UI del pack (todo lo que NO sea el
# sheet in-game -- ver guardrails.py para el por que de esa separacion).
#
# 3 bugs que nos encontramos portando packs reales:
#
# 1. plist mal formado: un <true/>/<false/> sin su <key>textureRotated</key>
#    de antes. lo arregla plist_utils.load_plist_repaired.
#
# 2. metadata.size desactualizado: no afecta nada en el juego, pero lo
#    dejamos prolijo igual.
#
# 3. falta el plist directamente: hay un .png pero ningun .plist al lado
#    (nos paso con GJ_GameSheet04 en WespTP). sin el plist, Cocos2d no
#    tiene como saber donde cortar cada sprite, y esa parte de la UI sale
#    toda rota/recortada mal. no podemos inventar coordenadas para arte
#    custom de un pack, pero si la grilla del sheet coincide exacto con
#    el layout de GD vanilla (algo comun -- la mayoria de los packs solo
#    re-pintan sprites sin mover nada de lugar), podemos pedir prestadas
#    las coordenadas de un plist vanilla que sepamos que anda bien. esto
#    SOLO se hace cuando el png del pack mide exactamente lo mismo en
#    pixeles que el png de referencia -- es una señal fuerte (no perfecta,
#    pero fuerte) de que el layout es el mismo.
#
# sobre la carpeta de referencia: solo necesitamos el .plist (las
# coordenadas) y el TAMAÑO del .png de referencia, nunca sus pixeles. por
# eso una referencia puede venir de dos formas:
#   - "completa": carpeta con los .plist Y los .png reales (lo que armarias
#     a mano con una copia de Resources de GD)
#   - "liviana": carpeta con los .plist + un sizes.json mapeando
#     "Archivo.png" -> [ancho, alto]. esto es lo que va empaquetado adentro
#     del .exe, porque no tiene sentido cargar 20mb de pngs vanilla cuando
#     lo unico que miramos de ellos es el tamaño.

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from PIL import Image

from .plist_utils import (
    PlistRepairError,
    fix_metadata_size,
    load_plist_repaired,
    save_plist,
)

# sheets que en cualquier version de GD son pura UI/menu/iconos.
# A PROPOSITO no esta GJ_GameSheet (sin numero) -- ese es el sheet
# in-game (pinchos, bloques, orbes, decoraciones). la mayoria de los
# packs solo repintan menu/iconos y nunca tocan ese archivo. tratarlo
# como "falta" y rellenarlo con uno vanilla de otro lado puede romper
# una instalacion que ya andaba bien (el usuario ya tiene su propia
# copia correcta puesta por su GD). ver el README, sección de por qué.
MENU_SHEET_BASENAMES = [
    "GJ_GameSheet02",
    "GJ_GameSheet03",
    "GJ_GameSheet04",
    "GJ_GameSheetGlow",
    "GJ_LaunchSheet",
    "BE_GameSheet01",
    "GauntletSheet",
]
QUALITY_SUFFIXES = ("", "-hd", "-uhd")


def _reference_png_size(reference_dir: Path, png_name: str) -> Optional[tuple[int, int]]:
    """el tamaño del png de referencia, buscando primero en sizes.json (referencia liviana) y si no esta, abriendo el png real"""
    sizes_path = reference_dir / "sizes.json"
    if sizes_path.is_file():
        with open(sizes_path) as f:
            sizes = json.load(f)
        if png_name in sizes:
            w, h = sizes[png_name]
            return w, h
    png_path = reference_dir / png_name
    if png_path.is_file():
        return Image.open(png_path).size
    return None


@dataclass
class SheetAuditResult:
    basename: str
    suffix: str
    png_path: Path
    plist_path: Path
    had_plist: bool
    messages: list[str] = field(default_factory=list)
    fixed: bool = False
    skipped_reason: Optional[str] = None


def audit_and_repair_sheet(
    pack_dir: Path,
    basename: str,
    suffix: str,
    reference_dir: Optional[Path],
) -> Optional[SheetAuditResult]:
    """
    revisa un sheet (basename + suffix). devuelve None si el .png ni
    siquiera existe para esta combinacion (la mayoria de los packs no
    traen las 3 calidades).
    """
    png_path = pack_dir / f"{basename}{suffix}.png"
    plist_path = pack_dir / f"{basename}{suffix}.plist"

    if not png_path.is_file():
        return None

    result = SheetAuditResult(
        basename=basename,
        suffix=suffix,
        png_path=png_path,
        plist_path=plist_path,
        had_plist=plist_path.is_file(),
    )

    real_w, real_h = Image.open(png_path).size

    if not plist_path.is_file():
        if reference_dir is None:
            result.skipped_reason = (
                "falta el plist y no me pasaste un pack de referencia "
                "(usa --reference para pedirle prestadas las coordenadas "
                "a una copia vanilla)"
            )
            return result

        ref_plist_path = reference_dir / f"{basename}{suffix}.plist"
        if not ref_plist_path.is_file():
            result.skipped_reason = f"no encontre un plist de referencia para {basename}{suffix}"
            return result

        ref_size = _reference_png_size(reference_dir, f"{basename}{suffix}.png")
        if ref_size is None:
            result.skipped_reason = f"no encontre el tamaño del png de referencia para {basename}{suffix}"
            return result

        if ref_size != (real_w, real_h):
            result.skipped_reason = (
                f"el png mide {real_w}x{real_h} y el de referencia "
                f"{ref_size[0]}x{ref_size[1]} -- el layout seguro es distinto, "
                "mejor no adivinar coordenadas (se podria desalinear toda la UI)"
            )
            return result

        ref_data, ref_warnings = load_plist_repaired(ref_plist_path)

        # las dimensiones son idénticas: podemos reusar las coordenadas
        # del plist de referencia tal cual, solo apuntando al png de este pack
        ref_data["metadata"]["realTextureFileName"] = png_path.name
        ref_data["metadata"]["textureFileName"] = png_path.name
        save_plist(plist_path, ref_data)
        result.fixed = True
        result.messages.append(
            f"{plist_path.name} no existia; le pedi prestadas las coordenadas "
            f"a la referencia (mismas dimensiones {real_w}x{real_h}) porque "
            "el png de este pack coincide exacto con el layout vanilla"
        )
        result.messages += [f"(referencia) {w}" for w in ref_warnings]
        return result

    # el plist existe: arreglamos lo estructural + el metadata viejo
    try:
        data, warnings = load_plist_repaired(plist_path)
    except PlistRepairError as e:
        result.skipped_reason = str(e)
        return result

    result.messages += warnings
    size_msg = fix_metadata_size(data, (real_w, real_h))
    if size_msg:
        result.messages.append(f"{plist_path.name}: {size_msg}")

    if warnings or size_msg:
        save_plist(plist_path, data)
        result.fixed = True

    return result


def audit_and_repair_pack(
    pack_dir: Path,
    reference_dir: Optional[Path] = None,
) -> list[SheetAuditResult]:
    results = []
    for basename in MENU_SHEET_BASENAMES:
        for suffix in QUALITY_SUFFIXES:
            res = audit_and_repair_sheet(pack_dir, basename, suffix, reference_dir)
            if res is not None:
                results.append(res)
    return results
