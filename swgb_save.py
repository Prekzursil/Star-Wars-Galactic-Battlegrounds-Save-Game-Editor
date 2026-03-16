from __future__ import absolute_import

import os
import shutil
import struct
import zlib
from dataclasses import dataclass
from typing import List, Optional, Set, Tuple


PLAYER_PATTERN = bytes.fromhex("16db00000021")
NAME_SEARCH_WINDOW = 512
MAX_NAME_BYTES = 32
MIN_MARKER_NAME_LENGTH = 3
MIN_DIRECT_NAME_LENGTH = 4
RESOURCE_COUNT = 4
RESOURCE_VALUE_MAX = 100000.0
NO_SAVE_DATA_LOADED = "No save data loaded"
PLAYER_ENTRY_ERRORS = (RuntimeError, ValueError, TypeError, UnicodeDecodeError, struct.error)


@dataclass
class Player:
    """Represents a player in the save file.

    File Format:
    - Player Number: 4-byte little-endian integer (e.g., 01 00 00 00 for player 1)
    - Name Length: 4-byte little-endian integer
    - Name: ASCII string
    - Resources: Four 32-bit floats (wood, food, nova, ore)
    """

    name: str
    index: int
    resources: List[float]  # [food, wood, nova, ore]


class SaveGame:
    """SWGB save game file parser."""

    def __init__(self, filename: str):
        """Initialize with save file path."""
        self.filename = filename
        self.data: Optional[bytes] = None
        self.players: List[Player] = []
        self.wbits: Optional[int] = None

    def read(self) -> None:
        """Read and decompress the save file."""
        with open(self.filename, "rb") as file_handle:
            compressed = file_handle.read()

        print(f"Compressed size: {len(compressed):,} bytes")

        for wbits in [zlib.MAX_WBITS, 15, -15]:
            try:
                self.data = zlib.decompress(compressed, wbits)
                print(f"Successfully decompressed with wbits={wbits}")
                self.wbits = wbits
                break
            except zlib.error:
                print(f"Failed to decompress with wbits={wbits}")

        if not self.data:
            raise ValueError("Failed to decompress save file")

        print(f"Decompressed size: {len(self.data):,} bytes")

        self._find_player_entries()

        if not self.players:
            print("Could not find any player entries")

    def _hex_dump(self, data: bytes, offset: int = 0, length: int = 64) -> str:
        """Create a hex dump of bytes with ASCII representation."""
        result = []
        for index in range(0, min(len(data), length), 16):
            chunk = data[index : index + 16]
            hex_part = " ".join(f"{byte:02x}" for byte in chunk).ljust(48)
            ascii_part = "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in chunk)
            result.append(f"{offset + index:08x}: {hex_part} |{ascii_part}|")
        return "\n".join(result)

    @staticmethod
    def _search_window(pattern_pos: int) -> Tuple[int, int]:
        return max(0, pattern_pos - NAME_SEARCH_WINDOW), pattern_pos

    def _find_null_terminated_end(self, start: int, limit: int) -> int:
        end = start
        upper_bound = min(start + MAX_NAME_BYTES, limit)
        while end < upper_bound and self.data and self.data[end] != 0:
            end += 1
        return end

    @staticmethod
    def _is_name_byte(byte_value: int) -> bool:
        return byte_value == 32 or 48 <= byte_value <= 57 or 65 <= byte_value <= 90 or 97 <= byte_value <= 122

    @staticmethod
    def _is_valid_candidate_name(candidate: str, min_length: int) -> bool:
        return (
            len(candidate) >= min_length
            and candidate.isprintable()
            and all(character.isalnum() or character.isspace() for character in candidate)
        )

    def _decode_candidate_name(self, start: int, end: int, *, min_length: int) -> Optional[str]:
        if self.data is None or end <= start:
            return None
        try:
            candidate = self.data[start:end].decode("ascii").strip()
        except UnicodeDecodeError:
            return None
        if not self._is_valid_candidate_name(candidate, min_length):
            return None
        return candidate

    def _name_from_marker(self, offset: int, search_end: int) -> Optional[str]:
        if self.data is None or offset + 1 >= len(self.data):
            return None
        if self.data[offset] != 0x09 or self.data[offset + 1] != 0x00:
            return None
        name_start = offset + 2
        name_end = self._find_null_terminated_end(name_start, search_end)
        return self._decode_candidate_name(name_start, name_end, min_length=MIN_MARKER_NAME_LENGTH)

    def _name_from_direct_scan(self, offset: int, search_end: int) -> Optional[str]:
        if self.data is None or offset + MIN_DIRECT_NAME_LENGTH > search_end:
            return None
        name_end = offset
        upper_bound = min(offset + MAX_NAME_BYTES, search_end)
        while name_end < upper_bound:
            current_byte = self.data[name_end]
            if current_byte == 0:
                break
            if not self._is_name_byte(current_byte):
                break
            name_end += 1
        return self._decode_candidate_name(offset, name_end, min_length=MIN_DIRECT_NAME_LENGTH)

    def _find_name_before_pattern(
        self,
        pattern_pos: int,
        *,
        default_name: str,
        marker_prefix: str,
        direct_prefix: str,
    ) -> str:
        search_start, search_end = self._search_window(pattern_pos)
        for offset in range(search_start, search_end - 1):
            marker_name = self._name_from_marker(offset, search_end)
            if marker_name:
                print(f"{marker_prefix} '{marker_name}' at offset {offset + 2}")
                return marker_name
            direct_name = self._name_from_direct_scan(offset, search_end)
            if direct_name:
                print(f"{direct_prefix} '{direct_name}' at offset {offset}")
                return direct_name
        return default_name

    def _read_resource_values(self, pattern_pos: int) -> Optional[List[float]]:
        if self.data is None:
            return None
        resource_start = pattern_pos + len(PLAYER_PATTERN)
        values: List[float] = []
        for index in range(RESOURCE_COUNT):
            chunk = self.data[resource_start + index * 4 : resource_start + (index + 1) * 4]
            try:
                value = struct.unpack("<f", chunk)[0]
            except struct.error:
                return None
            if not 0.0 <= value <= RESOURCE_VALUE_MAX:
                return None
            values.append(value)
        return values

    @staticmethod
    def _reorder_resources(values: List[float]) -> List[float]:
        return [values[1], values[0], values[2], values[3]]

    def _build_entry(self, pattern_pos: int, name: str, player_num: int) -> Tuple[int, str, int, bytes]:
        if self.data is None:
            return pattern_pos, name, player_num, b""
        resource_start = pattern_pos + len(PLAYER_PATTERN)
        return pattern_pos, name, player_num, self.data[resource_start : resource_start + RESOURCE_COUNT * 4]

    def _find_player_entries(self) -> List[Tuple[int, str, int, bytes]]:
        """Find all player entries in the file by looking for the pattern before player names."""
        entries: List[Tuple[int, str, int, bytes]] = []
        if self.data is None:
            return entries

        print(f"Searching for player pattern: {' '.join(f'{byte:02x}' for byte in PLAYER_PATTERN)}")
        pos = 0

        while pos < len(self.data) - 32:
            pattern_pos = self.data.find(PLAYER_PATTERN, pos)
            if pattern_pos == -1:
                print("No more patterns found")
                break

            print(f"\nFound pattern at offset {pattern_pos}")
            print("Context (64 bytes):")
            print(self._hex_dump(self.data[pattern_pos : pattern_pos + 64], pattern_pos))

            try:
                values = self._read_resource_values(pattern_pos)
                if values is None:
                    pos = pattern_pos + 1
                    continue

                player_num = len(self.players) + 1
                name = self._find_name_before_pattern(
                    pattern_pos,
                    default_name=f"Player {player_num}",
                    marker_prefix="Found name",
                    direct_prefix="Found name",
                )

                print(f"\nFound player {player_num} at {pattern_pos}")
                print(f"Name: {name}")
                print(f"Resources: {values}")
                print("Context:")
                print(self._hex_dump(self.data[pattern_pos : pattern_pos + 32], pattern_pos))

                player = Player(name, player_num, self._reorder_resources(values))
                self.players.append(player)
                entries.append(self._build_entry(pattern_pos, name, player_num))
            except PLAYER_ENTRY_ERRORS as exc:
                print(f"Error processing pattern at {pattern_pos}: {exc}")

            pos = pattern_pos + 1

        return entries

    def _match_player(self, candidate_name: str, updated_players: Set[str]) -> Optional[Player]:
        for player in self.players:
            if player.name == candidate_name and player.name not in updated_players:
                return player
        return None

    @staticmethod
    def _write_resources(data: bytearray, resource_start: int, resources: List[float]) -> None:
        for index, value in enumerate(resources):
            value_bytes = struct.pack("<f", value)
            data[resource_start + index * 4 : resource_start + (index + 1) * 4] = value_bytes

    @staticmethod
    def _verify_written_resources(data: bytearray, resource_start: int, resources: List[float]) -> None:
        print("\nVerifying resource values:")
        for index, expected_value in enumerate(resources):
            actual_value = struct.unpack("<f", data[resource_start + index * 4 : resource_start + (index + 1) * 4])[0]
            print(f"Resource {index}: Expected {expected_value:,.0f}, Got {actual_value:,.0f}")
            if abs(actual_value - expected_value) > 0.01:
                print("WARNING: Resource value mismatch!")

    def _update_matching_player(self, pattern_pos: int, data: bytearray, updated_players: Set[str]) -> bool:
        candidate_name = self._find_name_before_pattern(
            pattern_pos,
            default_name="",
            marker_prefix="Found potential name (marker):",
            direct_prefix="Found potential name (direct):",
        )
        if not candidate_name:
            return False

        player = self._match_player(candidate_name, updated_players)
        if player is None:
            return False

        if self.data is None:
            raise ValueError(NO_SAVE_DATA_LOADED)

        print(f"Matched player: {player.name}")
        resource_start = pattern_pos + len(PLAYER_PATTERN)
        print(f"Updating resources at offset {resource_start}")
        print("Before update:")
        print(self._hex_dump(self.data[resource_start : resource_start + 16], resource_start))
        self._write_resources(data, resource_start, player.resources)
        print("After update:")
        print(self._hex_dump(data[resource_start : resource_start + 16], resource_start))
        self._verify_written_resources(data, resource_start, player.resources)
        updated_players.add(player.name)
        return True

    @staticmethod
    def _create_backup_if_missing(filename: str) -> None:
        backup_path = filename + ".backup"
        if not os.path.exists(backup_path):
            shutil.copy2(filename, backup_path)
            print(f"Created backup: {backup_path}")

    @staticmethod
    def _compress_save_data(payload: bytes) -> bytes:
        compressor = zlib.compressobj(
            level=9,
            method=zlib.DEFLATED,
            wbits=-15,
            memLevel=9,
            strategy=zlib.Z_DEFAULT_STRATEGY,
        )
        compressed = compressor.compress(payload)
        compressed += compressor.flush()
        return compressed

    @staticmethod
    def _write_compressed_file(filename: str, compressed: bytes) -> None:
        with open(filename, "wb") as file_handle:
            file_handle.write(compressed)
        print(f"Saved changes to: {filename}")

    def save(self, filename: Optional[str] = None) -> None:
        """Save changes to file."""
        if self.data is None:
            raise ValueError(NO_SAVE_DATA_LOADED)

        if filename is None:
            filename = self.filename

        data = bytearray(self.data)
        updated_players: Set[str] = set()
        pos = 0

        while pos < len(self.data) - 32:
            pattern_pos = self.data.find(PLAYER_PATTERN, pos)
            if pattern_pos == -1:
                break
            try:
                self._update_matching_player(pattern_pos, data, updated_players)
            except PLAYER_ENTRY_ERRORS as exc:
                print(f"Warning: Error processing pattern at {pattern_pos}: {exc}")
            pos = pattern_pos + 1

        if len(updated_players) != len(self.players):
            missing = {player.name for player in self.players} - updated_players
            print(f"Warning: Could not update resources for players: {missing}")

        self.data = bytes(data)

        self._create_backup_if_missing(filename)

        print("\nAnalyzing original file format...")
        with open(filename, "rb") as file_handle:
            original = file_handle.read()

        try:
            compressed = self._compress_save_data(self.data)

            print(f"Original size: {len(original):,} bytes")
            print(f"Compressed size: {len(compressed):,} bytes")

            self._write_compressed_file(filename, compressed)
        except Exception as exc:
            print(f"Error saving file: {exc}")
            raise

    def print_info(self) -> None:
        """Print save file information."""
        if self.data is None:
            raise ValueError(NO_SAVE_DATA_LOADED)

        print(f"\nSave File: {self.filename}")
        print(f"Size: {len(self.data):,} bytes")
        print("\nPlayers:")

        for player in self.players:
            print(f"\n{player.name} (Player {player.index}):")
            print(f"  Food:  {player.resources[0]:,.0f}")
            print(f"  Wood:  {player.resources[1]:,.0f}")
            print(f"  Nova:  {player.resources[2]:,.0f}")
            print(f"  Ore:   {player.resources[3]:,.0f}")


def main() -> None:
    """Main entry point."""
    import sys

    if len(sys.argv) != 2:
        print("Usage: python swgb_save.py <save_file>")
        print("Example: python swgb_save.py 1.ga2")
        sys.exit(1)

    try:
        save = SaveGame(sys.argv[1])
        save.read()
        save.print_info()
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
