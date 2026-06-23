import plistlib
from pathlib import Path

from PIL import Image

from gd_tp_porter.plist_utils import save_plist
from gd_tp_porter.porter import port_pack


def _frame(x, y, w, h, rotated=False):
    return {
        "spriteOffset": "{0,0}",
        "spriteSize": f"{{{w},{h}}}",
        "spriteSourceSize": f"{{{w},{h}}}",
        "textureRect": f"{{{{{x},{y}}},{{{w},{h}}}}}",
        "textureRotated": rotated,
    }


def _armar_pack_minimo(pack_dir: Path) -> None:
    pack_dir.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", (50, 50)).save(pack_dir / "GJ_GameSheet02-uhd.png")
    save_plist(pack_dir / "GJ_GameSheet02-uhd.plist", {
        "frames": {"player_01_001.png": _frame(0, 0, 10, 10)},
        "metadata": {"size": "{50,50}"},
    })
    Image.new("RGBA", (50, 50)).save(pack_dir / "GJ_GameSheetGlow-uhd.png")
    save_plist(pack_dir / "GJ_GameSheetGlow-uhd.plist", {
        "frames": {},
        "metadata": {"size": "{50,50}"},
    })
    # GJ_GameSheet04 con png pero sin plist -- el bug real que encontramos
    Image.new("RGBA", (40, 40)).save(pack_dir / "GJ_GameSheet04-uhd.png")
    # hack viejo de fondo que tiene que desaparecer
    (pack_dir / "GDBackground.dll").write_bytes(b"esto no es una dll real")


def test_port_pack_de_punta_a_punta(tmp_path: Path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    _armar_pack_minimo(source)

    report = port_pack(source_dir=source, output_dir=output)

    # se separaron los iconos
    assert (output / "icons" / "player_01-uhd.png").is_file()

    # GameSheet04 quedo marcado como salteado (no le pase referencia)
    gs04_results = [r for r in report.sheet_results if r.basename == "GJ_GameSheet04"]
    assert len(gs04_results) == 1
    assert gs04_results[0].skipped_reason is not None

    # se saco el hack viejo
    assert not (output / "GDBackground.dll").is_file()
    assert "GDBackground.dll" in report.removed_files

    # el source no se toco para nada
    assert (source / "GDBackground.dll").is_file()


def test_port_pack_jamas_genera_el_sheet_ingame(tmp_path: Path):
    """
    este es EL test importante. ni aunque la carpeta de --reference
    tenga un GJ_GameSheet (sin numero) ahi adentro, portear un pack
    tiene que devolver algo que no lo incluya -- exactamente el error
    que cometimos a mano con los pinchos de WespTP. un pack que solo
    repinta menu/iconos tiene que salir del otro lado sin un sheet
    in-game que nunca trajo el solo.
    """
    source = tmp_path / "source"
    output = tmp_path / "output"
    reference = tmp_path / "reference"
    _armar_pack_minimo(source)

    reference.mkdir()
    Image.new("RGBA", (100, 100)).save(reference / "GJ_GameSheet-uhd.png")
    save_plist(reference / "GJ_GameSheet-uhd.plist", {
        "frames": {"spike_01_001.png": _frame(0, 0, 10, 10)},
        "metadata": {"size": "{100,100}"},
    })
    # tambien le damos una referencia de GameSheet04 que si coincide,
    # para que ese camino del codigo tambien se ejercite
    Image.new("RGBA", (40, 40)).save(reference / "GJ_GameSheet04-uhd.png")
    save_plist(reference / "GJ_GameSheet04-uhd.plist", {
        "frames": {"GJ_dailyBtn_001.png": _frame(0, 0, 10, 10)},
        "metadata": {"size": "{40,40}"},
    })

    report = port_pack(source_dir=source, output_dir=output, reference_dir=reference)

    # GameSheet04 SI se arreglo con la referencia (es un sheet de menu legitimo)
    gs04_results = [r for r in report.sheet_results if r.basename == "GJ_GameSheet04"]
    assert gs04_results[0].fixed is True

    # pero el sheet in-game (sin numero) no tiene que aparecer en la
    # salida bajo ningun concepto, aunque la referencia si lo tuviera
    assert not (output / "GJ_GameSheet-uhd.png").is_file()
    assert not (output / "GJ_GameSheet-uhd.plist").is_file()
    assert not (output / "GJ_GameSheet.png").is_file()
    assert not (output / "GJ_GameSheet-hd.png").is_file()


def test_port_pack_no_toca_el_sheet_ingame_si_el_pack_ya_trae_uno(tmp_path: Path):
    """
    si un pack SI trae su propio GJ_GameSheet (raro, pero algunas
    conversiones completas lo hacen), portear tiene que dejarlo
    exactamente como esta, no borrarlo ni reemplazarlo por nada.
    """
    source = tmp_path / "source"
    output = tmp_path / "output"
    _armar_pack_minimo(source)

    bytes_custom = b"este es el sheet in-game propio del pack"
    Image.new("RGBA", (20, 20)).save(source / "GJ_GameSheet-uhd.png")
    (source / "GJ_GameSheet-uhd.plist").write_bytes(bytes_custom)

    report = port_pack(source_dir=source, output_dir=output)

    out_plist = output / "GJ_GameSheet-uhd.plist"
    assert out_plist.is_file()
    assert out_plist.read_bytes() == bytes_custom
    assert not any("sague" in n for n in report.notes)
