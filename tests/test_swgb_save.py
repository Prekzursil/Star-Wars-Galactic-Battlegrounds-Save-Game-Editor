# mypy: disable-error-code=assignment

import io
import runpy
import struct
import sys
import zlib
import builtins
from pathlib import Path

import pytest

import swgb_save


def _player_blob(name: str, values: tuple[float, float, float, float]) -> bytes:
    pattern = bytes.fromhex("16db00000021")
    return (
        b"\x00" * 8
        + b"\x09\x00"
        + name.encode("ascii")
        + b"\x00"
        + b"\x00" * 8
        + pattern
        + struct.pack("<ffff", *values)
        + b"\x00" * 16
    )


def _raw_deflate(payload: bytes) -> bytes:
    compressor = zlib.compressobj(level=9, method=zlib.DEFLATED, wbits=-15)
    return compressor.compress(payload) + compressor.flush()


def test_hex_dump_formats_offsets_and_ascii() -> None:
    save = swgb_save.SaveGame("dummy.ga2")

    rendered = save._hex_dump(b"AB\x00\x7f", offset=16, length=16)

    assert "00000010:" in rendered
    assert "41 42 00 7f" in rendered
    assert "|AB..|" in rendered


def test_read_raises_when_decompression_never_succeeds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "broken.ga2"
    path.write_bytes(b"not-a-save")

    def always_fail(_data: bytes, _wbits: int) -> bytes:
        raise zlib.error("boom")

    monkeypatch.setattr(swgb_save.zlib, "decompress", always_fail)

    save = swgb_save.SaveGame(str(path))

    with pytest.raises(ValueError, match="Failed to decompress save file"):
        save.read()

    assert save.players == []
    assert save.wbits is None


def test_read_parses_player_resources_and_tracks_successful_wbits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "player.ga2"
    path.write_bytes(b"compressed-placeholder")
    payload = _player_blob("Player One", (10.0, 20.0, 30.0, 40.0))
    calls: list[int] = []

    def fake_decompress(_data: bytes, wbits: int) -> bytes:
        calls.append(wbits)
        if wbits != -15:
            raise zlib.error("wrong format")
        return payload

    monkeypatch.setattr(swgb_save.zlib, "decompress", fake_decompress)

    save = swgb_save.SaveGame(str(path))
    save.read()

    assert calls == [zlib.MAX_WBITS, 15, -15]
    assert save.wbits == -15
    assert [(player.name, player.index, player.resources) for player in save.players] == [
        ("Player One", 1, [20.0, 10.0, 30.0, 40.0])
    ]


def test_save_updates_resources_creates_backup_and_writes_compressed_bytes(tmp_path: Path) -> None:
    path = tmp_path / "edit.ga2"
    original_payload = _player_blob("Player One", (1.0, 2.0, 3.0, 4.0))
    original_compressed = _raw_deflate(original_payload)
    path.write_bytes(original_compressed)

    save = swgb_save.SaveGame(str(path))
    save.data = original_payload
    save.players = [swgb_save.Player("Player One", 1, [11.0, 22.0, 33.0, 44.0])]

    save.save()

    backup_path = path.with_suffix(path.suffix + ".backup")
    assert backup_path.exists()
    restored = zlib.decompress(path.read_bytes(), -15)
    pattern_pos = restored.find(bytes.fromhex("16db00000021"))
    resource_start = pattern_pos + 6
    written = struct.unpack("<ffff", restored[resource_start : resource_start + 16])
    assert written == pytest.approx((11.0, 22.0, 33.0, 44.0))


def test_print_info_lists_players(capsys: pytest.CaptureFixture[str]) -> None:
    save = swgb_save.SaveGame("dummy.ga2")
    save.data = b"x" * 12
    save.players = [swgb_save.Player("Player One", 1, [100.0, 200.0, 300.0, 400.0])]

    save.print_info()

    captured = capsys.readouterr().out
    assert "Save File: dummy.ga2" in captured
    assert "Player One (Player 1)" in captured
    assert "Food:" in captured
    assert "Wood:" in captured


