"""Audit and repair the menu/UI sprite sheets of a Geometry Dash texture
pack (everything except the in-game gameplay sheet, which this tool never
touches — see README for why).

Three classes of issue, all discovered by porting real-world packs:

1. Malformed plist: a `<true/>`/`<false/>` missing its preceding
   `<key>textureRotated</key>`. Repaired by plist_utils.load_plist_repaired.
2. Stale metadata.size: cosmetic only, doesn't affect rendering, but we
   correct it for cleanliness.
3. Missing plist entirely: a .png exists with no matching .plist (seen with
   GJ_GameSheet04 in the wild). Cocos2d/Cocos2d-x cannot load loose sprites
   without an atlas descriptor, and the affected UI falls back to broken/
   misplaced fragments. We can't invent coordinates for a pack's *custom*
   artwork, but if the menu sheet's grid matches vanilla GD's layout
   (common — most packs only re-skin sprites without moving them), we can
   safely borrow the *coordinates* from a known-good vanilla plist of the
   same dimensions. We only do this when the PNG's pixel dimensions exactly
   match the reference plist's declared size, which is a strong (though not
   airtight) signal that the layout matches too.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from PIL import Image

from .plist_utils import (
    PlistRepairError,
    fix_metadata_size,
    load_plist_repaired,
    parse_size,
    save_plist,
)

# Sheets that are exclusively menu/UI/icons in every known GD release.
# Deliberately NOT included: GJ_GameSheet{,-hd,-uhd} (no number suffix) —
# that is the in-game gameplay sheet (spikes, blocks, orbs, decorations).
# Most texture packs only re-skin menus/icons and never touch it; treating
# it as "missing" and backfilling it from vanilla has been observed to
# *break* a working install (the user's own GD already supplies a correct,
# version-matched copy). See README "Why we never touch GJ_GameSheet".
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
    """Check one (basename, suffix) sheet pair. Returns None if the PNG
    doesn't exist at all for this combination (most packs don't ship every
    quality level)."""
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
                "plist is missing and no reference pack was supplied "
                "(pass --reference to borrow coordinates from a vanilla copy)"
            )
            return result
        ref_plist_path = reference_dir / f"{basename}{suffix}.plist"
        ref_png_path = reference_dir / f"{basename}{suffix}.png"
        if not (ref_plist_path.is_file() and ref_png_path.is_file()):
            result.skipped_reason = f"no reference plist found for {basename}{suffix}"
            return result

        ref_data, ref_warnings = load_plist_repaired(ref_plist_path)
        ref_w, ref_h = Image.open(ref_png_path).size
        if (ref_w, ref_h) != (real_w, real_h):
            result.skipped_reason = (
                f"PNG size {real_w}x{real_h} doesn't match reference "
                f"{ref_w}x{ref_h} — layout likely differs, refusing to "
                "guess coordinates (would risk misaligned UI)"
            )
            return result

        # Dimensions match exactly: safe to reuse the reference plist's
        # frame coordinates verbatim, just repointed at this pack's PNG.
        ref_data["metadata"]["realTextureFileName"] = png_path.name
        ref_data["metadata"]["textureFileName"] = png_path.name
        save_plist(plist_path, ref_data)
        result.fixed = True
        result.messages.append(
            f"{plist_path.name} was missing entirely; borrowed coordinates "
            f"from reference (same {real_w}x{real_h} dimensions) since this "
            "pack's PNG matches the vanilla layout size exactly"
        )
        result.messages += [f"(reference) {w}" for w in ref_warnings]
        return result

    # plist exists: repair structural issues + stale metadata.
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
