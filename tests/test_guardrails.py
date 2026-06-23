from pathlib import Path

import pytest

from gd_tp_porter.guardrails import (
    ProtectedFileError,
    assert_not_protected,
    filter_out_protected,
)


@pytest.mark.parametrize(
    "filename",
    ["GJ_GameSheet.png", "GJ_GameSheet.plist", "GJ_GameSheet-hd.png", "GJ_GameSheet-uhd.plist"],
)
def test_protected_files_raise(filename: str):
    with pytest.raises(ProtectedFileError):
        assert_not_protected(Path(filename))


@pytest.mark.parametrize(
    "filename",
    [
        "GJ_GameSheet02.png",
        "GJ_GameSheet02-uhd.plist",
        "GJ_GameSheet03-hd.png",
        "GJ_GameSheet04.plist",
        "GJ_GameSheetGlow-uhd.png",
    ],
)
def test_numbered_sheets_are_not_protected(filename: str):
    # Should not raise: numbered/named variants are legitimately customized
    # by texture packs and are NOT the in-game gameplay sheet.
    assert_not_protected(Path(filename))


def test_filter_out_protected_splits_correctly():
    paths = [
        Path("GJ_GameSheet-uhd.png"),
        Path("GJ_GameSheet02-uhd.png"),
        Path("icons/player_01-uhd.png"),
    ]
    safe, rejected = filter_out_protected(paths)
    assert Path("GJ_GameSheet-uhd.png") in rejected
    assert Path("GJ_GameSheet02-uhd.png") in safe
    assert Path("icons/player_01-uhd.png") in safe
    assert len(safe) == 2
    assert len(rejected) == 1
