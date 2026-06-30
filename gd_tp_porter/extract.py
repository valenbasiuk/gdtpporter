# nota sobre el .rar: muchos packs vienen en RAR5. el unrar-free de
# debian/ubuntu NO entiende RAR5, solo RAR4 para abajo, asi que se usa rarfile pero no se lol capaz falla

from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

try:
    import rarfile  # type: ignore

    HAVE_RARFILE = True
except ImportError:
    HAVE_RARFILE = False


class ExtractionError(RuntimeError):
    pass


def _try_rarfile(archive_path: Path, dest_dir: Path) -> bool:
    """
    intenta extraer con la libreria rarfile. solo cuenta como exito si
    extractall() termina sin tirar ninguna excepcion. una extraccion a
    medias que dejo algunos archivos sueltos es peor que nada, porque
    despues seguimos de largo pensando que el pack esta completo y no lo
    esta.
    """
    if not HAVE_RARFILE:
        return False
    try:
        with rarfile.RarFile(archive_path) as rf:
            rf.extractall(dest_dir)
        return True
    except Exception:
        return False


def _clear_dir(d: Path) -> None:
    """vacia la carpeta sin borrar la carpeta en si (puede ser un TemporaryDirectory que maneja otro)"""
    for child in d.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def _try_external_tool(archive_path: Path, dest_dir: Path) -> bool:
    """
    fallback a un binario de afuera que sepa leer RAR5. probamos
    unrar-free primero (corriendolo con dest_dir como cwd, asi anda mucho
    mejor que pasandole un path de salida explicito -- probado a las
    patadas, no se por que pero asi funciona), despues 7z/7za, despues
    bsdtar.
    """
    archive_abs = str(archive_path.resolve())

    for tool in ("unrar-free", "unrar"):
        if shutil.which(tool) is None:
            continue
        try:
            proc = subprocess.run(
                [tool, "x", "-y", archive_abs],
                cwd=str(dest_dir),
                capture_output=True,
                text=False,  # algunos nombres de archivo del rar no son utf-8 limpio
            )
            if proc.returncode == 0 and any(dest_dir.iterdir()):
                return True
        except OSError:
            continue

    for tool, args in (
        ("7z", ["x", f"-o{dest_dir}", "-y", str(archive_path)]),
        ("7za", ["x", f"-o{dest_dir}", "-y", str(archive_path)]),
        ("bsdtar", ["-xf", str(archive_path), "-C", str(dest_dir)]),
    ):
        if shutil.which(tool) is None:
            continue
        try:
            subprocess.run([tool, *args], check=True, capture_output=True, text=True)
            if any(dest_dir.iterdir()):
                return True
        except subprocess.CalledProcessError:
            continue
    return False


def extract_archive(archive_path: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    suffix = archive_path.suffix.lower()
    if suffix == ".zip":
        with zipfile.ZipFile(archive_path) as zf:
            zf.extractall(dest_dir)
        return
    if suffix == ".rar":
        if _try_rarfile(archive_path, dest_dir):
            return
        # si rarfile dejo basura a medio extraer, la limpiamos antes de
        # probar con la otra herramienta
        _clear_dir(dest_dir)
        if _try_external_tool(archive_path, dest_dir):
            return
        raise ExtractionError(
            "no pude extraer este .rar. muchos packs vienen en RAR5, que el "
            "unrar-free comun NO lee. instala alguno de estos y reintenta:\n"
            "  sudo apt install p7zip-full      (trae 7z, lee RAR5)\n"
            "  sudo apt install libarchive-tools (trae bsdtar)\n"
            "o el unrar real (no-free) de rarlab.com."
        )
    raise ExtractionError(f"tipo de archivo no soportado: {suffix} (solo .zip/.rar)")


def find_pack_root(extracted_dir: Path) -> Path:
    """
    busca a ojo la carpeta que tiene los sprites sueltos del pack,
    fijandose si hay algun GJ_GameSheet02*.png (eso lo tiene cualquier
    pack, sin excepcion).

    si extracted_dir ya es directamente esa carpeta (lo normal cuando el
    usuario apunta el programa a una carpeta ya extraida), se devuelve
    tal cual sin buscar nada mas.
    """
    if any(extracted_dir.glob("GJ_GameSheet02*.png")):
        return extracted_dir

    candidates = list(extracted_dir.rglob("GJ_GameSheet02*.png"))
    if candidates:
        return candidates[0].parent

    # si no encontramos el GameSheet02, al menos buscamos cualquier .plist
    # -- mejor que adivinar a ciegas la carpeta de arriba
    plist_candidates = list(extracted_dir.rglob("*.plist"))
    if plist_candidates:
        return plist_candidates[0].parent

    raise ExtractionError(
        f"no encontre ningun archivo de texture pack en {extracted_dir} "
        "(busque GJ_GameSheet02*.png y *.plist). seguro que esto es un "
        "texture pack de Geometry Dash?"
    )
