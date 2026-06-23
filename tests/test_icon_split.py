# tests del icon_split con atlas sinteticos chiquitos -- no son sheets
# reales de GD, solo lo minimo para probar el agrupado/recorte/reescritura
# sin tener que meter pngs de varios MB en el repo como fixture

from pathlib import Path

from PIL import Image

from gd_tp_porter.icon_split import split_icons_for_quality
from gd_tp_porter.plist_utils import save_plist


def _frame(x, y, w, h, rotated=False):
    return {
        "spriteOffset": "{0,0}",
        "spriteSize": f"{{{w},{h}}}",
        "spriteSourceSize": f"{{{w},{h}}}",
        "textureRect": f"{{{{{x},{y}}},{{{w},{h}}}}}",
        "textureRotated": rotated,
    }


def _imagen_solida(size, color=(255, 0, 0, 255)):
    return Image.new("RGBA", size, color)


def test_split_basico(tmp_path: Path):
    # un GJ_GameSheet02 sintetico con dos frames de player y uno de robot,
    # mas un glow sheet con un glow de player
    gs02_img = _imagen_solida((100, 50))
    glow_img = _imagen_solida((100, 50), color=(0, 255, 0, 255))

    gs02_frames = {
        "player_01_001.png": _frame(0, 0, 10, 10),
        "player_01_2_001.png": _frame(10, 0, 10, 10),
        "robot_01_001.png": _frame(20, 0, 15, 15),
        "fireBoost_001.png": _frame(0, 20, 8, 8),
    }
    glow_frames = {
        "player_01_glow_001.png": _frame(0, 0, 12, 12),
    }

    gs02_img.save(tmp_path / "GJ_GameSheet02-uhd.png")
    save_plist(tmp_path / "GJ_GameSheet02-uhd.plist", {
        "frames": gs02_frames,
        "metadata": {"size": "{100,50}"},
    })
    glow_img.save(tmp_path / "GJ_GameSheetGlow-uhd.png")
    save_plist(tmp_path / "GJ_GameSheetGlow-uhd.plist", {
        "frames": glow_frames,
        "metadata": {"size": "{100,50}"},
    })

    out_dir = tmp_path / "out"
    result = split_icons_for_quality(tmp_path, "-uhd", out_dir)

    assert result is not None
    assert result.warnings == []
    # 3 grupos: player_01, robot_01, fireBoost_001
    assert result.icons_written == 3

    icons_dir = out_dir / "icons"
    assert (icons_dir / "player_01-uhd.png").is_file()
    assert (icons_dir / "player_01-uhd.plist").is_file()
    assert (icons_dir / "robot_01-uhd.png").is_file()
    assert (icons_dir / "fireBoost_001-uhd.png").is_file()

    # el sheet de player_01 tiene que tener sus 3 frames (2 base + 1 glow)
    import plistlib
    with open(icons_dir / "player_01-uhd.plist", "rb") as f:
        player_plist = plistlib.load(f)
    assert set(player_plist["frames"].keys()) == {
        "player_01_001.png",
        "player_01_2_001.png",
        "player_01_glow_001.png",
    }


def test_split_sin_los_archivos_necesarios_devuelve_none(tmp_path: Path):
    # no hay ni GJ_GameSheet02 ni Glow para esta calidad
    result = split_icons_for_quality(tmp_path, "-uhd", tmp_path / "out")
    assert result is None


def test_split_arregla_plist_roto(tmp_path: Path):
    gs02_img = _imagen_solida((50, 50))
    glow_img = _imagen_solida((50, 50))

    gs02_img.save(tmp_path / "GJ_GameSheet02-uhd.png")
    glow_img.save(tmp_path / "GJ_GameSheetGlow-uhd.png")

    # plist de GameSheet02 con el bug del textureRotated sin su key
    xml_roto = b"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>frames</key>
    <dict>
        <key>dart_01_001.png</key>
        <dict>
            <key>spriteOffset</key>
            <string>{0,0}</string>
            <key>spriteSize</key>
            <string>{10,10}</string>
            <key>spriteSourceSize</key>
            <string>{10,10}</string>
            <key>textureRect</key>
            <string>{{0,0},{10,10}}</string>
            <false/>
        </dict>
    </dict>
    <key>metadata</key>
    <dict>
        <key>size</key>
        <string>{50,50}</string>
    </dict>
</dict>
</plist>
"""
    (tmp_path / "GJ_GameSheet02-uhd.plist").write_bytes(xml_roto)
    save_plist(tmp_path / "GJ_GameSheetGlow-uhd.plist", {
        "frames": {},
        "metadata": {"size": "{50,50}"},
    })

    out_dir = tmp_path / "out"
    result = split_icons_for_quality(tmp_path, "-uhd", out_dir)

    assert result is not None
    assert result.icons_written == 1
    assert any("arregle" in w for w in result.warnings)
    assert (out_dir / "icons" / "dart_01-uhd.png").is_file()
