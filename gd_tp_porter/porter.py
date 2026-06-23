"""Top-level orchestration: take a 2.1-era texture pack folder and produce
a 2.2-compatible Resources folder (+ optional zip), with a full report of
what was changed, skipped, or flagged for manual attention.
"""
from __future__ import annotations

import shutil
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
        lines.append("=== Icon sheet splitting (player/ship/robot/etc -> icons/) ===")
        if not self.icon_results:
            lines.append("  No GJ_GameSheet02 + GJ_GameSheetGlow pair found at any quality level.")
        for r in self.icon_results:
            label = r.quality_suffix or "(base/low quality)"
            lines.append(f"  [{label}] wrote {r.icons_written} icon sheets")
            for w in r.warnings:
                lines.append(f"    ! {w}")
        lines.append("")
        lines.append("=== Menu/UI sheet audit ===")
        for r in self.sheet_results:
            tag = f"{r.basename}{r.suffix}"
            if r.skipped_reason:
                lines.append(f"  [{tag}] SKIPPED: {r.skipped_reason}")
            elif r.fixed:
                lines.append(f"  [{tag}] fixed:")
                for m in r.messages:
                    lines.append(f"    - {m}")
            else:
                lines.append(f"  [{tag}] OK, no changes needed")
        if self.removed_files:
            lines.append("")
            lines.append("=== Removed (not needed / not compatible with 2.2) ===")
            for f in self.removed_files:
                lines.append(f"  - {f}")
        if self.notes:
            lines.append("")
            lines.append("=== Notes ===")
            for n in self.notes:
                lines.append(f"  - {n}")
        return "\n".join(lines)


# Files associated with old fan-made background-swap hacks that predate
# native custom-background support and are not compatible with 2.2.
LEGACY_HACK_FILES = {"GDBackground.dll"}


def port_pack(
    source_dir: Path,
    output_dir: Path,
    reference_dir: Optional[Path] = None,
    keep_legacy_hacks: bool = False,
) -> PortReport:
    """Port a single texture pack folder (already extracted, containing the
    loose .png/.plist/.fnt/.ogg files exactly as they'd sit in Resources/).

    output_dir is created fresh as a copy of source_dir, then modified in
    place: icons/ added, sheets repaired, legacy hack files optionally
    dropped. source_dir is never modified.
    """
    if output_dir.exists():
        shutil.rmtree(output_dir)
    shutil.copytree(source_dir, output_dir)

    report = PortReport()

    icon_results = split_all_icons(output_dir, output_dir)
    report.icon_results = icon_results

    sheet_results = audit_and_repair_pack(output_dir, reference_dir=reference_dir)
    report.sheet_results = sheet_results

    if not keep_legacy_hacks:
        for fname in LEGACY_HACK_FILES:
            fpath = output_dir / fname
            if fpath.is_file():
                fpath.unlink()
                report.removed_files.append(fname)

    # Defensive check: make sure nothing in the output tree is one of the
    # protected in-game sheet files unless it was already present in the
    # *source* (i.e. this pack genuinely ships its own, which we leave
    # alone — we just never add one ourselves).
    for protected in PROTECTED_BASENAMES:
        for ext in (".png", ".plist"):
            candidate = output_dir / f"{protected}{ext}"
            existed_in_source = (source_dir / f"{protected}{ext}").is_file()
            if candidate.is_file() and not existed_in_source:
                # Should be unreachable given the rest of this tool never
                # writes these names, but if it ever happens, fail loudly
                # rather than ship a possibly-mismatched in-game sheet.
                candidate.unlink()
                report.notes.append(
                    f"Removed unexpected {candidate.name}: this tool never "
                    "creates the in-game gameplay sheet. If you need this "
                    "fixed, the pack's own /Resources is missing it and "
                    "your existing Geometry Dash install already supplies "
                    "a correct copy — no action needed."
                )

    report.notes.append(
        "This tool never touches GJ_GameSheet / -hd / -uhd (no numeric "
        "suffix) — the in-game gameplay sheet. If this pack ships its own "
        "copy it was left untouched; if not, your existing GD install "
        "supplies it and nothing further is needed."
    )

    return report


def zip_output(output_dir: Path, zip_path: Path) -> Path:
    """Zip output_dir's *contents* (not the folder itself) into zip_path."""
    if zip_path.suffix == ".zip":
        zip_path = zip_path.with_suffix("")
    archive = shutil.make_archive(str(zip_path), "zip", root_dir=str(output_dir))
    return Path(archive)