def test_print_info_requires_loaded_data() -> None:
    save = swgb_save.SaveGame("dummy.ga2")

    with pytest.raises(ValueError, match="No save data loaded"):
        save.print_info()


def test_main_shows_usage_without_path(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["swgb_save.py"])

    with pytest.raises(SystemExit) as exc:
        swgb_save.main()

    assert exc.value.code == 1
    output = capsys.readouterr().out
    assert "Usage: python swgb_save.py <save_file>" in output


def test_main_reads_and_prints_when_given_a_path(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    events: list[tuple[str, str]] = []

    class FakeSaveGame:
        def __init__(self, filename: str):
            events.append(("init", filename))

        def read(self) -> None:
            events.append(("read", ""))

        def print_info(self) -> None:
            events.append(("print_info", ""))

    monkeypatch.setattr(swgb_save, "SaveGame", FakeSaveGame)
    monkeypatch.setattr(sys, "argv", ["swgb_save.py", "example.ga2"])

    swgb_save.main()

    assert events == [("init", "example.ga2"), ("read", ""), ("print_info", "")]
    assert capsys.readouterr().out == ""


def test_read_reports_when_no_players_are_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "empty.ga2"
    path.write_bytes(b"compressed-placeholder")
    monkeypatch.setattr(swgb_save.zlib, "decompress", lambda _data, _wbits: b"\x00" * 80)

    save = swgb_save.SaveGame(str(path))
    save.read()

    assert save.players == []
    output = capsys.readouterr().out
    assert "Could not find any player entries" in output


def test_find_player_entries_handles_marker_and_direct_name_fallbacks(
    capsys: pytest.CaptureFixture[str],
) -> None:
    pattern = bytes.fromhex("16db00000021")
    payload = (
        b"\x00" * 12
        + b"\x09\x00\xff\x00"
        + b"@@@"
        + b"Han Solo\x00"
        + b"\x00" * 8
        + pattern
        + struct.pack("<ffff", 10.0, 20.0, 30.0, 40.0)
        + b"\x00" * 32
    )
    save = swgb_save.SaveGame("dummy.ga2")
    save.data = payload

    save._find_player_entries()

    assert [(player.name, player.resources) for player in save.players] == [
        ("Han Solo", [20.0, 10.0, 30.0, 40.0])
    ]
    output = capsys.readouterr().out
    assert "Found name 'Han Solo'" in output


def test_find_player_entries_handles_direct_name_decode_errors() -> None:
    pattern = bytes.fromhex("16db00000021")
    payload = b"\x00" * 12 + (b"\xe9" * 4) + b"\x00" + b"\x00" * 8 + pattern + struct.pack("<ffff", 1.0, 2.0, 3.0, 4.0) + b"\x00" * 32
    save = swgb_save.SaveGame("dummy.ga2")
    save.data = payload

    save._find_player_entries()

    assert save.players == [swgb_save.Player("Player 1", 1, [2.0, 1.0, 3.0, 4.0])]


def test_find_player_entries_handles_direct_name_scan_exceptions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pattern = bytes.fromhex("16db00000021")
    payload = (
        b"\x00" * 12
        + b"Han Solo\x00"
        + b"\x00" * 8
        + pattern
        + struct.pack("<ffff", 1.0, 2.0, 3.0, 4.0)
        + b"\x00" * 32
    )
    save = swgb_save.SaveGame("dummy.ga2")
    save.data = payload
    real_chr = builtins.chr

    def flaky_chr(value: int):
        if value == ord("S"):
            raise RuntimeError("chr boom")
        return real_chr(value)

    monkeypatch.setattr(builtins, "chr", flaky_chr)

    save._find_player_entries()

    assert save.players == [swgb_save.Player("Player 1", 1, [2.0, 1.0, 3.0, 4.0])]


def test_find_player_entries_skips_out_of_range_resource_sequences() -> None:
    pattern = bytes.fromhex("16db00000021")
    payload = pattern + struct.pack("<ffff", 1.0, 2.0, 3.0, 100001.0) + b"\x00" * 48
    save = swgb_save.SaveGame("dummy.ga2")
    save.data = payload

    save._find_player_entries()

    assert save.players == []


def test_find_player_entries_handles_unpack_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pattern = bytes.fromhex("16db00000021")
    payload = pattern + struct.pack("<ffff", 1.0, 2.0, 3.0, 4.0) + b"\x00" * 48
    save = swgb_save.SaveGame("dummy.ga2")
    save.data = payload
    real_unpack = swgb_save.struct.unpack
    calls = {"count": 0}

    def flaky_unpack(fmt: str, data: bytes):
        calls["count"] += 1
        if calls["count"] == 4:
            raise struct.error("truncated")
        return real_unpack(fmt, data)

    monkeypatch.setattr(swgb_save.struct, "unpack", flaky_unpack)

    save._find_player_entries()

    assert save.players == []


def test_find_player_entries_logs_processing_errors(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = _player_blob("Player One", (10.0, 20.0, 30.0, 40.0))
    save = swgb_save.SaveGame("dummy.ga2")
    save.data = payload

    class BrokenPlayers(list):
        def append(self, _item):
            raise RuntimeError("boom")

    save.players = BrokenPlayers()

    save._find_player_entries()

    assert "Error processing pattern" in capsys.readouterr().out


def test_find_player_entries_returns_empty_without_loaded_data() -> None:
    save = swgb_save.SaveGame("dummy.ga2")

    assert save._find_player_entries() == []


def test_save_updates_via_direct_name_match_and_warns_for_missing_players(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "direct.ga2"
    payload = (
        b"\x00" * 16
        + b"Han Solo\x00"
        + b"\x00" * 8
        + bytes.fromhex("16db00000021")
        + struct.pack("<ffff", 1.0, 2.0, 3.0, 4.0)
        + b"\x00" * 32
    )
    path.write_bytes(_raw_deflate(payload))

    save = swgb_save.SaveGame(str(path))
    save.data = payload
    save.players = [
        swgb_save.Player("Han Solo", 1, [11.0, 22.0, 33.0, 44.0]),
        swgb_save.Player("Leia", 2, [1.0, 2.0, 3.0, 4.0]),
    ]

    save.save()

    restored = zlib.decompress(path.read_bytes(), -15)
    pattern_pos = restored.find(bytes.fromhex("16db00000021"))
    resource_start = pattern_pos + 6
    assert struct.unpack("<ffff", restored[resource_start : resource_start + 16]) == pytest.approx(
        (11.0, 22.0, 33.0, 44.0)
    )
    output = capsys.readouterr().out
    assert "Found potential name (direct): 'Han Solo'" in output
    assert "Warning: Could not update resources for players: {'Leia'}" in output


def test_save_requires_loaded_data(tmp_path: Path) -> None:
    save = swgb_save.SaveGame(str(tmp_path / "missing.ga2"))

    with pytest.raises(ValueError, match="No save data loaded"):
        save.save()


def test_save_continues_after_name_processing_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "broken-save.ga2"
    payload = _player_blob("Player One", (1.0, 2.0, 3.0, 4.0))
    path.write_bytes(_raw_deflate(payload))

    save = swgb_save.SaveGame(str(path))
    save.data = payload
    save.players = [swgb_save.Player("Player One", 1, [11.0, 22.0, 33.0, 44.0])]

    monkeypatch.setattr(swgb_save.struct, "pack", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("pack boom")))

    save.save()

    output = capsys.readouterr().out
    assert "Warning: Could not update resources for players" in output


def test_save_logs_mismatched_written_values_for_direct_name_updates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "mismatch.ga2"
    payload = (
        b"\x00" * 16
        + b"Han Solo\x00"
        + b"\x00" * 8
        + bytes.fromhex("16db00000021")
        + struct.pack("<ffff", 1.0, 2.0, 3.0, 4.0)
        + b"\x00" * 32
    )
    path.write_bytes(_raw_deflate(payload))

    save = swgb_save.SaveGame(str(path))
    save.data = payload
    save.players = [swgb_save.Player("Han Solo", 1, [11.0, 22.0, 33.0, 44.0])]
    real_pack = swgb_save.struct.pack

    def wrong_pack(fmt: str, value: float):
        return real_pack(fmt, value + 1.0)

    monkeypatch.setattr(swgb_save.struct, "pack", wrong_pack)

    save.save()

    assert "WARNING: Resource value mismatch!" in capsys.readouterr().out


def test_save_handles_invalid_direct_name_characters(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "invalid-direct.ga2"
    payload = (
        b"\x00" * 16
        + b"Han!\x00"
        + b"\x00" * 8
        + bytes.fromhex("16db00000021")
        + struct.pack("<ffff", 1.0, 2.0, 3.0, 4.0)
        + b"\x00" * 32
    )
    path.write_bytes(_raw_deflate(payload))

    save = swgb_save.SaveGame(str(path))
    save.data = payload
    save.players = [swgb_save.Player("Han", 1, [11.0, 22.0, 33.0, 44.0])]

    save.save()

    assert "Warning: Could not update resources for players: {'Han'}" in capsys.readouterr().out


def test_save_skips_direct_name_candidates_with_invalid_characters(
    tmp_path: Path
) -> None:
    path = tmp_path / "direct-invalid.ga2"
    payload = (
        b"\x00" * 16
        + b"Han!\x00"
        + b"\x00" * 8
        + bytes.fromhex("16db00000021")
        + struct.pack("<ffff", 1.0, 2.0, 3.0, 4.0)
        + b"\x00" * 32
    )
    path.write_bytes(_raw_deflate(payload))

    save = swgb_save.SaveGame(str(path))
    save.data = payload
    save.players = []

    save.save()


def test_save_logs_outer_processing_warning_when_search_setup_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "outer-warning.ga2"
    payload = _player_blob("Player One", (1.0, 2.0, 3.0, 4.0))
    path.write_bytes(_raw_deflate(payload))

    save = swgb_save.SaveGame(str(path))
    save.data = payload
    save.players = [swgb_save.Player("Player One", 1, [11.0, 22.0, 33.0, 44.0])]
    real_max = builtins.max
    call_count = {"count": 0}

    def flaky_max(*args, **kwargs):
        call_count["count"] += 1
        if call_count["count"] == 1:
            raise RuntimeError("max boom")
        return real_max(*args, **kwargs)

    monkeypatch.setattr(builtins, "max", flaky_max)

    save.save()
    assert builtins.max(1, 2) == 2

    assert "Warning: Error processing pattern" in capsys.readouterr().out


def test_save_raises_when_compression_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "compress-fail.ga2"
    payload = _player_blob("Player One", (1.0, 2.0, 3.0, 4.0))
    path.write_bytes(_raw_deflate(payload))

    save = swgb_save.SaveGame(str(path))
    save.data = payload
    save.players = []

    monkeypatch.setattr(
        swgb_save.zlib,
        "compressobj",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("compress boom")),
    )

    with pytest.raises(RuntimeError, match="compress boom"):
        save.save()

    assert "Error saving file: compress boom" in capsys.readouterr().out


def test_main_reports_errors_when_read_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class FakeSaveGame:
        def __init__(self, _filename: str):
            return None

        def read(self) -> None:
            raise RuntimeError("boom")

        def print_info(self) -> None:
            raise AssertionError("print_info should not run")

    with pytest.raises(AssertionError, match="print_info should not run"):
        FakeSaveGame("ignored").print_info()

    monkeypatch.setattr(swgb_save, "SaveGame", FakeSaveGame)
    monkeypatch.setattr(sys, "argv", ["swgb_save.py", "broken.ga2"])

    with pytest.raises(SystemExit) as exc:
        swgb_save.main()

    assert exc.value.code == 1
    assert "Error: boom" in capsys.readouterr().out


def test_running_swgb_save_as_main_executes_entrypoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    save_path = tmp_path / "script-run.ga2"
    save_path.write_bytes(_raw_deflate(_player_blob("Player One", (1.0, 2.0, 3.0, 4.0))))
    monkeypatch.setattr(sys, "argv", ["swgb_save.py", str(save_path)])

    runpy.run_path(str(Path(swgb_save.__file__)), run_name="__main__")

    output = capsys.readouterr().out
    assert "Save File:" in output
    assert "Player One" in output
