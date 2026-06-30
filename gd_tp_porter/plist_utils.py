# cositas para leer/escribir los plist de los atlas de sprites (formato
# viejo de TexturePacker que usa GD). un frame normal se ve asi:

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
            raise ValueError(f"esto no es un textureRect: {s!r}")
        x, y, w, h = map(int, m.groups())
        return cls(x, y, w, h)

    def to_plist_string(self) -> str:
        return f"{{{{{self.x},{self.y}}},{{{self.w},{self.h}}}}}"


def parse_size(s: str) -> tuple[int, int]:
    m = SIZE_RE.match(s.strip())
    if not m:
        raise ValueError(f"esto no es un size: {s!r}")
    return int(m.group(1)), int(m.group(2))


def format_size(w: int, h: int) -> str:
    return f"{{{w},{h}}}"


class PlistRepairError(RuntimeError):
    """el plist esta tan roto que no nos animamos a arreglarlo solos"""


def load_plist_repaired(path: Path) -> tuple[dict, list[str]]:
    """
    carga un plist de atlas de sprites, arreglando la corrupcion conocida
    si hace falta.

    devuelve (plist_dict, warnings). si no se puede ni con el fixup, PlistRepairError
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
                f"{path.name}: arregle {n} <key>textureRotated</key> que faltaba(n)"
            )
            return data, warnings
        except Exception as e:
            raise PlistRepairError(
                f"{path.name}: sigue invalido despues de intentar arreglarlo: {e}"
            )
    raise PlistRepairError(f"{path.name}: no se pudo parsear y no aplica ningun fixup conocido")


def save_plist(path: Path, data: dict) -> None:
    with open(path, "wb") as f:
        plistlib.dump(data, f)


def fix_metadata_size(data: dict, real_size: tuple[int, int]) -> Optional[str]:
    meta = data.get("metadata", {})
    declared = meta.get("size")
    real_str = format_size(*real_size)
    if declared != real_str:
        meta["size"] = real_str
        data["metadata"] = meta
        return f"metadata.size decia {declared}, lo corregi a {real_str}"
    return None
