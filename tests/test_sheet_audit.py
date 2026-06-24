import json
import plistlib
from pathlib import Path

from PIL import Image

from gd_tp_porter.plist_utils import save_plist
from gd_tp_porter.sheet_audit import audit_and_repair_sheet


def test_sin_png_devuelve_none(tmp_path: Path):
    result = audit_and_repair_sheet(tmp_path, "GJ_GameSheet04", "-uhd", None)
    assert result is None


def test_falta_plist_sin_referencia_se_saltea(tmp_path: Path):
    Image.new("RGBA", (10, 10)).save(tmp_path / "GJ_GameSheet04-uhd.png")
    result = audit_and_repair_sheet(tmp_path, "GJ_GameSheet04", "-uhd", None)
    assert result is not None
    assert result.skipped_reason is not None
    assert "no me pasaste" in result.skipped_reason


def test_falta_plist_con_referencia_que_coincide_se_pide_prestado(tmp_path: Path):
    pack_dir = tmp_path / "pack"
    ref_dir = tmp_path / "ref"
    pack_dir.mkdir()
    ref_dir.mkdir()

    # el pack tiene el png pero no el plist
    Image.new("RGBA", (64, 32)).save(pack_dir / "GJ_GameSheet04-uhd.png")

    # la referencia tiene los dos, mismas dimensiones
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


def test_falta_plist_con_referencia_que_no_coincide_se_saltea(tmp_path: Path):
    pack_dir = tmp_path / "pack"
    ref_dir = tmp_path / "ref"
    pack_dir.mkdir()
    ref_dir.mkdir()

    Image.new("RGBA", (64, 32)).save(pack_dir / "GJ_GameSheet04-uhd.png")
    # el png de referencia mide OTRA cosa -> tiene que negarse a adivinar
    Image.new("RGBA", (999, 999)).save(ref_dir / "GJ_GameSheet04-uhd.png")
    save_plist(ref_dir / "GJ_GameSheet04-uhd.plist", {
        "frames": {},
        "metadata": {"size": "{999,999}"},
    })

    result = audit_and_repair_sheet(pack_dir, "GJ_GameSheet04", "-uhd", ref_dir)

    assert result is not None
    assert result.fixed is False
    assert result.skipped_reason is not None
    assert "seguro es distinto" in result.skipped_reason
    assert not (pack_dir / "GJ_GameSheet04-uhd.plist").is_file()


def test_metadata_size_viejo_se_corrige(tmp_path: Path):
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


def test_sheet_que_ya_esta_bien_no_se_toca(tmp_path: Path):
    Image.new("RGBA", (64, 32)).save(tmp_path / "GJ_GameSheet03-uhd.png")
    save_plist(tmp_path / "GJ_GameSheet03-uhd.plist", {
        "frames": {},
        "metadata": {"size": "{64,32}"},
    })

    result = audit_and_repair_sheet(tmp_path, "GJ_GameSheet03", "-uhd", None)

    assert result is not None
    assert result.fixed is False
    assert result.skipped_reason is None


def test_referencia_liviana_con_sizes_json_tambien_funciona(tmp_path: Path):
    """
    la referencia que va empaquetada en el .exe no tiene los pngs reales
    (serian 20mb+ de pixeles que nunca miramos) -- solo un sizes.json con
    las dimensiones de cada uno. esto tiene que servir igual que tener
    el png real.
    """
    pack_dir = tmp_path / "pack"
    ref_dir = tmp_path / "ref_liviana"
    pack_dir.mkdir()
    ref_dir.mkdir()

    Image.new("RGBA", (64, 32)).save(pack_dir / "GJ_GameSheet04-uhd.png")

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
    # nada de .png en la referencia -- solo el json con el tamaño
    with open(ref_dir / "sizes.json", "w") as f:
        json.dump({"GJ_GameSheet04-uhd.png": [64, 32]}, f)

    result = audit_and_repair_sheet(pack_dir, "GJ_GameSheet04", "-uhd", ref_dir)

    assert result is not None
    assert result.fixed is True
    with open(pack_dir / "GJ_GameSheet04-uhd.plist", "rb") as f:
        data = plistlib.load(f)
    assert "GJ_dailyBtn_001.png" in data["frames"]
