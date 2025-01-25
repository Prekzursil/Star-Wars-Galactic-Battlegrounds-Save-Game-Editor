import zlib
import struct
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple

@dataclass
class Player:
    """Represents a player in the save file
    
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
    """SWGB save game file parser"""
    
    def __init__(self, filename: str):
        """Initialize with save file path"""
        self.filename = filename
        self.data = None  # Decompressed data
        self.players = []  # List of players
        self.wbits = None  # Store successful wbits value
    
    def read(self) -> None:
        """Read and decompress the save file"""
        # Read compressed data
        with open(self.filename, 'rb') as f:
            compressed = f.read()
        
        print(f"Compressed size: {len(compressed):,} bytes")
        
        # Try different decompression methods
        for wbits in [zlib.MAX_WBITS, 15, -15]:
            try:
                self.data = zlib.decompress(compressed, wbits)
                print(f"Successfully decompressed with wbits={wbits}")
                self.wbits = wbits  # Store successful wbits value
                break
            except zlib.error:
                print(f"Failed to decompress with wbits={wbits}")
                continue
        
        if not self.data:
            raise ValueError("Failed to decompress save file")
        
        print(f"Decompressed size: {len(self.data):,} bytes")
        
        # Find and parse all players
        self._find_player_entries()
        
        if not self.players:
            print("Could not find any player entries")
    
    def _hex_dump(self, data: bytes, offset: int = 0, length: int = 64) -> str:
        """Create a hex dump of bytes with ASCII representation"""
        result = []
        for i in range(0, min(len(data), length), 16):
            chunk = data[i:i+16]
            # Hex values
            hex_part = ' '.join(f'{b:02x}' for b in chunk)
            hex_part = hex_part.ljust(48)  # Pad to align ASCII part
            # ASCII values
            ascii_part = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
            result.append(f"{offset+i:08x}: {hex_part} |{ascii_part}|")
        return '\n'.join(result)
    
    def _find_player_entries(self) -> List[Tuple[int, str, int, bytes]]:
        """Find all player entries in the file by looking for the pattern before player names"""
        entries = []
        pos = 0
        
        # Pattern: 16 db 00 00 00 21
        player_pattern = bytes.fromhex('16db00000021')  # Pattern before player names
        
        print(f"Searching for player pattern: {' '.join(f'{b:02x}' for b in player_pattern)}")
        
        while pos < len(self.data) - 32:
            # Look for the pattern
            pattern_pos = self.data.find(player_pattern, pos)
            if pattern_pos == -1:
                print("No more patterns found")
                break
                
            print(f"\nFound pattern at offset {pattern_pos}")
            print("Context (64 bytes):")
            print(self._hex_dump(self.data[pattern_pos:pattern_pos+64], pattern_pos))
                
            try:
                # Resources appear right after the pattern
                resource_start = pattern_pos + 6
                
                # Try to read 4 consecutive floats
                values = []
                valid_sequence = True
                
                for i in range(4):
                    try:
                        value = struct.unpack('<f', self.data[resource_start + i*4:resource_start + (i+1)*4])[0]
                        if 0.0 <= value <= 100000.0:  # Reasonable resource range
                            values.append(value)
                        else:
                            valid_sequence = False
                            break
                    except:
                        valid_sequence = False
                        break
                
                if valid_sequence and len(values) == 4:
                    player_num = len(self.players) + 1
                    
                    # Look for name before the pattern
                    name = f"Player {player_num}"  # Default name
                    
                    # Search backwards from pattern for name length marker
                    search_start = max(0, pattern_pos - 512)  # Look up to 512 bytes before pattern
                    search_end = pattern_pos
                    
                    # Look for name length marker (09 00) followed by name
                    for i in range(search_start, search_end - 2):
                        if self.data[i] == 0x09 and self.data[i+1] == 0x00:
                            try:
                                # Name should follow immediately
                                name_start = i + 2
                                name_end = name_start
                                
                                # Find end of name (null terminator)
                                while name_end < min(name_start + 32, search_end):
                                    if self.data[name_end] == 0:
                                        break
                                    name_end += 1
                                
                                if name_end > name_start:
                                    test_name = self.data[name_start:name_end].decode('ascii').strip()
                                    if test_name and test_name.isprintable() and len(test_name) > 2:
                                        # Check if this looks like a valid name
                                        if all(c.isalnum() or c.isspace() for c in test_name):
                                            name = test_name
                                            print(f"Found name '{name}' at offset {name_start}")
                                            break
                            except:
                                continue
                        # Also look for names directly
                        elif i + 4 <= search_end:  # Need at least 4 bytes for a name
                            try:
                                # Try to read a reasonable length name
                                name_end = i
                                valid_chars = 0
                                
                                while name_end < min(i + 32, search_end):
                                    if self.data[name_end] == 0:
                                        break
                                    if chr(self.data[name_end]).isalnum() or chr(self.data[name_end]).isspace():
                                        valid_chars += 1
                                    else:
                                        break
                                    name_end += 1
                                
                                if valid_chars >= 4:  # Need at least 4 valid characters
                                    test_name = self.data[i:name_end].decode('ascii').strip()
                                    if test_name and test_name.isprintable() and len(test_name) >= 4:
                                        # Check if this looks like a valid name
                                        if all(c.isalnum() or c.isspace() for c in test_name):
                                            name = test_name
                                            print(f"Found name '{name}' at offset {i}")
                                            break
                            except:
                                continue
                    
                    print(f"\nFound player {player_num} at {pattern_pos}")
                    print(f"Name: {name}")
                    print(f"Resources: {values}")
                    print("Context:")
                    print(self._hex_dump(self.data[pattern_pos:pattern_pos+32], pattern_pos))
                    
                    # Create player object directly
                    # Resources are in order: [wood, food, nova, ore]
                    # Reorder values to match the game's order
                    reordered_values = [values[1], values[0], values[2], values[3]]  # Swap food and wood
                    player = Player(name, player_num, reordered_values)
                    self.players.append(player)
            except Exception as e:
                print(f"Error processing pattern at {pattern_pos}: {e}")
            
            pos = pattern_pos + 1
        
        return entries
    
    
    def save(self, filename: str = None) -> None:
        """Save changes to file"""
        if filename is None:
            filename = self.filename
        
        # Update resource values in the data
        data = bytearray(self.data)
        
        # Pattern: 16 db 00 00 00 21
        pattern = bytes.fromhex('16db00000021')
        pos = 0
        
        # Keep track of which players we've updated
        updated_players = set()
        
        while pos < len(self.data) - 32:
            pattern_pos = self.data.find(pattern, pos)
            if pattern_pos == -1:
                break
            
            try:
                # Look for name before the pattern
                search_start = max(0, pattern_pos - 512)
                search_end = pattern_pos
                
                # Try both name detection methods
                found_player = False
                
                # Method 1: Look for name length marker (09 00)
                for i in range(search_start, search_end - 2):
                    if self.data[i] == 0x09 and self.data[i+1] == 0x00:
                        try:
                            name_start = i + 2
                            name_end = name_start
                            while name_end < min(name_start + 32, search_end):
                                if self.data[name_end] == 0:
                                    break
                                name_end += 1
                            
                            if name_end > name_start:
                                test_name = self.data[name_start:name_end].decode('ascii').strip()
                                if test_name and test_name.isprintable():
                                    print(f"Found potential name (marker): '{test_name}' at offset {name_start}")
                                    # Find matching player
                                    for player in self.players:
                                        if player.name == test_name and player.name not in updated_players:
                                            print(f"Matched player: {player.name}")
                                            # Update resources
                                            resource_start = pattern_pos + 6
                                            for j, value in enumerate(player.resources):
                                                value_bytes = struct.pack('<f', value)
                                                data[resource_start + j*4:resource_start + (j+1)*4] = value_bytes
                                            updated_players.add(player.name)
                                            found_player = True
                                            break
                                    if found_player:
                                        break
                        except:
                            continue
                    
                    # Method 2: Look for direct name match
                    if not found_player and i + 4 <= search_end:
                        try:
                            name_end = i
                            valid_chars = 0
                            while name_end < min(i + 32, search_end):
                                if self.data[name_end] == 0:
                                    break
                                if chr(self.data[name_end]).isalnum() or chr(self.data[name_end]).isspace():
                                    valid_chars += 1
                                else:
                                    break
                                name_end += 1
                            
                            if valid_chars >= 4:
                                test_name = self.data[i:name_end].decode('ascii').strip()
                                if test_name and test_name.isprintable():
                                    print(f"Found potential name (direct): '{test_name}' at offset {i}")
                                    # Find matching player
                                    for player in self.players:
                                        if player.name == test_name and player.name not in updated_players:
                                            print(f"Matched player: {player.name}")
                                            # Update resources
                                            resource_start = pattern_pos + 6
                                            print(f"Updating resources at offset {resource_start}")
                                            print("Before update:")
                                            print(self._hex_dump(self.data[resource_start:resource_start+16], resource_start))
                                            for j, value in enumerate(player.resources):
                                                value_bytes = struct.pack('<f', value)
                                                data[resource_start + j*4:resource_start + (j+1)*4] = value_bytes
                                            print("After update:")
                                            print(self._hex_dump(data[resource_start:resource_start+16], resource_start))
                                            
                                            # Verify values were written correctly
                                            print("\nVerifying resource values:")
                                            for j, expected_value in enumerate(player.resources):
                                                actual_value = struct.unpack('<f', data[resource_start + j*4:resource_start + (j+1)*4])[0]
                                                print(f"Resource {j}: Expected {expected_value:,.0f}, Got {actual_value:,.0f}")
                                                if abs(actual_value - expected_value) > 0.01:  # Allow small float differences
                                                    print("WARNING: Resource value mismatch!")
                                            
                                            updated_players.add(player.name)
                                            found_player = True
                                            break
                                    if found_player:
                                        break
                        except:
                            continue
            except Exception as e:
                print(f"Warning: Error processing pattern at {pattern_pos}: {e}")
            
            pos = pattern_pos + 1
        
        # Verify all players were updated
        if len(updated_players) != len(self.players):
            missing = set(p.name for p in self.players) - updated_players
            print(f"Warning: Could not update resources for players: {missing}")
        
        # Save the modified data
        self.data = bytes(data)
        
        # Create backup first
        backup_path = filename + '.backup'
        if not os.path.exists(backup_path):
            import shutil
            shutil.copy2(filename, backup_path)
            print(f"Created backup: {backup_path}")
        
        # Read original file to analyze format
        print("\nAnalyzing original file format...")
        with open(filename, 'rb') as f:
            original = f.read()
        
        try:
            # Create compressor object with same settings as read
            compressor = zlib.compressobj(
                level=9,  # Maximum compression
                method=zlib.DEFLATED,
                wbits=-15,  # Raw deflate format (no header/footer)
                memLevel=9,  # Maximum memory for compression
                strategy=zlib.Z_DEFAULT_STRATEGY
            )
            
            # Compress data
            compressed = compressor.compress(self.data)
            compressed += compressor.flush()
            
            print(f"Original size: {len(original):,} bytes")
            print(f"Compressed size: {len(compressed):,} bytes")
            
            # Save compressed data
            with open(filename, 'wb') as f:
                f.write(compressed)
            print(f"Saved changes to: {filename}")
        except Exception as e:
            print(f"Error saving file: {e}")
            raise
    
    def print_info(self) -> None:
        """Print save file information"""
        print(f"\nSave File: {self.filename}")
        print(f"Size: {len(self.data):,} bytes")
        print("\nPlayers:")
        
        for player in self.players:
            print(f"\n{player.name} (Player {player.index}):")
            print(f"  Food:  {player.resources[0]:,.0f}")
            print(f"  Wood:  {player.resources[1]:,.0f}")
            print(f"  Nova:  {player.resources[2]:,.0f}")
            print(f"  Ore:   {player.resources[3]:,.0f}")

def main():
    """Main entry point"""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python swgb_save.py <save_file>")
        print("Example: python swgb_save.py 1.ga2")
        sys.exit(1)
    
    try:
        # Parse save file
        save = SaveGame(sys.argv[1])
        save.read()
        save.print_info()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
