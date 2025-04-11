# Import libraries
import sqlite3
from string import printable
from tokenize import blank_re
from unittest import result
import pyotp
import time
import tkinter as tk
from tkinter import ttk, messagebox, StringVar

# Define global variables
accountType = "None"
userID = 1874

# Connect to SQLite database
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Functions - Authentication

# Function to fetch the authentication key of an admin by primary key
def fetchAuthByID(enteredID, table):
    try:
        # Query to fetch the authentication key
        query = f"SELECT authenticationKey FROM {table} WHERE rowid = {enteredID}"
        cursor.execute(query)
        
        # Fetch the result
        result = cursor.fetchone()
        
        if result:
            return result[0]
        else:
            messagebox.showerror("Database Error", f"No user was found under: {enteredID}")
            return None
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", str(e))
        return None

# Function to generate OTP based off of authKey
def generateAuthKey(authKey):
    currentTime = int(time.time())
    totp = pyotp.TOTP(str(authKey))
    otp0 = totp.at(currentTime-30)
    otp1 = totp.at(currentTime)
    otp2 = totp.at(currentTime+30)
    otp = [otp0, otp1, otp2]
    return otp


    
# Main program



class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LDP System")
        self.geometry("1000x600")
        self.resizable(True, True)
        self.current_frame = None
        self.switchFrame(Login) 

    def switchFrame(self, frame_class, *args, **kwargs):
        # Destroys current frame
        if self.current_frame:
            self.current_frame.destroy()
        # Creates new frame
        self.current_frame = frame_class(self, *args, **kwargs)
        self.current_frame.pack(fill="both", expand=True)

