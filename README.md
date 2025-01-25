# SWGB Save Editor

A graphical save game editor for Star Wars Galactic Battlegrounds that allows editing player resources.

## Overview

The SWGB Save Editor is a Python-based tool that enables editing of .ga2 save files from Star Wars Galactic Battlegrounds. It provides a user-friendly interface to modify player resources (Carbon, Food, Nova, and Ore) while maintaining the integrity of the save file format.

## Technical Details

### Save File Format

The save files (.ga2) use a compressed format with the following characteristics:
- Raw deflate compression (no zlib header/footer)
- Player data is marked by specific byte patterns:
  - `16 db 00 00 00 21` appears before each player's resource data
  - Resources are stored as 32-bit floats in the order: [wood, food, nova, ore]
  - Player names are preceded by a length marker (e.g., `09 00` for length 9)

### Project Structure

The project consists of two main Python files:

1. `swgb_save.py`: Core save file handling
   - Decompression/compression of save files
   - Player data parsing and modification
   - Resource value validation
   - Backup creation before saving

2. `swgb_save_gui.py`: Graphical user interface
   - File selection and loading
   - Player resource display and editing
   - Status updates and error handling
   - Tkinter-based interface

## Implementation Details

### Save File Handling (swgb_save.py)

1. File Reading:
```python
def read(self):
    # Try different decompression methods
    for wbits in [zlib.MAX_WBITS, 15, -15]:
        try:
            self.data = zlib.decompress(compressed, wbits)
            self.wbits = wbits  # Store successful wbits value
            break
        except zlib.error:
            continue
```

2. Player Detection:
```python
# Pattern: 16 db 00 00 00 21
player_pattern = bytes.fromhex('16db00000021')
pattern_pos = self.data.find(player_pattern, pos)
```

3. Resource Reading:
```python
# Resources appear right after the pattern
resource_start = pattern_pos + 6
value = struct.unpack('<f', self.data[resource_start + i*4:resource_start + (i+1)*4])[0]
```

4. Save File Writing:
```python
# Compress data using same format as original
if self.wbits == -15:
    # Raw deflate format
    compressed = zlib.compress(self.data, level=9)[2:-1]  # Remove zlib header/footer
```

### GUI Implementation (swgb_save_gui.py)

1. Main Window Layout:
```python
# File selection
self.file_frame = ttk.Frame(self.main_frame)
self.file_path = tk.StringVar()
self.file_entry = ttk.Entry(self.file_frame, textvariable=self.file_path)
self.browse_button = ttk.Button(self.file_frame, text="Browse", command=self.browse_file)
```

2. Resource Display:
```python
# Players treeview with columns
self.tree = ttk.Treeview(self.tree_frame, columns=('Player', 'Carbon', 'Food', 'Nova', 'Ore'))
# Set fixed widths for resource columns
for col in ('Carbon', 'Food', 'Nova', 'Ore'):
    self.tree.heading(col, text=col)
    self.tree.column(col, width=90, minwidth=90, stretch=False, anchor='e')
```

3. Edit Dialog:
```python
class EditResourceDialog:
    def __init__(self, parent, player_name, resources):
        self.dialog = tk.Toplevel(parent)
        # Resource entries
        for i, (resource, value) in enumerate([('Carbon', resources[0]), ('Food', resources[1]), 
                                             ('Nova', resources[2]), ('Ore', resources[3])]):
            ttk.Label(self.dialog, text=f"{resource}:").grid(row=i, column=0)
            var = tk.StringVar(value=f"{value:,.0f}")
            entry = ttk.Entry(self.dialog, textvariable=var)
```

## Development Process

1. Initial Analysis:
   - Examined save file format using hex editors
   - Identified compression method (raw deflate)
   - Located player data patterns

2. Core Functionality:
   - Implemented save file decompression
   - Added player data parsing
   - Created resource modification logic
   - Added compression and save functionality

3. GUI Development:
   - Created main window layout
   - Added file selection functionality
   - Implemented resource display using Treeview
   - Created edit dialog for resource modification

4. Refinements:
   - Added error handling and validation
   - Implemented automatic backups
   - Fixed column sizing issues
   - Improved resource value formatting

5. Testing and Fixes:
   - Tested with various save files
   - Fixed compression issues
   - Improved name detection
   - Added resource value validation

## Building the Executable

The project uses PyInstaller to create a standalone executable:

```bash
pyinstaller --clean --onefile --noconsole --name "SWGB Save Editor" swgb_save_gui.py
```

Build options:
- `--clean`: Clean PyInstaller cache
- `--onefile`: Create a single executable file
- `--noconsole`: Don't show console window
- `--name`: Set output executable name

## Usage

1. Launch the SWGB Save Editor
2. Click "Browse" to select a .ga2 save file
3. Click "Load Save File" to load the save
4. Select a player and click "Edit Resources"
5. Modify resource values in the dialog
6. Click "Save Changes" to save modifications

The editor automatically creates backups (*.ga2.backup) before saving changes.

## Error Handling

- Invalid save files: Detected during load
- Incorrect resource values: Validated during editing
- Save failures: Backup created before saving
- Compression errors: Verified before saving

## Future Improvements

Potential enhancements:
- Add support for editing other player data
- Implement save file analysis tools
- Add support for campaign saves
- Create save file comparison tools

## Technical Notes

- Python 3.11+ required
- Dependencies: tkinter, zlib
- Save file modifications preserve exact byte format
- Resource values limited to 0-1,000,000 range
