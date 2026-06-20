"""Branch-completeness tests for swgb_save.

These exercise the loop-exit and conditional-false branches that the
behaviour-focused suite in test_swgb_save.py does not reach, so the lean
gate's STRICT 100% line+branch coverage is met with real assertions (no
pragmas). Each test targets a specific partial branch reported by
`coverage --branch`.
"""

from __future__ import absolute_import, division

# pylint: disable=protected-access
import struct
from pathlib import Path
from typing import Optional

import swgb_save


def test_name_from_direct_scan_consumes_full_name_window() -> None:
    """`_name_from_direct_scan` while-loop exits on `name_end == upper_bound`.

    Supplying MAX_NAME_BYTES consecutive valid name bytes (no NUL, no
    non-name byte) drives the loop to its `name_end < upper_bound` false
    exit (branch 140->147) rather than an early `break`.
    """
    save = swgb_save.SaveGame("dummy.ga2")
    name_bytes = b"A" * swgb_save.MAX_NAME_BYTES
    save.data = name_bytes + b"B" * 8

    result = save._name_from_direct_scan(0, search_end=len(save.data))

    assert result == "A" * swgb_save.MAX_NAME_BYTES  # nosec B101


def test_find_player_entries_loop_exits_on_window_boundary() -> None:
    """`_find_player_entries` while-loop exits via `pos < len-32` false.

    A pattern placed so that after `pos = pattern_pos + 1` the index passes
    `len(data) - 32` makes the loop condition (branch 209->247) terminate
    the scan instead of `find()` returning -1.
    """
    pattern = swgb_save.PLAYER_PATTERN
    # Resources right after the pattern must be out of range so the entry is
    # skipped (keeps players empty) but the pattern is still *found*, which is
    # what forces the loop to advance and then fail the while condition.
    bad_resources = struct.pack("<ffff", -1.0, -1.0, -1.0, -1.0)
    payload = b"\x00" * 4 + pattern + bad_resources
    save = swgb_save.SaveGame("dummy.ga2")
    save.data = payload

    entries = save._find_player_entries()

    assert entries == []  # nosec B101
    assert save.players == []  # nosec B101


def test_match_player_returns_none_when_no_name_matches() -> None:
    """`_match_player` for-loop falls through (branch 251->250 / ->return None).

    A loaded player whose name differs from the candidate exercises the
    loop body without taking the early return.
    """
    save = swgb_save.SaveGame("dummy.ga2")
    save.players = [swgb_save.Player("Player One", 1, [1.0, 2.0, 3.0, 4.0])]

    matched: Optional[swgb_save.Player] = save._match_player("Different Name", set())

    assert matched is None  # nosec B101


def test_match_player_skips_already_updated_player() -> None:
    """`_match_player` second clause false: name matches but is already updated."""
    save = swgb_save.SaveGame("dummy.ga2")
    save.players = [swgb_save.Player("Player One", 1, [1.0, 2.0, 3.0, 4.0])]

    matched = save._match_player("Player One", {"Player One"})

    assert matched is None  # nosec B101


def test_rewrite_player_resources_loop_exits_on_window_boundary() -> None:
    """`_rewrite_player_resources` while-loop exits via `pos < len-32` false.

    Same window-boundary exit as the find path (branch 310->320). With a
    found pattern but no matching player, the rewrite advances and then
    terminates on the loop condition, returning an empty updated set.
    """
    pattern = swgb_save.PLAYER_PATTERN
    payload = b"\x00" * 4 + pattern + struct.pack("<ffff", 1.0, 2.0, 3.0, 4.0)
    save = swgb_save.SaveGame("dummy.ga2")
    save.data = payload
    save.players = [swgb_save.Player("Nobody", 1, [9.0, 9.0, 9.0, 9.0])]

    updated = save._rewrite_player_resources(bytearray(payload))

    assert updated == set()  # nosec B101


def test_create_backup_is_skipped_when_backup_already_exists(tmp_path: Path) -> None:
    """`_create_backup_if_missing` takes the false branch (330->exit) when present.

    Pre-creating the `.backup` file makes `os.path.exists` true, so the copy
    is skipped and the existing backup content is preserved untouched.
    """
    original = tmp_path / "save.ga2"
    original.write_bytes(b"new-content")
    backup = tmp_path / "save.ga2.backup"
    backup.write_bytes(b"pre-existing-backup")

    swgb_save.SaveGame._create_backup_if_missing(str(original))

    # Skipped copy: the backup keeps its original (different) content.
    assert backup.read_bytes() == b"pre-existing-backup"  # nosec B101
