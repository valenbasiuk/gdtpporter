import plistlib
from pathlib import Path

from PIL import Image

from gd_tp_porter.plist_utils import save_plist
from gd_tp_porter.sheet_audit import audit_and_repair_sheet


def test_missing_png_returns_none(tmp_path: Path):
    result = audit_and_repair_sheet(tmp_path, "GJ_GameSheet04", "-uhd", None)
    assert result is None


def test_missing_plist_without_reference_is_skipped(tmp_path: Path):
    Image.new("RGBA", (10, 10)).save(tmp_path / "GJ_GameSheet04-uhd.png")
    result = audit_and_repair_sheet(tmp_path, "GJ_GameSheet04", "-uhd", None)
    assert result is not None
    assert result.skipped_reason is not None
    assert "no reference" in result.skipped_reason


def test_missing_plist_with_matching_reference_is_borrowed(tmp_path: Path):
    pack_dir = tmp_path / "pack"
    ref_dir = tmp_path / "ref"
    pack_dir.mkdir()
    ref_dir.mkdir()

    # Pack has the PNG but no plist.
    Image.new("RGBA", (64, 32)).save(pack_dir / "GJ_GameSheet04-uhd.png")

    # Reference has both, same dimensions.
    Image.new("RGBA", (64, 32)).save(ref_dir / "GJ_GameSheet04-uhd.png")
    save_plist(ref_dir / "GJ_GameSheet04-uhd.plist", {
        "frames": {
            "GJ_dailyBtn_001.png": {
                "textureRect": "{{0,0},{32,32}}",
                "textureRotated": False,
            }
        },
        "metadata": {
            "size": "{64,32}",
            "realTextureFileName": "GJ_GameSheet04-uhd.png",
            "textureFileName": "GJ_GameSheet04-uhd.png",
        },
    })

    result = audit_and_repair_sheet(pack_dir, "GJ_GameSheet04", "-uhd", ref_dir)

    assert result is not None
    assert result.fixed is True
    assert (pack_dir / "GJ_GameSheet04-uhd.plist").is_file()

    with open(pack_dir / "GJ_GameSheet04-uhd.plist", "rb") as f:
        data = plistlib.load(f)
    assert "GJ_dailyBtn_001.png" in data["frames"]


def test_missing_plist_with_mismatched_reference_is_skipped(tmp_path: Path):
    pack_dir = tmp_path / "pack"
    ref_dir = tmp_path / "ref"
    pack_dir.mkdir()
    ref_dir.mkdir()

    Image.new("RGBA", (64, 32)).save(pack_dir / "GJ_GameSheet04-uhd.png")
    # Reference PNG has DIFFERENT dimensions -> must refuse to guess.
    Image.new("RGBA", (999, 999)).save(ref_dir / "GJ_GameSheet04-uhd.png")
    save_plist(ref_dir / "GJ_GameSheet04-uhd.plist", {
        "frames": {},
        "metadata": {"size": "{999,999}"},
    })

    result = audit_and_repair_sheet(pack_dir, "GJ_GameSheet04", "-uhd", ref_dir)

    assert result is not None
    assert result.fixed is False
    assert result.skipped_reason is not None
    assert "doesn't match" in result.skipped_reason
    assert not (pack_dir / "GJ_GameSheet04-uhd.plist").is_file()


def test_stale_metadata_size_is_corrected(tmp_path: Path):
    Image.new("RGBA", (64, 32)).save(tmp_path / "GJ_GameSheet03-uhd.png")
    save_plist(tmp_path / "GJ_GameSheet03-uhd.plist", {
        "frames": {},
        "metadata": {"size": "{1,1}"},
    })

    result = audit_and_repair_sheet(tmp_path, "GJ_GameSheet03", "-uhd", None)

    assert result is not None
    assert result.fixed is True
    with open(tmp_path / "GJ_GameSheet03-uhd.plist", "rb") as f:
        data = plistlib.load(f)
    assert data["metadata"]["size"] == "{64,32}"


def test_correct_sheet_is_left_alone(tmp_path: Path):
    Image.new("RGBA", (64, 32)).save(tmp_path / "GJ_GameSheet03-uhd.png")
    save_plist(tmp_path / "GJ_GameSheet03-uhd.plist", {
        "frames": {},
        "metadata": {"size": "{64,32}"},
    })

    result = audit_and_repair_sheet(tmp_path, "GJ_GameSheet03", "-uhd", None)

    assert result is not None
    assert result.fixed is False
    assert result.skipped_reason is None
