import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from swgb_save import SaveGame
import sys
import os

class EditResourceDialog:
    def __init__(self, parent, player_name, resources):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Edit Resources - {player_name}")
        self.dialog.geometry("300x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (
            parent.winfo_rootx() + parent.winfo_width()/2 - 150,
            parent.winfo_rooty() + parent.winfo_height()/2 - 100))
        
        # Create and configure the grid
        self.dialog.columnconfigure(1, weight=1)
        
        # Resource entries
        self.entries = {}
        # Resources in player object are [wood, food, nova, ore]
        # But display them as [carbon, food, nova, ore]
        for i, (resource, value) in enumerate([('Carbon', resources[0]), ('Food', resources[1]), 
                                             ('Nova', resources[2]), ('Ore', resources[3])]):
            ttk.Label(self.dialog, text=f"{resource}:").grid(row=i, column=0, padx=5, pady=5, sticky='e')
            var = tk.StringVar(value=f"{value:,.0f}")
            entry = ttk.Entry(self.dialog, textvariable=var)
            entry.grid(row=i, column=1, padx=5, pady=5, sticky='ew')
            self.entries[resource] = var
        
        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="OK", command=self.ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.LEFT, padx=5)
        
        self.result = None
        
    def ok(self):
        """Validate and save the changes"""
        try:
            # Parse and validate all values
            values = {}
            for resource in ['Carbon', 'Food', 'Nova', 'Ore']:
                try:
                    value = float(self.entries[resource].get().replace(',', ''))
                    if value < 0 or value > 1000000:  # Reasonable limit
                        raise ValueError(f"{resource} must be between 0 and 1,000,000")
                    values[resource] = value
                except ValueError:
                    raise ValueError(f"Invalid {resource} value. Must be a number between 0 and 1,000,000")
            
            # Return values in game's order: [wood, food, nova, ore]
            self.result = [values['Carbon'], values['Food'], values['Nova'], values['Ore']]
            self.dialog.destroy()
            
        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))
            return  # Don't close dialog on validation error
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save changes: {str(e)}")
            return  # Don't close dialog on error
    
    def cancel(self):
        """Cancel the edit"""
        self.dialog.destroy()

class SaveGameGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SWGB Save Game Parser")
        self.root.geometry("600x500")
        
        # Store current save game
        self.current_save = None
        
        # Create main frame with padding
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        
        # File selection
        self.file_frame = ttk.Frame(self.main_frame)
        self.file_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        self.file_frame.columnconfigure(1, weight=1)
        
        self.file_label = ttk.Label(self.file_frame, text="Save File:")
        self.file_label.grid(row=0, column=0, padx=5)
        
        self.file_path = tk.StringVar()
        self.file_entry = ttk.Entry(self.file_frame, textvariable=self.file_path)
        self.file_entry.grid(row=0, column=1, padx=5, sticky=(tk.W, tk.E))
        
        self.browse_button = ttk.Button(self.file_frame, text="Browse", command=self.browse_file)
        self.browse_button.grid(row=0, column=2, padx=5)
        
        # Button frame
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.grid(row=1, column=0, pady=10)
        
        # Load and Save buttons
        self.load_button = ttk.Button(self.button_frame, text="Load Save File", command=self.load_save)
        self.load_button.grid(row=0, column=0, padx=5)
        
        self.edit_button = ttk.Button(self.button_frame, text="Edit Resources", command=self.edit_resources, state=tk.DISABLED)
        self.edit_button.grid(row=0, column=1, padx=5)
        
        self.save_button = ttk.Button(self.button_frame, text="Save Changes", command=self.save_changes, state=tk.DISABLED)
        self.save_button.grid(row=0, column=2, padx=5)
        
        # Players treeview
        self.tree_frame = ttk.Frame(self.main_frame)
        self.tree_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        self.tree_frame.columnconfigure(0, weight=1)
        self.tree_frame.rowconfigure(0, weight=1)
        
        # Players treeview with columns
        self.tree = ttk.Treeview(self.tree_frame, columns=('Player', 'Carbon', 'Food', 'Nova', 'Ore'), show='headings', selectmode='browse')
        
        # Configure column headings and widths
        self.tree.heading('Player', text='Player Name')
        self.tree.column('Player', width=200, minwidth=150, anchor='w')  # Left-align player names
        
        # Set fixed widths for resource columns
        for col in ('Carbon', 'Food', 'Nova', 'Ore'):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=90, minwidth=90, stretch=False, anchor='e')  # Right-align numbers with fixed width
        
        # Make the window resizable
        root.resizable(True, True)
        
        # Make the treeview expand with window
        self.tree_frame.columnconfigure(0, weight=1)
        self.tree_frame.rowconfigure(0, weight=1)
        
        # Add scrollbar
        self.scrollbar = ttk.Scrollbar(self.tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self.main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        self.status_bar.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.status_var.set("Ready")
    
    def browse_file(self):
        """Open file dialog to select save file"""
        filetypes = [
            ('SWGB Save Files', '*.ga2'),
            ('All Files', '*.*')
        ]
        filename = filedialog.askopenfilename(
            title="Select Save File",
            filetypes=filetypes,
            initialdir=os.path.dirname(os.path.abspath(__file__))
        )
        if filename:
            self.file_path.set(filename)
    
    def load_save(self):
        """Load and parse the selected save file"""
        filename = self.file_path.get()
        if not filename:
            messagebox.showerror("Error", "Please select a save file first")
            return
        
        try:
            # Clear existing items
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Load save file
            self.status_var.set("Loading save file...")
            self.root.update()
            
            self.current_save = SaveGame(filename)
            self.current_save.read()
            
            # Add players to tree
            for player in self.current_save.players:
                # Resources in player object are [wood, food, nova, ore]
                # But display them as [food, wood, nova, ore]
                values = [
                    f"{player.name} (Player {player.index})",  # Player name column
                    f"{player.resources[0]:,.0f}",  # Carbon (index 0)
                    f"{player.resources[1]:,.0f}",  # Food (index 1)
                    f"{player.resources[2]:,.0f}",  # Nova
                    f"{player.resources[3]:,.0f}"   # Ore
                ]
                self.tree.insert('', 'end', values=values)
            
            # Enable edit and save buttons
            self.edit_button.config(state=tk.NORMAL)
            self.save_button.config(state=tk.NORMAL)
            
            self.status_var.set(f"Loaded {len(self.current_save.players)} players from {os.path.basename(filename)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load save file: {str(e)}")
            self.status_var.set("Error loading file")
    
    def edit_resources(self):
        """Edit resources for selected player"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a player to edit")
            return
        
        # Get selected player index
        item = selection[0]
        player_idx = self.tree.index(item)
        player = self.current_save.players[player_idx]
        
        # Open edit dialog
        dialog = EditResourceDialog(self.root, player.name, player.resources)
        self.root.wait_window(dialog.dialog)
        
        if dialog.result:
            # Update player resources
            player.resources = dialog.result
            
            # Update tree view
            # Resources in player object are [wood, food, nova, ore]
            # But display them as [carbon, food, nova, ore]
            values = [
                f"{player.name} (Player {player.index})",  # Player name column
                f"{player.resources[0]:,.0f}",  # Carbon (index 0)
                f"{player.resources[1]:,.0f}",  # Food (index 1)
                f"{player.resources[2]:,.0f}",  # Nova
                f"{player.resources[3]:,.0f}"   # Ore
            ]
            self.tree.item(item, values=values)
            self.status_var.set(f"Updated resources for {player.name}")
    
    def save_changes(self):
        """Save changes to the save file"""
        if not self.current_save:
            return
        
        try:
            # Create backup
            backup_path = self.file_path.get() + '.backup'
            if not os.path.exists(backup_path):
                import shutil
                shutil.copy2(self.file_path.get(), backup_path)
            
            # Save changes
            self.current_save.save(self.file_path.get())
            self.status_var.set("Changes saved successfully")
            messagebox.showinfo("Success", "Changes saved successfully.\nBackup created as .backup file.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save changes: {str(e)}")
            self.status_var.set("Error saving changes")

def main():
    root = tk.Tk()
    app = SaveGameGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
