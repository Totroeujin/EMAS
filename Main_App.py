import wx
import wx.grid

class DebtGrid(wx.grid.Grid):
    """Custom grid for debt matrix with net flow on diagonals."""
    def __init__(self, parent, members):
        super().__init__(parent)
        self.members = members
        self.data = {}
        
        self.CreateGrid(len(members), len(members))
        self.SetRowLabelSize(150)
        self.SetColLabelSize(150)
        
        # Initialize grid cells
        for idx, member in enumerate(members):
            self.SetRowLabelValue(idx, member)
            self.SetColLabelValue(idx, member)
            for j in range(len(members)):
                self.SetCellValue(idx, j, "0.00")
                self.SetReadOnly(idx, j, True)
                self.SetCellBackgroundColour(idx, j, wx.Colour(240, 240, 240))  # Grey
        
        self.Bind(wx.grid.EVT_GRID_LABEL_LEFT_DCLICK, self.on_label_edit)
        self.update_diagonals()

    def on_label_edit(self, event):
        row = event.GetRow()
        if row != -1:
            new_name = wx.GetTextFromUser("Edit Member Name:", default_value=self.GetRowLabelValue(row))
            if new_name:
                self.SetRowLabelValue(row, new_name)
                self.SetColLabelValue(row, new_name)
                self.members[row] = new_name
        event.Skip()

    def update_diagonals(self):
        n = len(self.members)
        for idx in range(n):
            total_owed_to_me = sum(float(self.GetCellValue(idx, j)) for j in range(n) if j != idx)
            total_i_owe = sum(float(self.GetCellValue(i, idx)) for i in range(n) if i != idx)
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

class GroupPanel(wx.Panel):
    def __init__(self, parent, group_name):
        super().__init__(parent)
        self.group_name = group_name
        self.members = ["You"]
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
        new_member = wx.GetTextFromUser("Enter member name:")
        if new_member and new_member not in self.members:
            self.members.append(new_member)
            new_idx = len(self.members) - 1
            
            # Add new row and column
            self.debt_grid.AppendRows(1)
            self.debt_grid.AppendCols(1)
            
            # Initialize new row/column cells
            for j in range(len(self.members)):
                # New row initialization
                self.debt_grid.SetCellValue(new_idx, j, "0.00")
                self.debt_grid.SetReadOnly(new_idx, j, True)
                self.debt_grid.SetCellBackgroundColour(new_idx, j, wx.Colour(240, 240, 240))
                
                # New column initialization
                self.debt_grid.SetCellValue(j, new_idx, "0.00")
                self.debt_grid.SetReadOnly(j, new_idx, True)
                self.debt_grid.SetCellBackgroundColour(j, new_idx, wx.Colour(240, 240, 240))
            
            # Update labels and comboboxes
            self.debt_grid.SetRowLabelValue(new_idx, new_member)
            self.debt_grid.SetColLabelValue(new_idx, new_member)
            self.lender.Append(new_member)
            self.borrower.Append(new_member)
            self.debt_grid.update_diagonals()

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
        
        # Update matrix
        lender_idx = self.members.index(lender)
        borrower_idx = self.members.index(borrower)
        
        # Update lender -> borrower cell
        current = float(self.debt_grid.GetCellValue(lender_idx, borrower_idx) or 0.0)
        new_value = current + amount
        self.debt_grid.SetCellValue(lender_idx, borrower_idx, f"{new_value:.2f}")
        self.debt_grid.update_cell_style(lender_idx, borrower_idx)
        
        # Update net balances
        self.debt_grid.update_diagonals()

class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="Financial Manager", size=(800, 600))
        self.notebook = wx.Notebook(self)
        self.add_group("Default Group")
        
        # Menu bar
        menubar = wx.MenuBar()
        file_menu = wx.Menu()
        
        # Create menu item and bind separately
        self.add_group_item = file_menu.Append(wx.ID_ANY, "Add Group")
        menubar.Append(file_menu, "File")
        self.SetMenuBar(menubar)
        
        # Bind using the menu item's ID
        self.Bind(wx.EVT_MENU, self.on_add_group, id=self.add_group_item.GetId())
        
        self.Show()

    def add_group(self, name):
        panel = GroupPanel(self.notebook, name)
        self.notebook.AddPage(panel, name)

    def on_add_group(self, event):
        name = wx.GetTextFromUser("Group name:")
        if name: 
            self.add_group(name)

if __name__ == "__main__":
    app = wx.App()
    MainFrame()
    app.MainLoop()