from pathlib import Path

import pytest

from gd_tp_porter.plist_utils import (
    Rect,
    fix_metadata_size,
    load_plist_repaired,
    parse_size,
    PlistRepairError,
)

VALID_PLIST = b"""<?xml version="1.0" encoding="UTF-8"?>
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

# Same as above but missing the <key>textureRotated</key> before <false/>,
# which is the real-world corruption this tool was built to repair.
BROKEN_PLIST = VALID_PLIST.replace(
    b"<key>textureRotated</key>\n            <false/>", b"<false/>"
)

UNFIXABLE_PLIST = b"this is not a plist at all"


def test_rect_parse_roundtrip():
    r = Rect.parse("{{10,20},{120,150}}")
    assert (r.x, r.y, r.w, r.h) == (10, 20, 120, 150)
    assert r.to_plist_string() == "{{10,20},{120,150}}"


def test_parse_size():
    assert parse_size("{4096,4096}") == (4096, 4096)


def test_load_valid_plist(tmp_path: Path):
    p = tmp_path / "ok.plist"
    p.write_bytes(VALID_PLIST)
    data, warnings = load_plist_repaired(p)
    assert warnings == []
    assert "spike_01_001.png" in data["frames"]


def test_load_and_repair_broken_plist(tmp_path: Path):
    p = tmp_path / "broken.plist"
    p.write_bytes(BROKEN_PLIST)
    data, warnings = load_plist_repaired(p)
    assert len(warnings) == 1
    assert "repaired" in warnings[0]
    frame = data["frames"]["spike_01_001.png"]
    assert frame["textureRotated"] is False


def test_unfixable_plist_raises(tmp_path: Path):
    p = tmp_path / "garbage.plist"
    p.write_bytes(UNFIXABLE_PLIST)
    with pytest.raises(PlistRepairError):
        load_plist_repaired(p)


def test_fix_metadata_size_changes_stale_value():
    data = {"metadata": {"size": "{100,100}"}}
    msg = fix_metadata_size(data, (200, 300))
    assert msg is not None
    assert data["metadata"]["size"] == "{200,300}"


def test_fix_metadata_size_noop_when_already_correct():
    data = {"metadata": {"size": "{200,300}"}}
    msg = fix_metadata_size(data, (200, 300))
    assert msg is None
    assert data["metadata"]["size"] == "{200,300}"