class Login(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        tk.Label(self, text="Account Login", font=("San Francisco", 24)).pack(pady=10)

        # Login Layout
        Login = tk.Frame(self)
        Login.pack(pady=20)
        tk.Label(Login, text="Account ID", borderwidth=2, padx=10, pady=10).grid(row=0, column=0)
        enteredID = tk.Text(Login, height=1, width=5, borderwidth=2)
        enteredID.grid(row=0, column=1)
        tk.Label(Login, text="6 Digit Authentication Code", borderwidth=2, padx=10, pady=10).grid(row=1, column=0)
        userCode = tk.Text(Login, height=1, width=6, wrap="word", borderwidth=2)
        userCode.grid(row=1, column=1)
        ttk.Button(Login, text="Login", command=lambda: self.authUser(enteredID, userCode)).grid(row=3, column=0, padx=10, pady=10)

    # Function to Authenticate User

    def authUser(self, enteredID, userCode):        
        global accountType
        global userID
        enteredID = enteredID.get("1.0", tk.END).strip()
        userCode = userCode.get("1.0", tk.END).strip()
        ID = [[adminFrame, distributorFrame, customerFrame],[2, 4, 5],["tblAdmin", "tblDistributor", "tblCustomer"]]
        try:
            arrayPos = ID[1].index(len(enteredID))  # Look for the length in ID[1]
        except ValueError:
            messagebox.showerror("User Error","Not Logged In, Incorrect ID")
        accountType = ID[0][arrayPos]
        userID = enteredID
        table = ID[2][arrayPos]
        correctKey = generateAuthKey(fetchAuthByID(enteredID, table))
        if userCode in correctKey:
            self.master.switchFrame(accountType)
        else:
            messagebox.showerror("User Error", "Not Logged In, Incorrect Code")
            return False


class adminFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        tk.Label(self, text="Admin Home Page", font=("San Francisco", 24)).pack(pady=10)

        # Hex grid layout
        buttons_frame = tk.Frame(self)
        buttons_frame.pack(pady=20) 
        ttk.Button(buttons_frame, text="View Orders", command=lambda: master.switchFrame(OrderViewPage)).grid(row=0, column=0, padx=10, pady=10)
        ttk.Button(buttons_frame, text="View Customers", command=lambda: master.switchFrame(CustomerViewPage)).grid(row=1, column=0, padx=10, pady=10)
        ttk.Button(buttons_frame, text="View Distributors", command=lambda: master.switchFrame(DistributorViewPage)).grid(row=2, column=0, padx=10, pady=10)
        ttk.Button(buttons_frame, text="Log Out", command=self.master.destroy).grid(row=0, column=1, padx=10, pady=10)
        ttk.Button(buttons_frame, text="Customer Order Form", command=lambda: master.switchFrame(adminOrder)).grid(row=1, column=1, padx=10, pady=10)
        ttk.Button(buttons_frame, text="Distributor Pay List", command=lambda: master.switchFrame(distributorPayList)).grid(row=2, column=1, padx=10, pady=10)

class distributorPayList(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.columns_to_display = ["distributorID", "distributorFName", "distributorLName", "distributorPay"]
        tk.Label(self, text="Distributor Pay List", font=("San Fancisco", 24)).pack(pady=10)
        # Treeview widget for displaying data
        self.tree = ttk.Treeview(self, columns=self.columns_to_display, show="headings")
        self.tree.pack(fill="both", expand=True)
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        columns_str = ", ".join(self.columns_to_display)
        query = f"SELECT {columns_str} FROM tblDistributor"
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        for col in self.columns_to_display:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="w")

        for row in rows:
            self.tree.insert("", "end", values=row)

        self.tree.pack(fill="both", expand=True)

        buttonsFrame = tk.Frame(self)
        buttonsFrame.pack(pady=10)

        ttk.Button(buttonsFrame, text="Reset Payments", command=lambda: self.resetPayments(rows)).grid(row=0, column=4, padx=10, pady=5)
        ttk.Button(buttonsFrame, text="Back to Home", command=lambda: self.master.switchFrame(adminFrame)).grid(row=0, column=5, padx=10, pady=5)

    def resetPayments(self, rows):
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        for row in rows:
            query = f"UPDATE tblDistributor SET distributorPay = 0 WHERE distributorID = {row[0]}"
            cursor.execute(query)
            conn.commit()
        conn.close

    def populateList(self):
        try:
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()
            columns_str = ", ".join(self.columns_to_display)
            query = f"SELECT {columns_str} FROM {self.table_name}"
            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()

            self.tree.delete(*self.tree.get_children())

            for row in rows:
                self.tree.insert("", "end", values=row)

        except sqlite3.Error as e:
            messagebox.showerror("Database Error", str(e))

class adminOrder(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        tk.Label(self, text="Customer Order Form", font=("San Francisco", 24)).pack(pady=10)


        orderForm = tk.Frame(self)
        orderForm.pack(pady=20)
        # Define order rows
        orderFields = ["orderDueDate", "orderPostCode", "orderHousesNum", "distributorID", "customerID"]
        # Create dictionary for Text fields
        self.newRow = {}
        # Create form by itereating betweeen each row name
        for row in orderFields:
            if row[0] == "o":
                tk.Label(orderForm, text=row[5:]).grid(column=0, padx=15, pady=15)
            else:
                tk.Label(orderForm, text=row).grid(column=0, padx=15, pady=15)
            newRow = tk.Text(orderForm, height = 1, width = 25)
            newRow.grid(column=1)
            self.newRow[row] = newRow
        ttk.Button(orderForm, text="Submit", command=lambda: self.submit(orderFields)).grid(padx=10, pady=5)
        ttk.Button(orderForm, text="Back to Home", command=lambda: self.master.switchFrame(adminFrame)).grid(padx=10, pady=5)

    def submit(self, orderFields):
        # Get what's in the text fields
        result = []
        for col, newRow in self.newRow.items():
            text = str(newRow.get("1.0", "end-1c"))
            result.append(text)

        # Generate Sample Vars
        date = str(time.strftime("%d%m%Y"))
        cost = 150
        orderStatus = 0

        # Order Record
        queryOrder = "INSERT INTO tblOrder (orderStatus, orderDate, " + ", ".join(orderFields) + f") VALUES ('{orderStatus}', '{date}', " + ", ".join(f"'{value}'" for value in result) + ")"
        customerID = queryOrder[-7:-2]
        try:
            cursor.execute(queryOrder) 
            conn.commit()
            orderID = cursor.lastrowid
            messagebox.showinfo("Successful Operation", "Record created successfully.")
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", str(e))

        # Invoice Record
        queryInvoice = f"INSERT INTO tblInvoice (invoiceAmount, invoiceOrderID, invoiceCustomerID) VALUES ('{cost}', '{orderID}', '{customerID}')"
        try:
            cursor.execute(queryInvoice) 
            conn.commit()
            messagebox.showinfo("Successful Operation", "Record created successfully.")
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", str(e))
        
        messagebox.showinfo("Order Cost",f"The cost for this order will be \u00A3{cost}")
        self.master.switchFrame(adminFrame)

class BaseViewPage(tk.Frame):
    def __init__(self, master, table_name, columns_to_display):
        super().__init__(master)
        self.master = master
        self.table_name = table_name
        self.columns_to_display = columns_to_display
        self.filters = {"category": None, "value": None}

        tk.Label(self, text=f"View {table_name[3:].capitalize()}", font=("San Francisco", 20)).pack(pady=10)

        # Table frame
        table_frame = tk.Frame(self)
        table_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Treeview widget for displaying data
        self.tree = ttk.Treeview(table_frame, columns=self.columns_to_display, show="headings")
        for col in self.columns_to_display:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="w")
       
        
        self.tree.pack(fill="both", expand=True)

        self.populateList()

        self.tree.bind("<Button-3>", self.rightClick)

        # Filter options
        filter_frame = tk.Frame(self)
        filter_frame.pack(pady=10)
        tk.Label(filter_frame, text="Filter Category:").grid(row=0, column=0, padx=10, pady=5)
        self.filter_category = ttk.Combobox(filter_frame, state="readonly", values=self.columns_to_display)
        self.filter_category.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(filter_frame, text="Filter Value:").grid(row=0, column=2, padx=10, pady=5)
        self.filter_value = ttk.Combobox(filter_frame, state="readonly")
        self.filter_value.grid(row=0, column=3, padx=10, pady=5)

        self.filter_category.bind("<<ComboboxSelected>>", self.updateFilterValues)
        ttk.Button(filter_frame, text="Apply Filter", command=self.apply_filter).grid(row=0, column=4, padx=10, pady=5)
        ttk.Button(filter_frame, text="Back to Home", command=lambda: self.master.switchFrame(adminFrame)).grid(row=0, column=5, padx=10, pady=5)

        if self.table_name == "tblOrder":
            return
        else:
            ttk.Button(self, text="Add Record", command=self.addRecord).pack(pady=10)

    def rightClick(self, event):
        # Create a context menu
        context_menu = tk.Menu(self.master, tearoff=0)
    
        # Add a command to the menu
        context_menu.add_command(label="Remove Record", command=lambda: self.removeRecord(self.getSelectedID(event)))
    
        # Display the context menu at the mouse position
        context_menu.post(event.x_root, event.y_root)
        

    def showContextMenu(self, event, item):
        # Create a context menu
        context_menu = tk.Menu(self.master, tearoff=0)
    
        # Add a command to the menu
        context_menu.add_command(label="Remove Record", command=lambda: self.removeRecord(self.getSelectedID(event)))
    
        # Display the context menu at the mouse position
        context_menu.post(event.x_root, event.y_root)

    def getSelectedID(self, event):
        row = self.tree.identify("item", event.x, event.y)
        if row:
            primary_key = self.tree.item(row)["values"][0]
            return str(primary_key)
        else:
            messagebox.showerror("No row selected", "Please select a row.")

    def removeRecord(self, record):
        try:
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()
            query = f"DELETE FROM {self.table_name} WHERE rowid = '" + str(record) + "'"
            cursor.execute(query)
            conn.commit()
            conn.close()
            self.populateList()
            messagebox.showinfo("Successful Operation", "Record removed successfully.")
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", str(e))

    def updateFilterValues(self, event=None):
        selected_category = self.filter_category.get()
        try:
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()
            cursor.execute(f"SELECT DISTINCT {selected_category} FROM {self.table_name}")
            values = [row[0] for row in cursor.fetchall()]
            conn.close()
            self.filter_value['values'] = values
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", str(e))

    def populateList(self):
        try:
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()
            columns_str = ", ".join(self.columns_to_display)
            query = f"SELECT {columns_str} FROM {self.table_name}"
            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()

            self.tree.delete(*self.tree.get_children())

            for row in rows:
                self.tree.insert("", "end", values=row + ("Remove", "View Full"))

        except sqlite3.Error as e:
            messagebox.showerror("Database Error", str(e))

    def apply_filter(self):
        self.filters["category"] = self.filter_category.get()
        self.filters["value"] = self.filter_value.get()
        self.populateList()
    
    def addRecord(self):
        self.addRecord = tk.Toplevel(self)
        title = "Create" + self.table_name[3:] + "Record"
        self.addRecord.title(title)
        self.addRecord.geometry("400x700")

        # Dictionary for Text Widgets
        self.newRecord = {}
        # New Record Layout
        
        if self.table_name[3] == "D":
            tableType = 11
        else:
            tableType = 8

        for col in self.columns_to_display:
            text = col[tableType:]
            tk.Label(self.addRecord, text=text).grid(padx = 5, pady = 5)
            newRecord = tk.Text(self.addRecord, height = 1, width = 25)
            newRecord.grid(column = 1, padx = 5, pady = 5)
            self.newRecord[col] = newRecord
        ttk.Button(self.addRecord, text="Submit", command=self.submit).grid()

    def submit(self):
        result = []
        for col, newRecord in self.newRecord.items():
            text = str(newRecord.get("1.0", "end-1c"))
            result.append(text)
        authKey = pyotp.random_base32()
        messagebox.showinfo("Authentication Key", f"This account's authentication key used to log in is {authKey}, we recommend the user to reset this for security reasons!")
        query = "INSERT INTO " + str(self.table_name) + " (authenticationKey, " + ", ".join(self.columns_to_display) + f") VALUES ('{authKey}', " + ", ".join(f"'{value}'" for value in result) + ")"
        try:
            cursor.execute(query) 
            conn.commit()
            messagebox.showinfo("Successful Operation", "Record created successfully.")
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", str(e))
        self.addRecord.destroy()   

class CustomerViewPage(BaseViewPage):
    def __init__(self, master):
        super().__init__(master, "tblCustomer", ["customerID", "customerEmail", "customerName", "customerNotes", "customerPhone", "customerRate"])

class DistributorViewPage(BaseViewPage):
    def __init__(self, master):
        super().__init__(master, "tblDistributor", ["distributorID", "distributorFName", "distributorLName", "distributorEmail", "distributorPhone", "distributorPay", "distributorCurrentOrder", "distributorRate"])

class OrderViewPage(BaseViewPage):
    def __init__(self, master):
        super().__init__(master, "tblOrder", ["orderID", "orderDate", "orderDueDate", "orderPostCode", "orderHousesNum", "orderMap", "distributorID", "orderStatus", "customerID"])


class customerFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        tk.Label(self, text="Customer Home Page", font=("San Francisco", 24)).pack(pady=10)

        # Grid layout
        customerDetails = tk.Frame(self)
        customerDetails.pack(pady=20)
        # Account Details
        queryCustomer = f"SELECT customerEmail, customerName, customerPhone FROM tblcustomer WHERE rowid = '{userID}'"
        try:
            cursor.execute(queryCustomer) 
            conn.commit()
            customerResult = cursor.fetchall()
            customerEmail, customerName, customerPhone = customerResult[0]
            messagebox.showinfo("Successful Operation", "Details Receieved Successfully")
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", str(e))
                # Account Details
        queryOrderStats = f"SELECT COUNT(orderID) AS totalOrders, SUM(orderHousesNum) AS totalHouses, MAX(orderDate) AS mostRecentOrder FROM tblOrder WHERE customerID = '{userID}' ORDER BY orderDate DESC LIMIT 3"
        try:
            cursor.execute(queryOrderStats) 
            conn.commit()
            orderStatsResult = cursor.fetchall()
            totalOrders, totalHouses, mostRecentOrder = orderStatsResult[0]
            messagebox.showinfo("Successful Operation", "Details Receieved Successfully")
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", str(e))
        queryOrder = f"SELECT orderPostCode, orderDate, orderStatus FROM tblOrder WHERE customerID = '{userID}' ORDER BY orderDate DESC LIMIT 3"
        try:
            cursor.execute(queryOrder) 
            conn.commit()
            orderResult = cursor.fetchall()
            messagebox.showinfo("Successful Operation", "Details Receieved Successfully")
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", str(e))

        # Account Details
        ttk.Label(customerDetails, text="Account Details").grid(row=0, column=0)
        ttk.Label(customerDetails, text="Name").grid(row=1, column=0, padx=10, pady=10)
        ttk.Label(customerDetails, text="Phone Number").grid(row=2, column=0, padx=10, pady=10)
        ttk.Label(customerDetails, text="Email").grid(row=3, column=0, padx=10, pady=10)
        ttk.Label(customerDetails, text=f"{customerName}").grid(row=1, column=1, padx=10, pady=10)
        ttk.Label(customerDetails, text=f"{customerPhone}").grid(row=2, column=1, padx=10, pady=10)
        ttk.Label(customerDetails, text=f"{customerEmail}").grid(row=3, column=1, padx=10, pady=10)
        # Account Stats
        ttk.Label(customerDetails, text="Account Statistics").grid(row=5, column=0, padx=10, pady=10)
        ttk.Label(customerDetails, text="Total Orders").grid(row=7, column=0, padx=10, pady=10)
        ttk.Label(customerDetails, text="Total Houses Delivered To").grid(row=8, column=0, padx=10, pady=10)
        ttk.Label(customerDetails, text="Most Recent Order").grid(row=9, column=0, padx=10, pady=10)
        ttk.Label(customerDetails, text=f"{totalOrders}").grid(row=7, column=1, padx=10, pady=10)
        ttk.Label(customerDetails, text=f"{totalHouses}").grid(row=8, column=1, padx=10, pady=10)
        ttk.Label(customerDetails, text=f"{mostRecentOrder}").grid(row=9, column=1, padx=10, pady=10)
        # Past 3 Orders
        ttk.Label(customerDetails, text="Past 3 Orders").grid(row=0, column=2, padx=10, pady=10)

        for i, order in enumerate(orderResult):
            orderPostCode, orderDate, orderStatus = order
            ttk.Label(customerDetails, text="Order PostCode").grid(row=1 + i * 3, column=2, padx=10, pady=10)
            ttk.Label(customerDetails, text=f"{orderPostCode}").grid(row=1 + i * 3, column=3, padx=10, pady=10)
            ttk.Label(customerDetails, text="Order Date").grid(row=2 + i * 3, column=2, padx=10, pady=10)
            ttk.Label(customerDetails, text=f"{orderDate}").grid(row=2 + i * 3, column=3, padx=10, pady=10)
            ttk.Label(customerDetails, text="Order Status").grid(row=3 + i * 3, column=2, padx=10, pady=10)
            ttk.Label(customerDetails, text=f"{orderStatus}").grid(row=3 + i * 3, column=3, padx=10, pady=10)

        # Functions
        ttk.Button(customerDetails, text="Log Out", command=master.destroy).grid(row=0, column=4, padx=10, pady=10)
        ttk.Button(customerDetails, text="Change Account Details").grid(row=2, column=4, padx=10, pady=10)
        ttk.Button(customerDetails, text="Complete Order Form", command=lambda: self.customerOrderForm()).grid(row=4, column=4, padx=10, pady=10)
        ttk.Button(customerDetails, text="View All Orders").grid(row=6, column=4, padx=10, pady=10)
        ttk.Button(customerDetails, text="Copy Authentication Token").grid(row=7, column=4, padx=10, pady=10)
        ttk.Button(customerDetails, text="Reset Authentication Token").grid(row=8, column=4, padx=10, pady=10)
        ttk.Button(customerDetails, text="View Pending Invoices").grid(row=9, column=4, padx=10, pady=10)


    def changeDetails(self):
        messagebox.showinfo("Change Account Details", "This functionality will be added in the future.")

    def customerOrderForm(self):
        self.customerOrderForm = tk.Toplevel(self)
        self.customerOrderForm.title("Order Form")
        self.customerOrderForm.geometry("400x700")
        tk.Label(self.customerOrderForm, text="Customer Order Form", font=("San Francisco", 24)).pack(pady=10)

        orderForm = tk.Frame(self.customerOrderForm)
        orderForm.pack(pady=20)
        # Define order rows
        orderFields = ["orderDueDate", "orderPostCode", "orderHousesNum", "distributorID", "customerID"]
        # Create dictionary for Text fields
        self.newRow = {}
        # Create form by itereating betweeen each row name
        for row in orderFields:
            if row[0] == "o":
                # If the row name starts with "o", remove the first 5 letters, if not, leave it
                tk.Label(orderForm, text=row[5:]).grid(column=0, padx=15, pady=15)
            else:
                tk.Label(orderForm, text=row).grid(column=0, padx=15, pady=15)
            newRow = tk.Text(orderForm, height = 1, width = 25)
            newRow.grid(column=1)
            self.newRow[row] = newRow
        ttk.Button(orderForm, text="Submit", command=lambda: self.submit(orderFields)).grid(padx=10, pady=5)
        ttk.Button(orderForm, text="Close", command=lambda: self.customerOrderForm.destroy()).grid(padx=10, pady=5)

    def submit(self, orderFields):
        # Get what's in the text fields
        result = []
        for col, newRow in self.newRow.items():
            text = str(newRow.get("1.0", "end-1c"))
            result.append(text)

        # Generate Sample Vars
        date = str(time.strftime("%d%m%Y"))

        # The cost will be derived from the number of Houses using the customerRate in the future, orderHousesNum will also not be available for customers to edit
        cost = 150
        orderStatus = 0

        # Order Record
        queryOrder = "INSERT INTO tblOrder (orderStatus, orderDate, " + ", ".join(orderFields) + f") VALUES ('{orderStatus}', '{date}', " + ", ".join(f"'{value}'" for value in result) + ")"
        customerID = queryOrder[-7:-2]
        try:
            cursor.execute(queryOrder) 
            conn.commit()
            orderID = cursor.lastrowid
            messagebox.showinfo("Successful Operation", "Record created successfully.")
            messagebox.showinfo("Order Cost",f"The cost for this order will be \u00A3{cost}")
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", str(e))

        # Invoice Record
        queryInvoice = f"INSERT INTO tblInvoice (invoiceAmount, invoiceOrderID, invoiceCustomerID) VALUES ('{cost}', '{orderID}', '{customerID}')"
        try:
            cursor.execute(queryInvoice) 
            conn.commit()
            messagebox.showinfo("Successful Operation", "Record created successfully.")
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", str(e))
        
        messagebox.showinfo("Order Cost",f"The cost for this order will be \u00A3{cost}")
        self.customerOrderForm.destroy()
        del self.customerOrderForm

    def viewAllOrders(self):
        messagebox.showinfo("View all account information", "This functionality will be added in the future.")

    def copyAuthToken(self):
        messagebox.showinfo("Copy Authentication Token", "This functionality will be added in the future.")

    def resetAuthToken(self):
        messagebox.showinfo("Reset Authentication Token", "This functionality will be added in the future.")

    def pendingInvoices(self):
        messagebox.showinfo("Pending Invoices", "This functionality will be added in the future.")


class distributorFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        tk.Label(self, text="Distributor Home Page", font=("San Francisco", 24)).pack(pady=10)

        distributorDetails = tk.Frame(self)
        distributorDetails.pack(pady=20)

        # Gathering account stats, this will only return single values for each parameter
        statsQuery = f"SELECT COUNT(o.orderID) AS totalOrders, SUM(o.orderHousesNum) AS totalHouses, d.distributorPay, d.distributorRate FROM tblOrder o JOIN tblDistributor d ON o.distributorID = d.distributorID WHERE o.distributorID = {userID}"
        
        # Fetch the result
        try:
            cursor.execute(statsQuery)
            StatsResult = cursor.fetchall()
            totalOrders,totalHouses, distributorPay, distributorRate = StatsResult[0]
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", str(e))

        # Gethering Recent Order information, this is to return up to 3 of the most recent orders
        orderQuery = f"SELECT orderPostCode, orderHousesNum, orderDueDate FROM tblOrder WHERE distributorID = {userID} ORDER BY orderDate ASC LIMIT 3"
        cursor.execute(orderQuery)

        # Fetch the result
        try:
            orderResult = cursor.fetchall()
            if orderResult == []:
                raise ValueError("No recent orders found.")
            orderPostCode, orderHousesNum, orderDueDate = orderResult[0]
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", str(e))
        except ValueError as ve:
            messagebox.showinfo("Recent Order Error", ve)
        # Iterate Results
        for i, order in enumerate(orderResult):
            orderPostCode, orderHousesNum, orderDueDate = order

        # Grid Layout

        # Current Order Details
        ttk.Label(distributorDetails, text="Current Order").grid(row=0, column=0, padx=10, pady=10)
        ttk.Label(distributorDetails, text="Post Code").grid(row=1, column=0, padx=10, pady=10)
        ttk.Label(distributorDetails, text="Number of Houses").grid(row=2, column=0, padx=10, pady=10)
        ttk.Label(distributorDetails, text="Due Date").grid(row=3, column=0, padx=10, pady=10)
        ttk.Label(distributorDetails, text="Price").grid(row=4, column=0, padx=10, pady=10)

        tk.Entry(distributorDetails, textvariable=StringVar(value=orderPostCode), state='readonly').grid(row=1, column=1, padx=10, pady=10)
        tk.Entry(distributorDetails, textvariable=StringVar(value=orderHousesNum), state='readonly').grid(row=2, column=1, padx=10, pady=10)
        tk.Entry(distributorDetails, textvariable=StringVar(value=orderDueDate), state='readonly').grid(row=3, column=1, padx=10, pady=10)
        tk.Entry(distributorDetails, textvariable=StringVar(value=int(orderHousesNum) * int(distributorRate) / 20), state='readonly').grid(row=4, column=1, padx=10, pady=10)

        # Account Statistics
        ttk.Label(distributorDetails, text="Account Statistics").grid(row=6, column=0, padx=10, pady=10)
        ttk.Label(distributorDetails, text="Total Orders Completed").grid(row=7, column=0, padx=10, pady=10)
        ttk.Label(distributorDetails, text="Total Houses Delivered To").grid(row=8, column=0, padx=10, pady=10)
        ttk.Label(distributorDetails, text="Distributor Pending Pay").grid(row=9, column=0, padx=10, pady=10)

        # Use StringVar with tk.Entry for readonly fields
        tk.Entry(distributorDetails, textvariable=StringVar(value=totalOrders), state='readonly').grid(row=7, column=1, padx=10, pady=10)
        tk.Entry(distributorDetails, textvariable=StringVar(value=totalHouses), state='readonly').grid(row=8, column=1, padx=10, pady=10)
        tk.Entry(distributorDetails, textvariable=StringVar(value=distributorPay), state='readonly').grid(row=9, column=1, padx=10, pady=10)

        # Past 3 Orders
        ttk.Label(distributorDetails, text="Past 3 Orders").grid(row=0, column=2, padx=10, pady=10)

        # Iteration Loop for past orders
        for i, order in enumerate(orderResult):
            orderPostCode, orderHousesNum, orderDueDate = order
            orderAmount = int(distributorRate) * int(orderHousesNum) / 20
            
            # Use Entry widgets for each of the fields
            ttk.Label(distributorDetails, text="Order PostCode").grid(row=3 * i + 1, column=2, padx=10, pady=10)
            tk.Entry(distributorDetails, textvariable=StringVar(value=orderPostCode), state='readonly').grid(row=3 * i + 1, column=3, padx=10, pady=10)
            
            ttk.Label(distributorDetails, text="Order Date").grid(row=3 * i + 2, column=2, padx=10, pady=10)
            tk.Entry(distributorDetails, textvariable=StringVar(value=orderDueDate), state='readonly').grid(row=3 * i + 2, column=3, padx=10, pady=10)
            
            ttk.Label(distributorDetails, text="Balance Added").grid(row=3 * i + 3, column=2, padx=10, pady=10)
            tk.Entry(distributorDetails, textvariable=StringVar(value=f"{orderAmount}"), state='readonly').grid(row=3 * i + 3, column=3, padx=10, pady=10)

    # Function Buttons

    def changeAccountDetails(self):
        messagebox.showinfo("Missing Function", "This Functionality will be added in the future")

    def viewAllOrders(self):
        messagebox.showinfo("Missing Function", "This Functionality will be added in the future")

    def copyAuthKey(self):
        messagebox.showinfo("Missing Function", "This Functionality will be added in the future")

    def resetAuthKey(self):
        messagebox.showinfo("Missing Function", "This Functionality will be added in the future")

if __name__ == "__main__":
    app = Application()
    app.mainloop()

    
# Close the connection
conn.close()
