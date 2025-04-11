import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

def on_right_click(event):
    # Get the item that was right-clicked
    item = tree.identify('item', event.x, event.y)
    
    if item:  # If a valid item is clicked
        # You can show a menu or trigger an action here
        show_context_menu(event, item)

def show_context_menu(event, item):
    # Create a context menu
    context_menu = tk.Menu(root, tearoff=0)
    
    # Add a command to the menu
    context_menu.add_command(label="Action 1", command=lambda: perform_action(item))
    context_menu.add_command(label="Action 2", command=lambda: perform_action(item))
    
    # Display the context menu at the mouse position
    context_menu.post(event.x_root, event.y_root)

def perform_action(item):
    # You can define actions based on the selected row
    values = tree.item(item, "values")
    messagebox.showinfo("Row Data", f"Action performed on: {values}")

# Create the main window
root = tk.Tk()
tree = ttk.Treeview(root, columns=("col1", "col2", "col3"), show="headings")

# Set up headings
tree.heading("col1", text="Column 1")
tree.heading("col2", text="Column 2")
tree.heading("col3", text="Column 3")

# Add sample data
tree.insert("", "end", values=("Data 1", "Data 2", "Data 3"))
tree.insert("", "end", values=("Data 4", "Data 5", "Data 6"))

# Configure columns
tree.column("col1", width=100, anchor="center")
tree.column("col2", width=100, anchor="center")
tree.column("col3", width=100, anchor="center")

# Bind the right-click event to the treeview
tree.bind("<Button-3>", on_right_click)

tree.pack(fill=tk.BOTH, expand=True)

root.mainloop()

