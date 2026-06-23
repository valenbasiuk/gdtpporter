"""Guard against the single most damaging mistake this tool could make:
touching the in-game gameplay sheet (GJ_GameSheet / -hd / -uhd, no number).

Background: most Geometry Dash texture packs only re-skin menus and player
icons. They never modify spikes, blocks, orbs, or other gameplay sprites,
which all live in GJ_GameSheet{,-hd,-uhd} (no numeric suffix — easy to
confuse with GJ_GameSheet02). An earlier version of the manual process this
tool automates incorrectly "fixed" a pack's missing icon sheet by copying in
a vanilla GJ_GameSheet from an unrelated GD install. That copy was not
guaranteed to byte-match the user's actual game version, and it broke
in-game decorative spikes that had been rendering fine using the user's own
real copy.

The fix was simply: don't. If a pack doesn't ship GJ_GameSheet itself, leave
it alone and let the user's existing GD installation supply it, as it always
did before the port.

This module exists so that's enforced in code, not just in a comment: any
attempt to write one of these filenames anywhere in the output tree raises.
"""
from __future__ import annotations

from pathlib import Path

# Matches GJ_GameSheet.png/.plist, GJ_GameSheet-hd.*, GJ_GameSheet-uhd.*
# but NOT GJ_GameSheet02 / 03 / 04 / Glow (those are numbered/named
# variants that texture packs legitimately do ship and customize).
PROTECTED_BASENAMES = {"GJ_GameSheet", "GJ_GameSheet-hd", "GJ_GameSheet-uhd"}


class ProtectedFileError(RuntimeError):
    pass


def assert_not_protected(path: Path) -> None:
    stem = path.stem  # filename without extension
    if stem in PROTECTED_BASENAMES:
        raise ProtectedFileError(
            f"Refusing to write {path.name}: this is the in-game gameplay "
            "sheet, which texture packs almost never ship and this tool "
            "must never fabricate or copy in from elsewhere. The user's "
            "own Geometry Dash installation already provides a correct, "
            "version-matched copy — overwriting it can only make things "
            "worse. If this specific pack genuinely does customize "
            "in-game sprites, copy that file in by hand; don't automate it."
        )


def filter_out_protected(paths: list[Path]) -> tuple[list[Path], list[Path]]:
    """Split a list of candidate output paths into (safe, rejected)."""
    safe, rejected = [], []
    for p in paths:
        if p.stem in PROTECTED_BASENAMES:
            rejected.append(p)
        else:
            safe.append(p)
    return safe, rejected
