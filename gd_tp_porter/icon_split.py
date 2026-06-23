# separa el sheet viejo de iconos (GJ_GameSheet02 + GJ_GameSheetGlow,
# todo amontonado en un solo archivo) en los sheets individuales por
# icono que pide 2.2 en Resources/icons/.
#
# esto es una reescritura de la idea de Weebifying en 2.2tpconvert
# (https://github.com/Weebifying/2.2tpconvert) -- el credito de haber
# descubierto como se tenia que separar esto es de ellos. lo que cambia
# aca: nada de regex para el textureRect (usamos plist_utils.Rect), anda
# para las 3 calidades ('', '-hd', '-uhd') en una sola pasada, y usa los
# arreglos de plist_utils para los plists rotos.

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from PIL import Image

from .plist_utils import Rect, load_plist_repaired, save_plist

Image.MAX_IMAGE_PIXELS = None  # los sheets uhd son grandes, no queremos que PIL se queje

ICON_PREFIXES = ("bird_", "dart_", "player_", "robot_", "ship_", "spider_")
FIREBOOST_KEY = "fireBoost_001.png"

QUALITY_SUFFIXES = ("", "-hd", "-uhd")


def _icon_group(frame_name: str) -> str:
    """
    a que grupo (= que sheet final) pertenece este frame.

    ej: 'player_03_001.png'        -> 'player_03'
        'player_ball_12_2_001.png' -> 'player_ball_12'
        'robot_05_glow_001.png'    -> 'robot_05'
        'fireBoost_001.png'        -> grupo propio, va solo
    """
    if frame_name == FIREBOOST_KEY:
        return frame_name
    parts = frame_name.split("_")
    if frame_name.startswith("player_ball_"):
        return f"player_ball_{parts[2]}"
    return f"{parts[0]}_{parts[1]}"


def _sprite_box(rect: Rect, sprite_size: tuple[int, int], rotated: bool) -> tuple[int, int, int, int]:
    """la caja (left, upper, right, lower) para recortar el frame del atlas ORIGINAL, ya tiendo en cuenta el textureRotated"""
    w, h = sprite_size
    if rotated:
        w, h = h, w
    return rect.x, rect.y, rect.x + w, rect.y + h


@dataclass
class IconSplitResult:
    quality_suffix: str
    icons_written: int
    warnings: list[str] = field(default_factory=list)


