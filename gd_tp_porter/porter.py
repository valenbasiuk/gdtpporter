# orquesta todo el proceso: agarra una carpeta de pack 2.1 y devuelve una
# carpeta Resources lista para 2.2 (+ zip si se pide), con un reporte de
# todo lo que se cambio, se salteo, o quedo pendiente de revisar a mano.

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .guardrails import PROTECTED_BASENAMES
from .icon_split import split_all_icons
from .sheet_audit import audit_and_repair_pack


@dataclass
class PortReport:
    icon_results: list = field(default_factory=list)
    sheet_results: list = field(default_factory=list)
    removed_files: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def render(self) -> str:
        lines = []
        lines.append("=== Separacion de iconos (player/ship/robot/etc -> icons/) ===")
        if not self.icon_results:
            lines.append("  no encontre el par GJ_GameSheet02 + GJ_GameSheetGlow en ninguna calidad.")
        for r in self.icon_results:
            label = r.quality_suffix or "(calidad base/low)"
            lines.append(f"  [{label}] {r.icons_written} sheets de icono generados")
            for w in r.warnings:
                lines.append(f"    ! {w}")
        lines.append("")
        lines.append("=== Auditoria de sheets de menu/UI ===")
        for r in self.sheet_results:
            tag = f"{r.basename}{r.suffix}"
            if r.skipped_reason:
                lines.append(f"  [{tag}] SALTEADO: {r.skipped_reason}")
            elif r.fixed:
                lines.append(f"  [{tag}] arreglado:")
                for m in r.messages:
                    lines.append(f"    - {m}")
            else:
                lines.append(f"  [{tag}] OK, no hacia falta nada")
        if self.removed_files:
            lines.append("")
            lines.append("=== Archivos sacados (no hacen falta / no andan en 2.2) ===")
            for f in self.removed_files:
                lines.append(f"  - {f}")
        if self.notes:
            lines.append("")
            lines.append("=== Notas ===")
            for n in self.notes:
                lines.append(f"  - {n}")
        return "\n".join(lines)


# archivos de hacks viejos de fans para cambiar el fondo, de antes de que
# GD soportara fondos custom nativamente. no sirven en 2.2.
LEGACY_HACK_FILES = {"GDBackground.dll"}


def port_pack(
    source_dir: Path,
    output_dir: Path,
    reference_dir: Optional[Path] = None,
    keep_legacy_hacks: bool = False,
) -> PortReport:
    """
    portea un pack (carpeta ya extraida, con los .png/.plist/.fnt/.ogg
    sueltos tal como irian en Resources/).

    output_dir se crea como copia de source_dir y de ahi en mas se
    modifica solo esa copia: se le agrega icons/, se le arreglan los
    sheets, se le sacan los hacks viejos si corresponde. source_dir nunca
    se toca.
    """
    if output_dir.exists():
        shutil.rmtree(output_dir)
    shutil.copytree(source_dir, output_dir)

    report = PortReport()

    report.icon_results = split_all_icons(output_dir, output_dir)
    report.sheet_results = audit_and_repair_pack(output_dir, reference_dir=reference_dir)

    if not keep_legacy_hacks:
        for fname in LEGACY_HACK_FILES:
            fpath = output_dir / fname
            if fpath.is_file():
                fpath.unlink()
                report.removed_files.append(fname)

    # chequeo de seguridad extra: que no haya quedado ningun archivo
    # protegido (el sheet in-game) en la salida, a menos que YA estuviera
    # en el pack original. esto en teoria nunca deberia dispararse porque
    # el resto del programa ni intenta escribir esos nombres, pero si
    # llegara a pasar, mejor fallar fuerte que entregar un sheet in-game
    # que capaz no coincide con la version de GD del usuario.
    for protected in PROTECTED_BASENAMES:
        for ext in (".png", ".plist"):
            candidate = output_dir / f"{protected}{ext}"
            existed_in_source = (source_dir / f"{protected}{ext}").is_file()
            if candidate.is_file() and not existed_in_source:
                candidate.unlink()
                report.notes.append(
                    f"sague {candidate.name} sin querer: este programa no "
                    "genera el sheet in-game bajo ninguna circunstancia. si "
                    "el pack original no lo tenia, tu GD ya te lo da puesto "
                    "-- no hace falta hacer nada mas."
                )

    report.notes.append(
        "este programa nunca toca GJ_GameSheet / -hd / -uhd (sin numero) -- "
        "el sheet in-game. si el pack traia su propia copia, se dejo como "
        "estaba; si no la traia, tu instalacion de GD ya te la da y no hace "
        "falta nada mas."
    )

    return report


def zip_output(output_dir: Path, zip_path: Path) -> Path:
    """zipea el CONTENIDO de output_dir (no la carpeta en si) en zip_path"""
    if zip_path.suffix == ".zip":
        zip_path = zip_path.with_suffix("")
    archive = shutil.make_archive(str(zip_path), "zip", root_dir=str(output_dir))
    return Path(archive)


def port_input(
    input_path: Path,
    output_dir: Optional[Path] = None,
    reference_dir: Optional[Path] = None,
    keep_legacy_hacks: bool = False,
    make_zip: bool = False,
) -> tuple[Path, PortReport, Optional[Path]]:
    """
    version "te lo resuelvo todo" de port_pack: recibe directamente lo
    que el usuario tenga a mano (un .zip/.rar, o una carpeta ya
    extraida), se encarga de extraer si hace falta, encuentra donde
    estan los archivos sueltos del pack, y llama a port_pack.

    esto existe para que el CLI (__main__.py) y el modo drag-and-drop
    (gui_entry.py, el que termina en el .exe) usen exactamente el mismo
    camino de codigo y no se desincronicen con el tiempo.

    devuelve (output_dir, reporte, ruta_del_zip_o_None).
    """
    # import acá adentro y no arriba del archivo para no obligar a quien
    # solo usa port_pack a tambien tener que lidiar con la extraccion de
    # archivos (cosas distintas, modulos distintos)
    from .extract import extract_archive, find_pack_root

    cleanup_tmp = None
    try:
        if input_path.is_file():
            cleanup_tmp = tempfile.TemporaryDirectory(prefix="gd_tp_porter_")
            extract_dir = Path(cleanup_tmp.name)
            extract_archive(input_path, extract_dir)
            pack_root = find_pack_root(extract_dir)
            default_name = input_path.stem
        else:
            pack_root = find_pack_root(input_path)
            default_name = input_path.name

        final_output_dir = output_dir or input_path.parent / f"{default_name}_2.2"

        report = port_pack(
            source_dir=pack_root,
            output_dir=final_output_dir,
            reference_dir=reference_dir,
            keep_legacy_hacks=keep_legacy_hacks,
        )

        zip_path = None
        if make_zip:
            zip_path = zip_output(final_output_dir, final_output_dir.with_suffix(""))

        return final_output_dir, report, zip_path
    finally:
        if cleanup_tmp is not None:
            cleanup_tmp.cleanup()
