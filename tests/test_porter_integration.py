import plistlib
from pathlib import Path

from PIL import Image

from gd_tp_porter.plist_utils import save_plist
from gd_tp_porter.porter import port_pack


def _make_frame(x, y, w, h, rotated=False):
    return {
        "spriteOffset": "{0,0}",
        "spriteSize": f"{{{w},{h}}}",
        "spriteSourceSize": f"{{{w},{h}}}",
        "textureRect": f"{{{{{x},{y}}},{{{w},{h}}}}}",
        "textureRotated": rotated,
    }


def _build_minimal_pack(pack_dir: Path) -> None:
    pack_dir.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", (50, 50)).save(pack_dir / "GJ_GameSheet02-uhd.png")
    save_plist(pack_dir / "GJ_GameSheet02-uhd.plist", {
        "frames": {"player_01_001.png": _make_frame(0, 0, 10, 10)},
        "metadata": {"size": "{50,50}"},
    })
    Image.new("RGBA", (50, 50)).save(pack_dir / "GJ_GameSheetGlow-uhd.png")
    save_plist(pack_dir / "GJ_GameSheetGlow-uhd.plist", {
        "frames": {},
        "metadata": {"size": "{50,50}"},
    })
    # GJ_GameSheet04 PNG with no plist (the real-world bug we found).
    Image.new("RGBA", (40, 40)).save(pack_dir / "GJ_GameSheet04-uhd.png")
    # A legacy background-swap hack file that should get dropped.
    (pack_dir / "GDBackground.dll").write_bytes(b"not a real dll")


def test_port_pack_end_to_end(tmp_path: Path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    _build_minimal_pack(source)

    report = port_pack(source_dir=source, output_dir=output)

    # Icons were split.
    assert (output / "icons" / "player_01-uhd.png").is_file()

    # GameSheet04 was correctly flagged as skipped (no reference given).
    gs04_results = [r for r in report.sheet_results if r.basename == "GJ_GameSheet04"]
    assert len(gs04_results) == 1
    assert gs04_results[0].skipped_reason is not None

    # Legacy hack file removed.
    assert not (output / "GDBackground.dll").is_file()
    assert "GDBackground.dll" in report.removed_files

    # Source untouched.
    assert (source / "GDBackground.dll").is_file()


def test_port_pack_never_creates_protected_ingame_sheet(tmp_path: Path):
    """Critical regression test: even when a reference dir DOES contain the
    in-game GJ_GameSheet (no numeric suffix), porting must never copy it
    into the output. This is the exact mistake made by hand in an earlier
    session — a pack that only re-skins menus/icons must come out the other
    end without an in-game sheet it never shipped itself."""
    source = tmp_path / "source"
    output = tmp_path / "output"
    reference = tmp_path / "reference"
    _build_minimal_pack(source)

    reference.mkdir()
    Image.new("RGBA", (100, 100)).save(reference / "GJ_GameSheet-uhd.png")
    save_plist(reference / "GJ_GameSheet-uhd.plist", {
        "frames": {"spike_01_001.png": _make_frame(0, 0, 10, 10)},
        "metadata": {"size": "{100,100}"},
    })
    # Also give a matching GJ_GameSheet04 reference so that path is exercised.
    Image.new("RGBA", (40, 40)).save(reference / "GJ_GameSheet04-uhd.png")
    save_plist(reference / "GJ_GameSheet04-uhd.plist", {
        "frames": {"GJ_dailyBtn_001.png": _make_frame(0, 0, 10, 10)},
        "metadata": {"size": "{40,40}"},
    })

    report = port_pack(source_dir=source, output_dir=output, reference_dir=reference)

    # GameSheet04 WAS fixed using the reference (legit numbered sheet).
    gs04_results = [r for r in report.sheet_results if r.basename == "GJ_GameSheet04"]
    assert gs04_results[0].fixed is True

    # But the in-game GJ_GameSheet (no number) must NOT appear anywhere in
    # the output, even though the reference dir had one available.
    assert not (output / "GJ_GameSheet-uhd.png").is_file()
    assert not (output / "GJ_GameSheet-uhd.plist").is_file()
    assert not (output / "GJ_GameSheet.png").is_file()
    assert not (output / "GJ_GameSheet-hd.png").is_file()


def test_port_pack_preserves_existing_ingame_sheet_if_pack_ships_one(tmp_path: Path):
    """If a pack DOES ship its own GJ_GameSheet (rare, but some full
    conversions do), porting must leave it completely untouched rather
    than deleting or replacing it."""
    source = tmp_path / "source"
    output = tmp_path / "output"
    _build_minimal_pack(source)

    custom_bytes = b"this is the pack's own custom in-game sheet"
    Image.new("RGBA", (20, 20)).save(source / "GJ_GameSheet-uhd.png")
    (source / "GJ_GameSheet-uhd.plist").write_bytes(custom_bytes)

    report = port_pack(source_dir=source, output_dir=output)

    out_plist = output / "GJ_GameSheet-uhd.plist"
    assert out_plist.is_file()
    assert out_plist.read_bytes() == custom_bytes
    assert not any("Removed unexpected" in n for n in report.notes)