def split_icons_for_quality(
    pack_dir: Path,
    suffix: str,
    out_dir: Path,
) -> Optional[IconSplitResult]:
    """
    separa GJ_GameSheet02{suffix} + GJ_GameSheetGlow{suffix} en
    out_dir/icons/*.png + *.plist. devuelve None si no estan los 4
    archivos para esta calidad (no es error, la mayoria de los packs
    solo traen una o dos de las tres calidades).
    """
    gs02_plist_path = pack_dir / f"GJ_GameSheet02{suffix}.plist"
    gs02_png_path = pack_dir / f"GJ_GameSheet02{suffix}.png"
    glow_plist_path = pack_dir / f"GJ_GameSheetGlow{suffix}.plist"
    glow_png_path = pack_dir / f"GJ_GameSheetGlow{suffix}.png"

    required = [gs02_plist_path, gs02_png_path, glow_plist_path, glow_png_path]
    if not all(p.is_file() for p in required):
        return None

    warnings: list[str] = []

    gs02_data, w1 = load_plist_repaired(gs02_plist_path)
    glow_data, w2 = load_plist_repaired(glow_plist_path)
    warnings += w1 + w2

    gs02_image = Image.open(gs02_png_path).convert("RGBA")
    glow_image = Image.open(glow_png_path).convert("RGBA")

    gs02_frames: list[tuple[str, dict]] = list(gs02_data["frames"].items())
    glow_frames: list[tuple[str, dict]] = list(glow_data["frames"].items())

    def is_icon_frame(name: str) -> bool:
        return name.startswith(ICON_PREFIXES) or name == FIREBOOST_KEY

    # agrupamos cada frame que importa (base + glow) por grupo de icono,
    # en el orden que aparecen, salteando duplicados de glow que por algun
    # motivo tambien aparecen en GameSheet02 (pasa con algunos frames de robot)
    groups: dict[str, list[tuple[str, dict]]] = {}
    group_order: list[str] = []
    for name, frame in gs02_frames:
        if not is_icon_frame(name):
            continue
        grp = _icon_group(name)
        if grp not in groups:
            groups[grp] = []
            group_order.append(grp)
        groups[grp].append((name, frame))

    for name, frame in glow_frames:
        if not is_icon_frame(name):
            continue
        grp = _icon_group(name)
        if grp not in groups:
            # grupo que solo tiene glow, sin base. lo guardamos igual.
            groups[grp] = []
            group_order.append(grp)
        if any(existing_name == name for existing_name, _ in groups[grp]):
            continue
        groups[grp].append((name, frame))

    icons_dir = out_dir / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)

    icons_written = 0
    for grp in group_order:
        frames = groups[grp]
        if not frames:
            continue

        # primera pasada: cuanto ancho necesitamos en total (cada frame +
        # 1px de padding, asi queda igual al layout del tool original) y
        # cual es el alto maximo
        total_w = 0
        max_h = 0
        sized_frames = []
        for name, frame in frames:
            rect = Rect.parse(frame["textureRect"])
            sw, sh = _parse_curly_size(frame["spriteSize"])
            rotated = bool(frame["textureRotated"])
            draw_w, draw_h = (sh, sw) if rotated else (sw, sh)
            sized_frames.append((name, frame, rect, draw_w, draw_h, rotated))
            total_w += draw_w + 1
            max_h = max(max_h, draw_h)

        sheet = Image.new("RGBA", (max(total_w, 1), max(max_h, 1)), (0, 0, 0, 0))

        new_frames: dict[str, dict] = {}
        x_cursor = 0
        is_fireboost = grp == FIREBOOST_KEY
        for name, frame, rect, draw_w, draw_h, rotated in sized_frames:
            left, upper, right, lower = _sprite_box(
                rect, _parse_curly_size(frame["spriteSize"]), rotated
            )
            # el glow de bird/dart/player/ship hay que sacarlo del sheet
            # de glow, no del sheet base (robot/spider/ball no tienen
            # variante glow separada, asi que esos quedan afuera de esto)
            use_glow_source = (
                name.endswith("glow_001.png")
                and name.startswith(("bird_", "dart_", "player_", "ship_"))
            )
            source = glow_image if use_glow_source else gs02_image
            sprite = source.crop((left, upper, right, lower))
            sheet.paste(sprite, (x_cursor, 0))

            new_frame = dict(frame)
            new_frame["textureRect"] = Rect(x_cursor, 0, sprite.width, sprite.height).to_plist_string()
            new_frames[name] = new_frame
            x_cursor += sprite.width + 1

        icon_basename = "fireBoost_001" if is_fireboost else grp
        png_name = f"{icon_basename}{suffix}.png"
        plist_name = f"{icon_basename}{suffix}.plist"

        plist_data = {
            "frames": new_frames,
            "metadata": {
                "format": 3,
                "pixelFormat": "RGBA4444",
                "premultiplyAlpha": False,
                "realTextureFileName": f"icons/{png_name}",
                "size": f"{{{sheet.width},{sheet.height}}}",
                "smartupdate": "",
                "textureFileName": f"icons/{png_name}",
            },
        }

        sheet.save(icons_dir / png_name)
        save_plist(icons_dir / plist_name, plist_data)
        icons_written += 1

    return IconSplitResult(quality_suffix=suffix, icons_written=icons_written, warnings=warnings)


def _parse_curly_size(s: str) -> tuple[int, int]:
    # spriteSize / spriteSourceSize vienen como "{120,150}" -- mas simple
    # que el de textureRect porque no tiene las llaves dobles
    s = s.strip().strip("{}")
    w, h = s.split(",")
    return int(float(w)), int(float(h))


def split_all_icons(pack_dir: Path, out_dir: Path) -> list[IconSplitResult]:
    results = []
    for suffix in QUALITY_SUFFIXES:
        res = split_icons_for_quality(pack_dir, suffix, out_dir)
        if res is not None:
            results.append(res)
    return results
