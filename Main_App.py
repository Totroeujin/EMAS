import wx
import wx.grid
import json
import os
from pathlib import Path

class EMAS_App(wx.App):
    def OnInit(self):
        self.config_path = Path(os.path.expanduser("~/.EMAS"))
        self.config_path.mkdir(exist_ok=True)
        self.save_path = self.config_path / "data.json"
        self.frame = MainFrame(self.save_path)
        self.frame.Show()
        return True

class DebtGrid(wx.grid.Grid):
    """Custom grid for debt matrix with net flow on diagonals."""
    def __init__(self, parent, members):
        super().__init__(parent)
        self.members = members
        self.debt_matrix = []
        self.initialize_matrix()
        
        # Create grid ONCE with final size
        self.CreateGrid(len(self.members), len(self.members))
        
        # Initialize grid content
        for idx, member in enumerate(self.members):
            self.SetRowLabelValue(idx, member)
            self.SetColLabelValue(idx, member)
            for j in range(len(self.members)):
                self.SetCellValue(idx, j, f"{self.debt_matrix[idx][j]:.2f}")
                self.SetReadOnly(idx, j, True)
        
        self.Bind(wx.grid.EVT_GRID_LABEL_LEFT_DCLICK, self.on_label_edit)
        self.update_diagonals()

    def initialize_matrix(self):
        """Create/update the debt matrix to match member count"""
        n = len(self.members)
        # Add new row/column for new members
        while len(self.debt_matrix) < n:
            self.debt_matrix.append([0.0] * n)
        # Truncate if members were removed (though your app doesn't support removal)
        self.debt_matrix = self.debt_matrix[:n]
        for row in self.debt_matrix:
            while len(row) < n:
                row.append(0.0)
            row[:] = row[:n]

    def on_label_edit(self, event):
        row = event.GetRow()
        if row != -1:
            new_name = wx.GetTextFromUser("Edit Member Name:", default_value=self.GetRowLabelValue(row))
            if new_name:
                self.SetRowLabelValue(row, new_name)
                self.SetColLabelValue(row, new_name)
                self.members[row] = new_name
        event.Skip()

    def update_diagonals(self, changed_members = None):
        n = len(self.members)
        for idx in range(n):
            total_owed_to_me = sum(self.debt_matrix[idx][j] for j in range(n) if j != idx)
            total_i_owe = sum(self.debt_matrix[i][idx] for i in range(n) if i != idx)
            net = total_owed_to_me - total_i_owe
            self.SetCellValue(idx, idx, f"{net:+.2f}")
            self.update_cell_style(idx, idx)

    def update_cell_style(self, row, col):
        value = float(self.GetCellValue(row, col))
    
        # Only update color for diagonal cells
        if row == col:
            if value > 0:
                color = wx.Colour(200, 255, 200)  # Green
            elif value < 0:
                color = wx.Colour(255, 200, 200)  # Red
            else:
                color = wx.Colour(240, 240, 240)  # Grey
            self.SetCellBackgroundColour(row, col, color)
        # Non-diagonal cells keep default grey
        
        self.ForceRefresh()

    def update_cell(self, row, col, value):
        """Update debt_matrix and grid cell."""
        self.debt_matrix[row][col] = value
        self.SetCellValue(row, col, f"{value:.2f}")
        self.update_cell_style(row, col)

    def refresh_all(self):
        """Refresh grid data and styles"""
        for i in range(len(self.members)):
            for j in range(len(self.members)):
                self.SetCellValue(i, j, f"{self.debt_matrix[i][j]:.2f}")
        self.update_diagonals()

