"""Shared helpers for reading/writing Cocos2d-style .plist sprite atlases
and doing basic geometry on textureRect/spriteSize style strings.

Geometry Dash texture packs use the old-style "TexturePacker" plist format:
    <key>frames</key>
    <dict>
        <key>some_001.png</key>
        <dict>
            <key>textureRect</key>
            <string>{{x,y},{w,h}}</string>
            <key>textureRotated</key>
            <false/>
            ...
        </dict>
    </dict>

A handful of real-world packs ship plists with a single stray <true/> or
<false/> that is missing its preceding <key>textureRotated</key> tag. This
breaks plistlib (and Cocos2d itself). We detect and repair that here instead
of relying on regex on the raw XML.
"""
from __future__ import annotations

import plistlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

RECT_RE = re.compile(r"\{\{(-?\d+),(-?\d+)\},\{(-?\d+),(-?\d+)\}\}")
SIZE_RE = re.compile(r"\{(-?\d+),(-?\d+)\}")


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    w: int
    h: int

    @classmethod
    def parse(cls, s: str) -> "Rect":
        m = RECT_RE.match(s.strip())
        if not m:
            raise ValueError(f"Not a textureRect string: {s!r}")
        x, y, w, h = map(int, m.groups())
        return cls(x, y, w, h)

    def to_plist_string(self) -> str:
        return f"{{{{{self.x},{self.y}}},{{{self.w},{self.h}}}}}"


def parse_size(s: str) -> tuple[int, int]:
    m = SIZE_RE.match(s.strip())
    if not m:
        raise ValueError(f"Not a size string: {s!r}")
    return int(m.group(1)), int(m.group(2))


def format_size(w: int, h: int) -> str:
    return f"{{{w},{h}}}"


class PlistRepairError(RuntimeError):
    """Raised when a plist is too malformed to safely auto-repair."""


def load_plist_repaired(path: Path) -> tuple[dict, list[str]]:
    """Load a sprite-atlas plist, auto-repairing known-benign corruption.

    Returns (plist_dict, warnings). Raises PlistRepairError if the file
    can't be parsed even after the known fixups.

    Known fixup: a `<true/>` or `<false/>` for `textureRotated` that lost
    its `<key>textureRotated</key>` predecessor (seen in the wild in at
    least one widely-distributed pack). We only insert the missing key
    when doing so is unambiguous: the bare bool tag must immediately
    follow a `<string>...</string>` (the textureRect or spriteSourceSize
    value that always precedes textureRotated in TexturePacker output).
    """
    raw = path.read_bytes()
    warnings: list[str] = []
    try:
        return plistlib.loads(raw), warnings
    except Exception:
        pass

    text = raw.decode("utf-8", errors="replace")
    fixed, n = re.subn(
        r"(</string>\s*)(<(?:true|false)/>)",
        r"\1<key>textureRotated</key>\n                \2",
        text,
    )
    if n:
        try:
            data = plistlib.loads(fixed.encode("utf-8"))
            warnings.append(
                f"{path.name}: repaired {n} missing <key>textureRotated</key> tag(s)"
            )
            return data, warnings
        except Exception as e:
            raise PlistRepairError(
                f"{path.name}: still invalid after attempted repair: {e}"
            )
    raise PlistRepairError(f"{path.name}: could not parse and no known fixup applied")


def save_plist(path: Path, data: dict) -> None:
    with open(path, "wb") as f:
        plistlib.dump(data, f)


def fix_metadata_size(data: dict, real_size: tuple[int, int]) -> Optional[str]:
    """Correct a stale metadata.size field in place. Returns a warning
    string if a correction was made, else None.

    metadata.size is informational only (Cocos2d does not use it to find
    sprites — textureRect coordinates are absolute pixel offsets into the
    real PNG) but several real packs ship a stale value left over from an
    older export. We fix it for cleanliness / future tooling, not because
    it affects in-game rendering.
    """
    meta = data.get("metadata", {})
    declared = meta.get("size")
    real_str = format_size(*real_size)
    if declared != real_str:
        meta["size"] = real_str
        data["metadata"] = meta
        return f"metadata.size was {declared}, corrected to {real_str}"
    return None
