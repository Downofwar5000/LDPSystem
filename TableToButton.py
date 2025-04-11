import tkinter as tk
from tkinter import ttk

class DynamicGridApp(tk.Tk):
    def __init__(self, variable=None):
        super().__init__()
        self.title("Dynamic Grid App")
        self.geometry("400x300")
        
        # Variable that determines what to display
        self.variable = variable
        
        # Main frame to hold the content
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Refresh the view initially
        self.refresh_view()

    def refresh_view(self):
        # Clear existing content
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        # Check the variable and display accordingly
        if self.variable:
            self.display_grid()
        else:
            self.display_button()

    def display_grid(self):
        # Display a grid of information
        data = self.variable  # Assumes it's a 2D list or similar structure
        for i, row in enumerate(data):
            for j, value in enumerate(row):
                ttk.Label(self.main_frame, text=value, relief=tk.RIDGE).grid(row=i, column=j, padx=5, pady=5)

    def display_button(self):
        # Display a button to indicate no data available
        def on_button_click():
            sample_data = [
            ["Name", "Age", "City"],
            ["Alice", "30", "New York"],
            ["Bob", "25", "San Francisco"]
            ]
            app.set_variable(sample_data)
        
        button = ttk.Button(self.main_frame, text="No Data Available - Click Me", command=on_button_click)
        button.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)

    def set_variable(self, new_variable):
        # Update the variable and refresh the view
        self.variable = new_variable
        self.refresh_view()

# Example usage
if __name__ == "__main__":
    # App instance with no data
    app = DynamicGridApp()

    # Set up some controls for testing
    def set_grid_data():
        sample_data = [
            ["Name", "Age", "City"],
            ["Alice", "30", "New York"],
            ["Bob", "25", "San Francisco"]
        ]
        app.set_variable(sample_data)

    def clear_data():
        app.set_variable(None)
    
    ttk.Button(app, text="Show Grid Data", command=set_grid_data).pack(pady=5)
    ttk.Button(app, text="Clear Data", command=clear_data).pack(pady=5)
    
    app.mainloop()
