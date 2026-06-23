"""Extract a user-supplied pack archive (.zip or .rar) to a working
directory, then locate the actual folder containing the loose
.png/.plist/.fnt files (packs are often nested one or two folders deep,
e.g. "MyPack v2.0/MyPack/*.png").

RAR extraction note: many texture packs are distributed as RAR5 archives.
The classic 'unrar-free' tool on Debian/Ubuntu does NOT support RAR5, only
RAR4 and earlier, so `rarfile` (which shells out to it) fails with
"Cannot find working tool" even when something called "unrar" is on PATH.
We try rarfile first (works fine with the real, non-free unrar binary) and
fall back to calling `7z`/`7za`/`bsdtar` directly, all of which handle
RAR5 correctly.
"""
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
    """Try extracting with the rarfile library. Only counts as success if
    extractall() completes with no exception at all — a partial extract
    that happens to leave a few files behind is worse than no extraction,
    since it can silently produce an incomplete pack."""
    if not HAVE_RARFILE:
        return False
    try:
        with rarfile.RarFile(archive_path) as rf:
            rf.extractall(dest_dir)
        return True
    except Exception:
        return False


def _try_external_tool(archive_path: Path, dest_dir: Path) -> bool:
    """Fall back to a CLI tool that handles RAR5 (rarfile/unrar-free often
    can't, or only when invoked just right). Tries unrar-free (run with
    dest_dir as cwd — it handles that far more reliably than being given
    an explicit output path), then 7z/7za, then bsdtar."""
    archive_abs = str(archive_path.resolve())

    for tool in ("unrar-free", "unrar"):
        if shutil.which(tool) is None:
            continue
        try:
            proc = subprocess.run(
                [tool, "x", "-y", archive_abs],
                cwd=str(dest_dir),
                capture_output=True,
                text=False,
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
            subprocess.run(
                [tool, *args], check=True, capture_output=True, text=True
            )
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
        _clear_dir(dest_dir)
        if _try_external_tool(archive_path, dest_dir):
            return
        raise ExtractionError(
            "Couldn't extract this .rar file. Many texture packs use RAR5, "
            "which the common 'unrar-free' package can NOT read. Install "
            "one of the following and try again:\n"
            "  sudo apt install p7zip-full      (provides 7z, reads RAR5)\n"
            "  sudo apt install libarchive-tools (provides bsdtar)\n"
            "or install the real non-free 'unrar' binary from rarlab.com."
        )
    raise ExtractionError(f"Unsupported archive type: {suffix} (only .zip/.rar)")


def _clear_dir(d: Path) -> None:
    """Remove everything inside d without removing d itself (it may be a
    caller-managed TemporaryDirectory)."""
    for child in d.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def find_pack_root(extracted_dir: Path) -> Path:
    """Heuristically find the folder that actually contains the pack's
    loose sprite files, by looking for a known anchor file
    (GJ_GameSheet02*.png, the icon sheet every pack has).

    If extracted_dir itself already directly contains one (the common case
    when the user points the tool at an already-extracted pack folder),
    it's returned as-is without searching.
    """
    if any(extracted_dir.glob("GJ_GameSheet02*.png")):
        return extracted_dir

    candidates = list(extracted_dir.rglob("GJ_GameSheet02*.png"))
    if candidates:
        return candidates[0].parent
    # Fall back to any folder containing at least one .plist — still better
    # than guessing the top-level extraction dir blindly.
    plist_candidates = list(extracted_dir.rglob("*.plist"))
    if plist_candidates:
        return plist_candidates[0].parent
    raise ExtractionError(
        f"Couldn't find any texture pack files under {extracted_dir} "
        "(looked for GJ_GameSheet02*.png and *.plist). Is this really a "
        "Geometry Dash texture pack archive?"
    )