class GroupPanel(wx.Panel):
    def __init__(self, parent, group_name, main_frame, members=None):
        super().__init__(parent)
        self.main_frame = main_frame
        self.group_name = group_name
        self.members = members if members else ["You"]
        self.debt_grid = DebtGrid(self, self.members)
        
        # Input widgets
        self.lender = wx.ComboBox(self, choices=self.members, style=wx.CB_READONLY)
        self.borrower = wx.ComboBox(self, choices=self.members, style=wx.CB_READONLY)
        self.amount = wx.TextCtrl(self)
        self.add_member = wx.Button(self, label="Add Member")
        self.add_transaction = wx.Button(self, label="Add Transaction")
        
        # Layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        input_sizer = wx.FlexGridSizer(rows=3, cols=2, vgap=5, hgap=5)
        input_sizer.AddMany([
            # Lender row
            (wx.StaticText(self, label="Lender:"), 0, wx.ALIGN_CENTER_VERTICAL),
            (self.lender, 1, wx.EXPAND),
            
            # Borrower row
            (wx.StaticText(self, label="Borrower:"), 0, wx.ALIGN_CENTER_VERTICAL),
            (self.borrower, 1, wx.EXPAND),
            
            # Amount row
            (wx.StaticText(self, label="Amount:"), 0, wx.ALIGN_CENTER_VERTICAL),
            (self.amount, 1, wx.EXPAND)
        ])
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(self.add_member, 0, wx.ALL, 5)
        button_sizer.Add(self.add_transaction, 0, wx.ALL, 5)
        
        sizer.Add(self.debt_grid, 1, wx.EXPAND|wx.ALL, 5)
        sizer.Add(input_sizer, 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(button_sizer, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        self.SetSizer(sizer)
        
        # Event bindings
        self.add_member.Bind(wx.EVT_BUTTON, self.on_add_member)
        self.add_transaction.Bind(wx.EVT_BUTTON, self.on_add_transaction)

    def on_add_member(self, event):
        new_member = wx.GetTextFromUser("Enter member name:", parent=self)
        if new_member and new_member not in self.members:
            # Update members list first
            self.members.append(new_member)
            new_idx = len(self.members) - 1
            
            # Resize grid BEFORE matrix initialization
            self.debt_grid.AppendRows(1)
            self.debt_grid.AppendCols(1)
            
            # Reinitialize matrix with new size
            self.debt_grid.initialize_matrix()
            
            # Initialize new cells
            for j in range(len(self.members)):
                self.debt_grid.SetCellValue(new_idx, j, "0.00")
                self.debt_grid.SetCellValue(j, new_idx, "0.00")
            
            # Update labels and comboboxes
            self.debt_grid.SetRowLabelValue(new_idx, new_member)
            self.debt_grid.SetColLabelValue(new_idx, new_member)
            self.lender.Append(new_member)
            self.borrower.Append(new_member)
            
            self.debt_grid.update_diagonals()
            self.main_frame.save_data()

    def on_add_transaction(self, event):
        lender = self.lender.GetValue()
        borrower = self.borrower.GetValue()
        amount = self.amount.GetValue().strip()
        
        # Input validation
        if not lender or not borrower or lender == borrower:
            wx.MessageBox("Invalid transaction!", "Error", wx.OK|wx.ICON_ERROR)
            return
        try:
            amount = float(amount)
            if amount <= 0: raise ValueError
        except ValueError:
            wx.MessageBox("Invalid amount!", "Error", wx.OK|wx.ICON_ERROR)
            return
        
        # Update both grid and matrix
        lender_idx = self.members.index(lender)
        borrower_idx = self.members.index(borrower)
        
        # Update debt_matrix first
        self.debt_grid.debt_matrix[lender_idx][borrower_idx] += amount
        # Then update grid cell
        self.debt_grid.SetCellValue(lender_idx, borrower_idx, 
                                f"{self.debt_grid.debt_matrix[lender_idx][borrower_idx]:.2f}")
        
        self.debt_grid.update_diagonals()
        self.debt_grid.ForceRefresh()
        self.main_frame.save_data()

class MainFrame(wx.Frame):
    def __init__(self, save_path):
        super().__init__(None, title="EMAS", size=(800, 600))
        self.save_path = save_path
        self.notebook = wx.Notebook(self)

        # Load data on startup
        self.load_data()
        
        # Menu bar
        menubar = wx.MenuBar()
        file_menu = wx.Menu()

        self.ID_SAVE_DATA = wx.NewId()
        self.ID_ADD_GROUP = wx.NewId()
        self.ID_SHOW_LOCATION = wx.NewId()
        self.ID_CLEAR_DATA = wx.NewId()
        
        file_menu.Append(self.ID_SAVE_DATA, "Save Data")
        file_menu.Append(self.ID_ADD_GROUP, "Add Group")
        file_menu.AppendSeparator()
        file_menu.Append(self.ID_SHOW_LOCATION, "Show Data File Location")
        file_menu.Append(self.ID_CLEAR_DATA, "Clear All Data")

        menubar.Append(file_menu, "File")
        self.SetMenuBar(menubar)
        
        # Event bindings
        self.Bind(wx.EVT_MENU, self.on_save, id=self.ID_SAVE_DATA)
        self.Bind(wx.EVT_MENU, self.on_add_group, id=self.ID_ADD_GROUP)
        self.Bind(wx.EVT_MENU, self.on_show_location, id=self.ID_SHOW_LOCATION)
        self.Bind(wx.EVT_MENU, self.on_clear_data, id=self.ID_CLEAR_DATA)
        
        self.Show()

    def on_show_location(self, event):
        """Reveal data file in system explorer"""
        import subprocess
        try:
            if os.name == 'nt':  # Windows
                subprocess.Popen(f'explorer /select,"{self.save_path}"')
            else:  # Mac/Linux
                subprocess.Popen(['open', '--reveal', str(self.save_path)])
        except Exception as e:
            wx.MessageBox(f"Path: {self.save_path}", "Data File Location", wx.OK)

    def on_clear_data(self, event):
        """Clear all groups and reset to default"""
        confirm = wx.MessageBox("This will delete ALL data! Continue?", 
                              "Warning", wx.YES_NO | wx.ICON_WARNING)
        if confirm == wx.YES:
            try:
                # Delete data file
                if self.save_path.exists():
                    self.save_path.unlink()
                
                # Clear current notebook
                self.notebook.DeleteAllPages()
                
                # Create fresh default group
                self.add_group("Default Group")
                
                wx.MessageBox("All data has been cleared!", "Success", 
                            wx.OK | wx.ICON_INFORMATION)
            except Exception as e:
                wx.MessageBox(f"Error clearing data: {str(e)}", "Error", 
                            wx.OK | wx.ICON_ERROR)

    def load_data(self):
        """Load data from JSON file on startup"""
        if self.save_path.exists():
            try:
                with open(self.save_path, 'r') as f:
                    data = json.load(f)
                
                for group_data in data["groups"]:
                    # Create panel with loaded data
                    panel = GroupPanel(
                        self.notebook,
                        group_data["name"],
                        self,
                        members=group_data["members"]
                    )
                    
                    # Set debt matrix
                    panel.debt_grid.debt_matrix = [
                        [float(val) for val in row] 
                        for row in group_data["debt_matrix"]
                    ]
                    
                    # Refresh grid display
                    panel.debt_grid.refresh_all()  # Add this line
                    
                    # Update comboboxes
                    panel.lender.SetItems(panel.members)
                    panel.borrower.SetItems(panel.members)
                    
                    self.notebook.AddPage(panel, group_data["name"])
            except Exception as e:
                wx.MessageBox(f"Error loading data: {str(e)}", "Error", wx.OK | wx.ICON_ERROR)
                self.add_group("Default Group")
        else:
            self.add_group("Default Group")

    def save_data(self):
        """Save all groups to JSON file"""
        data = {
            "groups": [
                {
                    "name": self.notebook.GetPageText(i),
                    "members": self.notebook.GetPage(i).members,
                    "debt_matrix": [
                        [float(cell) for cell in row]
                        for row in self.notebook.GetPage(i).debt_grid.debt_matrix
                    ]
                }
                for i in range(self.notebook.GetPageCount())  # Correct method
            ]
        }   
        
        with open(self.save_path, 'w') as f:
            json.dump(data, f, indent=2)

    def add_group(self, name):
        panel = GroupPanel(self.notebook, name, self)
        self.notebook.AddPage(panel, name)
        self.save_data()

    def on_add_group(self, event):
        dlg = wx.TextEntryDialog(self, "Enter group name:", "New Group")
        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetValue()
            if name: 
                self.add_group(name)
        dlg.Destroy()

    def on_save(self, event):
        self.save_data()
        wx.MessageBox("Data saved successfully!", "Info", wx.OK | wx.ICON_INFORMATION)

if __name__ == "__main__":
    app = EMAS_App()  
    app.MainLoop()    