from pathlib import Path

import pytest

from gd_tp_porter.plist_utils import (
    Rect,
    fix_metadata_size,
    load_plist_repaired,
    parse_size,
    PlistRepairError,
)

PLIST_OK = b"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>frames</key>
    <dict>
        <key>spike_01_001.png</key>
        <dict>
            <key>spriteOffset</key>
            <string>{0,0}</string>
            <key>spriteSize</key>
            <string>{120,120}</string>
            <key>textureRect</key>
            <string>{{10,20},{120,120}}</string>
            <key>textureRotated</key>
            <false/>
        </dict>
    </dict>
    <key>metadata</key>
    <dict>
        <key>size</key>
        <string>{4096,4096}</string>
        <key>textureFileName</key>
        <string>test.png</string>
    </dict>
</dict>
</plist>
"""

# el mismo plist de arriba pero sin el <key>textureRotated</key> antes del
# <false/> -- el bug real que nos encontramos en un pack y que este modulo
# tiene que poder arreglar solo
PLIST_ROTO = PLIST_OK.replace(
    b"<key>textureRotated</key>\n            <false/>", b"<false/>"
)

PLIST_IRRECUPERABLE = b"esto ni cerca de ser un plist"


def test_rect_parse_y_vuelta():
    r = Rect.parse("{{10,20},{120,150}}")
    assert (r.x, r.y, r.w, r.h) == (10, 20, 120, 150)
    assert r.to_plist_string() == "{{10,20},{120,150}}"


def test_parse_size():
    assert parse_size("{4096,4096}") == (4096, 4096)


def test_carga_plist_que_ya_esta_bien(tmp_path: Path):
    p = tmp_path / "ok.plist"
    p.write_bytes(PLIST_OK)
    data, warnings = load_plist_repaired(p)
    assert warnings == []
    assert "spike_01_001.png" in data["frames"]


def test_carga_y_arregla_plist_roto(tmp_path: Path):
    p = tmp_path / "roto.plist"
    p.write_bytes(PLIST_ROTO)
    data, warnings = load_plist_repaired(p)
    assert len(warnings) == 1
    assert "arregle" in warnings[0]
    frame = data["frames"]["spike_01_001.png"]
    assert frame["textureRotated"] is False


def test_plist_irrecuperable_explota(tmp_path: Path):
    p = tmp_path / "basura.plist"
    p.write_bytes(PLIST_IRRECUPERABLE)
    with pytest.raises(PlistRepairError):
        load_plist_repaired(p)


def test_fix_metadata_size_corrige_si_esta_viejo():
    data = {"metadata": {"size": "{100,100}"}}
    msg = fix_metadata_size(data, (200, 300))
    assert msg is not None
    assert data["metadata"]["size"] == "{200,300}"


def test_fix_metadata_size_no_hace_nada_si_ya_esta_bien():
    data = {"metadata": {"size": "{200,300}"}}
    msg = fix_metadata_size(data, (200, 300))
    assert msg is None
    assert data["metadata"]["size"] == "{200,300}"
