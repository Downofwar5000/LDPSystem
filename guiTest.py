import tkinter as tk
from tkinter import ttk

root = tk.Tk()
root.title("Parameterised StringVar Example")

# This is your parent container
customerDetails = ttk.Frame(root)
customerDetails.pack(padx=20, pady=20)

# Example values (these might come from your data)
totalOrders = 10
totalHouses = 50
mostRecentOrder = "2024-02-25"

# Dictionary mapping field names to values
fields = {
    "totalOrders": totalOrders,
    "totalHouses": totalHouses,
    "mostRecentOrder": mostRecentOrder
}

# Create a persistent container to hold your StringVars
readonly_vars = {}

# Starting row for grid placement
start_row = 7

# Loop through the fields, create a StringVar for each, store it, and attach it to an Entry widget
for idx, (field_name, field_value) in enumerate(fields.items()):
    # Create a persistent StringVar; casting to string to avoid any issues if field_value is not already a string
    sv = tk.StringVar(value=str(field_value))
    readonly_vars[field_name] = sv  # Save it so it won't be garbage-collected

    # Create the ttk.Entry; note state is "readonly" so text will be non-editable but selectable
    entry = ttk.Entry(customerDetails, textvariable=sv, state='readonly', style="TEntry")
    # Place the entry in the grid; rows start at start_row and columns set as needed
    entry.grid(row=start_row + idx, column=1, padx=10, pady=10)

root.mainloop()
