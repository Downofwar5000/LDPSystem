# Import libraries
import pyotp
import time
import tkinter as tk
from tkinter import NSEW, PhotoImage, ttk, messagebox, StringVar
import json
import osmnx as ox
import geopandas as gpd
import networkx as nx
import matplotlib.pyplot as plt
import contextily as ctx
from geopy.geocoders import Nominatim
from scipy.spatial.distance import euclidean
from shapely.geometry import Point, LineString
from PIL import Image, ImageTk


# Functions - Database

def loadJson(filename):
    # Loads a JSON file and returns its contents
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []  # Return an empty list if file doesn't exist or is corrupted

def writeJson(filename, data):
    # Writes data to a JSON file
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

def buildIndex():
    # Rebuilds the index file for all tables in the database
    indexData = {}

    for table in ["admin", "customer", "distributor", "order"]:
        tableFile = f"{dbPath}/{table}.json"
        tableData = loadJson(tableFile)

        indexData[table + "Index"] = {str(entry.get(table + "ID")): i for i, entry in enumerate(tableData) if table + "ID" in entry}

    writeJson(indexFile, indexData)
    print("Index rebuilt successfully.")

def submit(self, orderFields, result):
    # Load JSON data
    tableOrder = loadJson(f"{dbPath}/order.json")
    indexData = loadJson(f"{dbPath}/_index.json")

    # Generate necessary fields
    date = str(time.strftime("%d%m%Y"))
    orderStatus = 0

    # Generate new unique Order ID
    orderID = max([record.get("orderID", 0) for record in tableOrder], default=0) + 1

    # Extract customerID from the input
    customerTextWidget = self.orderRow.get("customerID")
    customerID = customerTextWidget.get("1.0", "end-1c").strip()

    # Verification


    # Ensure all fields except distributor are filled
        
    if not result[0] or not result[1] or not result[3]:
        messagebox.showerror("Missing Fields", "Please fill in all required fields.")
        return

    # Ensure fields are filled with acceptable values


    # Check if the due date is in the future
    try:
        date1 = time.strptime((result[0]), "%d%m%Y")
    except ValueError:
        messagebox.showerror("Invalid Date", "Please enter a valid 8-digit date in the format DDMMYYYY.")
        return

    date2 = time.strptime(date, "%d%m%Y")

    if date1 < date2:
        messagebox.showerror("Invalid Date", "Please enter a date in the future.")
        return

    # Check if the distributorID is correct

    if result[2]:
        if not any(int(result[2]) in record for record in loadJson(f"{dbPath}/distributor.json")):
            messagebox.showerror("Invalid Distributor", "Please enter a valid distributor ID.")
            return
    else:
        messagebox.showinfo("Distributor ID", "No distributor ID entered, the order will be assigned to the next available distributor.")

    # Check if the customerID is correct

    if not any(result[3] in record for record in loadJson(f"{dbPath}/customer.json")):
        messagebox.showerror("Invalid Customer", "Please enter a valid customer ID.")
        return

    # Check if the postcode exists
    try:
        HousesNum = getHouseholdNetwork(result[1])
    except ValueError:
        messagebox.showerror("Invalid Postcode", "Please enter a valid postcode.")
        return

    # Generate node map for the order
    HousesNum = getHouseholdNetwork(result[1])

    # Calculate cost based on customer rate

    customerData = loadJson(f"{dbPath}/customer.json")
    customerIndex = indexData.get("customerIndex", {}).get(customerID)
    customerRecord = customerData[customerIndex]
    cost = customerRecord.get("customerRate", 0) * HousesNum / 10

    # Fill in the new order details
    newOrder = {
        "orderID": orderID,
        "orderStatus": str(orderStatus),
        "orderDate": str(date),
        "invoiceAmount": str(cost),
        "orderMap": f"./Maps/{result[1]}.png",
        "orderHousesNum": str(HousesNum)
    }

    # Add dynamic fields 
    for field, value in zip(orderFields, result):
        newOrder[field] = value

    # Append order to the database
    tableOrder.append(newOrder)
    writeJson(f"{dbPath}/order.json", tableOrder)

    # Update the index and save it
    buildIndex()

    # Show confirmation messages
    messagebox.showinfo("Successful Operation", "Record created successfully.")
    messagebox.showinfo("Order Cost", f"The cost for this order will be \u00A3 {cost}")


# Functions - Authentication

def copyAuthKey():
    # Copies the authentication key for the current user
    authKey = fetchAuthByID(userId)
    app.clipboard_clear()
    app.clipboard_append(authKey)
    app.update()  # now it stays on the clipboard after the window is closed
    messagebox.showinfo("Copy Authentication Token", "Authentication key copied to clipboard.")

def resetAuthKey():
    # Resets the authentication key for the current user
    authKey = pyotp.random_base32()
    tableFile = f"{dbPath}/{table}.json"
    indexData = loadJson(indexFile)

    if table + "Index" not in indexData or str(userId) not in indexData[table + "Index"]:
        print(f"Error: Record ID {userId} not found in {table}.")

    recordPosition = indexData[table + "Index"][str(userId)]
    tableData = loadJson(tableFile)

    tableData[recordPosition]["authenticationKey"] = authKey
    writeJson(tableFile, tableData)

    messagebox.showinfo("Reset Authentication Token", f"New authentication key generated: {authKey}")
    copyAuthKey()

def fetchAuthByID(enteredID):
    # Fetches the authentication key for a given user ID
    indexData = loadJson(indexFile)
    tableFile = f"{dbPath}/{table}.json"

    recordPosition = indexData[table + "Index"][str(enteredID)]
    tableData = loadJson(tableFile)

    authKey = tableData[recordPosition]["authenticationKey"]
    
    print(authKey)
    return authKey

def generateAuthKey(authKey):
    # Generates a list of 3 OTPs based on the current time, given an authentication key
    print(authKey)
    currentTime = int(time.time())
    totp = pyotp.TOTP(str(authKey))
    otp0 = totp.at(currentTime-30)
    otp1 = totp.at(currentTime)
    otp2 = totp.at(currentTime+30)
    otp = [otp0, otp1, otp2]
    print(otp)
    return otp


# Function - Mapping

def getHouseholdNetwork(postcode, country="UK"):
    geolocator = Nominatim(user_agent="geo_locator")
    
    # Get coordinates of postcode
    location = geolocator.geocode(f"{postcode}, {country}", exactly_one=True)
    if not location:
        print("Postcode not found")
        return None

    lat, lon = location.latitude, location.longitude

    # Fetch buildings within a 500m radius which is a standard LDP leaflet drop
    buildings = ox.features_from_point((lat, lon), tags={'building': True}, dist=200)
    
    if buildings.empty:
        print("No buildings found in the area")
        return None

    # Extract centroids (representing households)
    buildings['centroid'] = buildings.geometry.centroid
    centroids = [(p.x, p.y) for p in buildings['centroid']]

    # Create a graph
    G = nx.Graph()
    for i, (x, y) in enumerate(centroids):
        G.add_node(i, pos=(x, y))

    # Connect nodes with all possible edges using geographic distances
    for i in range(len(centroids)):
        for j in range(i+1, len(centroids)):
            dist = euclidean(centroids[i], centroids[j])  # Euclidean distance in degrees
            G.add_edge(i, j, weight=dist)

    # Compute Minimum Spanning Tree (MST) for shortest connectivity
    mst = nx.minimum_spanning_tree(G)

    # Convert nodes to GeoDataFrame
    node_gdf = gpd.GeoDataFrame(geometry=[Point(x, y) for x, y in centroids], crs="EPSG:4326")
    
    # Convert edges to LineStrings **Fixed**
    edge_gdf = gpd.GeoDataFrame(
        geometry=[LineString([centroids[u], centroids[v]]) for u, v in mst.edges],
        crs="EPSG:4326"
    )

    # Convert to Web Mercator projection for better plotting
    node_gdf = node_gdf.to_crs(epsg=3857)
    edge_gdf = edge_gdf.to_crs(epsg=3857)
    
    # Plot
    fig, ax = plt.subplots(figsize=(10, 10))
    buildings.to_crs(epsg=3857).plot(ax=ax, color='gray', alpha=0.4, edgecolor='black')  # Buildings
    edge_gdf.plot(ax=ax, color="blue", linewidth=1.5)  # Network
    node_gdf.plot(ax=ax, color="red", markersize=10)  # Households

    # Add basemap
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron)

    plt.title(f"Household Network for {postcode}")

    # Save the figure
    plt.savefig(f"./Maps/{postcode}.png")

    plt.close(fig)  # Close the figure to free up memory

    print(f"Number of households in {postcode}: {len(centroids)}")
    return len(centroids)

# Define global variables

accountType = None
userId = 1001
table = "distributor"
dbPath = "./_database"
indexFile = f"{dbPath}/_index.json"


# Main program

# Create the main application window

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        buildIndex()
        self.title("LDP System")
        self.geometry("1000x600")
        self.resizable(True, True)
        self.currentFrame = None
        self.switchFrame(distributorFrame) 

    def switchFrame(self, frameClass, *args, **kwargs):
        # Destroys current frame
        if self.currentFrame:
            self.currentFrame.destroy()
        # Creates new frame
        self.currentFrame = frameClass(self, *args, **kwargs)
        self.currentFrame.pack(fill="both", expand=True)

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
        global userId
        global table
        enteredID = enteredID.get("1.0", tk.END).strip()
        userCode = userCode.get("1.0", tk.END).strip()
        ID = [[adminFrame, distributorFrame, customerFrame],[2, 4, 5],["admin", "distributor", "customer"]]
        try:
            arrayPos = ID[1].index(len(enteredID))  # Look for the length in ID[1]
        except ValueError:
            messagebox.showerror("User Error","Not Logged In, Incorrect ID")
        accountType = ID[0][arrayPos]
        userId = enteredID
        table = ID[2][arrayPos]
        correctKey = generateAuthKey(fetchAuthByID(enteredID))
        print(correctKey)
        if userCode in correctKey:
            self.master.switchFrame(accountType)
        else:
            messagebox.showerror("User Error", "Not Logged In, Incorrect Code")
            return False


# Inidividual Right Access Level frames for each user type

class adminFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.tableName = None
        self.columnsToDisplay = None
        self.filters = {"category": None, "value": None}
        self.initHomePage()

    def initHomePage(self):
        tk.Label(self, text="Admin Home Page", font=("San Francisco", 24)).pack(pady=10)

        # Hex grid layout
        buttonsFrame = tk.Frame(self)
        buttonsFrame.pack(pady=20) 
        ttk.Button(buttonsFrame, text="View Orders", command=lambda: self.switchToViewPage("order")).grid(row=0, column=0, padx=10, pady=10)
        ttk.Button(buttonsFrame, text="View Customers", command=lambda: self.switchToViewPage("customer")).grid(row=1, column=0, padx=10, pady=10)
        ttk.Button(buttonsFrame, text="View Distributors", command=lambda: self.switchToViewPage("distributor")).grid(row=2, column=0, padx=10, pady=10)
        ttk.Button(buttonsFrame, text="Log Out", command=self.master.destroy).grid(row=0, column=1, padx=10, pady=10)
        ttk.Button(buttonsFrame, text="Customer Order Form", command=self.customerOrderForm).grid(row=1, column=1, padx=10, pady=10)
        ttk.Button(buttonsFrame, text="Distributor Pay List", command=self.distributorPayList).grid(row=2, column=1, padx=10, pady=10)

    def switchToViewPage(self, tableName):
        self.tableName = tableName
        if tableName == "order":
            self.columnsToDisplay = ["orderID", "orderStatus", "orderDate", "invoiceAmount"]
        elif tableName == "customer":
            self.columnsToDisplay = ["customerID", "customerFName", "customerLName", "customerEmail"]
        else:
            self.columnsToDisplay = ["distributorID", "distributorFName", "distributorLName", "distributorPay"]

        self.clearFrame()
        self.viewPage()

    def clearFrame(self):
        for widget in self.winfo_children():
            widget.destroy()

    def viewPage(self):
        tk.Label(self, text=f"View {self.tableName.capitalize()}", font=("San Francisco", 20)).pack(pady=10)

        # Table frame
        tableFrame = tk.Frame(self)
        tableFrame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Treeview widget for displaying data
        self.tree = ttk.Treeview(tableFrame, columns=self.columnsToDisplay, show="headings")
        for col in self.columnsToDisplay:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="w")
       
        
        self.tree.pack(fill="both", expand=True)

        self.populateList()

        self.tree.bind("<Button-3>", self.rightClick)

        # Filter options
        filterFrame = tk.Frame(self)
        filterFrame.pack(pady=10)
        tk.Label(filterFrame, text="Filter Category:").grid(row=0, column=0, padx=10, pady=5)
        self.filterCategory = ttk.Combobox(filterFrame, state="readonly", values=self.columnsToDisplay)
        self.filterCategory.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(filterFrame, text="Filter Value:").grid(row=0, column=2, padx=10, pady=5)
        self.filterValue = ttk.Combobox(filterFrame, state="readonly")
        self.filterValue.grid(row=0, column=3, padx=10, pady=5)

        self.filterCategory.bind("<<ComboboxSelected>>", self.updateFilterValues)
        ttk.Button(filterFrame, text="Apply Filter", command=self.applyFilter).grid(row=0, column=4, padx=10, pady=5)
        ttk.Button(filterFrame, text="Back to Home", command=self.backToHome).grid(row=0, column=5, padx=10, pady=5)

        if not self.tableName == "order":
            ttk.Button(self, text="Add Record", command=self.addRecord).pack(pady=10)

    def rightClick(self, event):
        # Create a context menu
        contextMenu = tk.Menu(self.master, tearoff=0)
    
        # Add a command to the menu
        contextMenu.add_command(label="Remove Record", command=lambda: self.removeRecord(self.getSelectedID(event)))
        if self.tableName == "order":
            contextMenu.add_command(label="Mark as Paid", command=lambda: self.markAsPaid(self.getSelectedID(event)))
    
        # Display the context menu at the mouse position
        contextMenu.post(event.x_root, event.y_root)

    def getSelectedID(self, event):
        row = self.tree.identify("item", event.x, event.y)
        if row:
            primaryKey = self.tree.item(row)["values"][0]
            return str(primaryKey)
        else:
            messagebox.showerror("No row selected", "Please select a row.")

    def removeRecord(self, record):
        try:
            path = f"{dbPath}/{self.tableName}.json"

            # Load JSON data
            tableData = loadJson(path)

            # Load index
            indexData = loadJson(f"{dbPath}/_index.json")

            # Get the index dictionary for the table
            tableIndex = indexData.get(f"{self.tableName}Index", {})

            # Find record's position using the index
            recordPosition = tableIndex.get(record)

            if recordPosition is not None:
                # Remove the record
                tableData.pop(recordPosition)

                # Save updated JSON data
                writeJson(path, tableData)

                # Rebuild index to maintain consistency
                buildIndex()

                # Refresh UI
                self.populateList()
            
                messagebox.showinfo("Successful Operation", "Record removed successfully.")
            
            else:
                messagebox.showerror("Database Error", f"Record with ID {record} not found in index")
        except Exception as e:
            messagebox.showerror("Database Error", str(e))

    def markAsPaid(self, record):
        try:
            path = f"{dbPath}/{self.tableName}.json"
            # Load JSON data
            tableData = loadJson(path)
            # Load index
            indexData = loadJson(f"{dbPath}/_index.json")
            # Get the index dictionary for the table
            tableIndex = indexData.get(f"{self.tableName}Index", {})
            # Find record's position using the index
            recordPosition = tableIndex.get(record)
            if recordPosition is not None:
                if tableData[recordPosition]["orderStatus"] == "0":
                    # Mark the record as paid
                    tableData[recordPosition]["orderStatus"] = "1"
                    # Save updated JSON data
                    writeJson(path, tableData)
                    #Refresh UI
                    self.populateList()

                    messagebox.showinfo("Successful Operation", "Record marked as paid successfully.")
                else:
                    messagebox.showerror("Database Error", "Record is already marked as paid.")
            else:
                messagebox.showerror("Database Error", f"Record with ID {record} not found in index")
        except Exception as e:
            messagebox.showerror("Database Error", str(e))

    def updateFilterValues(self, event=None):
        try:
            selectedCategory = self.filterCategory.get()

            path = f"{dbPath}/{self.tableName}.json"

            # Load JSON data
            tableData = loadJson(path)

            # Extract unique values for the selected category
            values = list(set(record.get(selectedCategory, "") for record in tableData if selectedCategory in record))

            # Update filter values in UI
            self.filterValue["values"] = values

        except Exception as e:
            messagebox.showerror("Database Error", str(e))

    def populateList(self):

        # Remove all existing rows
        self.tree.delete(*self.tree.get_children())

        path = f"{dbPath}/{self.tableName}.json"     

        # Load the table data
        tableData = loadJson(path)

        # Apply filtering if a filter value is set
        filteredData = []
        if self.filters["value"] is not None:
            category = self.filters["category"]
            filterValue = self.filters["value"]
    
            # Ensure the category exists in the records and filter by value
            filteredData = [record for record in tableData if str(record.get(category, "")) == str(filterValue)]
        else:
            filteredData = tableData  # No filter applied, show all records

        # Extract only the required columns
        extractedData = [tuple(record.get(col, None) for col in self.columnsToDisplay) for record in filteredData]

        # Populate the treeview
        for row in extractedData:
            self.tree.insert("", "end", values=row)

    def applyFilter(self):
        self.filters["category"] = self.filterCategory.get()
        self.filters["value"] = self.filterValue.get()
        self.populateList()
    
    # Add Validation, and proper error messages
    def addRecord(self):
        self.addRecord = tk.Toplevel(self)
        title = "Create" + self.tableName.capitalize() + "Record"
        self.addRecord.title(title)
        self.addRecord.geometry("400x700")

        # Dictionary for Text Widgets
        self.newRecord = {}
        # New Record Layout
        
        if self.tableName == "distributor":
            tableType = 11
        else:
            tableType = 8

        for col in self.columnsToDisplay:
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
        
        newRecord = {"authenticationKey": authKey}
        newRecord.update({col: value for col, value in zip(self.columnsToDisplay, result)})

        path = f"{dbPath}/{self.tableName}.json"

        tableData = loadJson(path)

        # Determine a unique ID (if needed)
        newRecord[self.tableName + "ID"] = max([record.get(self.tableName + "ID", 0) for record in tableData], default=0) + 1

        # Append new record
        tableData.append(newRecord)

        # Save updated JSON data
        writeJson(path, tableData)

        buildIndex()

        messagebox.showinfo("Successful Operation", "Record created successfully.")

        self.addRecord.destroy()
        self.populateList()

    def customerOrderForm(self):
        self.clearFrame()
        tk.Label(self, text="Customer Order Form", font=("San Francisco", 24)).pack(pady=10)

        orderForm = tk.Frame(self)
        orderForm.pack(pady=20)
        # Define order rows
        orderFields = ["orderDueDate", "orderPostCode", "distributorID", "customerID"]
        # Create dictionary for Text fields
        self.orderRow = {}
        # Create form by itereating betweeen each row name
        for row in orderFields:
            if row[0] == "o":
                tk.Label(orderForm, text=row[5:]).grid(column=0, padx=15, pady=15)
            else:
                tk.Label(orderForm, text=row).grid(column=0, padx=15, pady=15)
            orderRow = tk.Text(orderForm, height = 1, width = 25)
            orderRow.grid(column=1)
            self.orderRow[row] = orderRow
        ttk.Button(orderForm, text="Submit", command=lambda: self.orderSubmit(orderFields)).grid(padx=10, pady=5)
        ttk.Button(orderForm, text="Back to Home", command=lambda: self.backToHome()).grid(padx=10, pady=5)

    def orderSubmit(self, orderFields):
        # Get order details from the text fields
        result = [str(orderRow.get("1.0", "end-1c")) for col, orderRow in self.orderRow.items()]

        submit(self, orderFields, result)

        # Switch frame after submission
        self.backToHome()

    def distributorPayList(self):
        self.clearFrame()
        tk.Label(self, text="Distributor Pay List", font=("San Francisco", 24)).pack(pady=10)

        # Treeview widget for displaying data
        self.tree = ttk.Treeview(self, columns=["distributorID", "distributorFName", "distributorLName", "distributorPay"], show="headings")
        self.tree.pack(fill="both", expand=True)

        # Load data from JSON
        distributors = loadJson(f"{dbPath}/distributor.json")

        # Set up Treeview headings
        for col in ["distributorID", "distributorFName", "distributorLName", "distributorPay"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="w")

        # Insert data into Treeview
        for distributor in distributors:
            values = [distributor.get(col, "N/A") for col in ["distributorID", "distributorFName", "distributorLName", "distributorPay"]]
            self.tree.insert("", "end", values=values)

        buttonsFrame = tk.Frame(self)
        buttonsFrame.pack(pady=10)

        ttk.Button(buttonsFrame, text="Reset Payments", command=lambda: self.resetPayments()).grid(row=0, column=4, padx=10, pady=5)
        ttk.Button(buttonsFrame, text="Back to Home", command=lambda: self.backToHome()).grid(row=0, column=5, padx=10, pady=5)

    def resetPayments(self):
        distributors = loadJson(f"{dbPath}/distributor.json")

        for distributor in distributors:
            distributor["distributorPay"] = 0

        writeJson(f"{dbPath}/distributor.json", distributors)
        messagebox.showinfo("Payment Reset", "All distributor payments have been reset to \u00A3 0.")

    def backToHome(self):
        self.clearFrame()
        self.initHomePage()

class customerFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        tk.Label(self, text="Customer Home Page", font=("San Francisco", 24)).pack(pady=10)

        # Grid layout
        customerDetails = tk.Frame(self)
        customerDetails.pack(pady=20)
        try:
            # Fetch JSON data
            customerData = loadJson(f"{dbPath}/customer.json")
            orderData = loadJson(f"{dbPath}/order.json")
            print(orderData)
            indexData = loadJson(f"{dbPath}/_index.json")

            # Get customer details
            customerIndex = indexData.get("customerIndex", {}).get(str(userId))
            if customerIndex is not None:
                customerRecord = customerData[customerIndex]
                customerEmail = customerRecord.get("customerEmail", "N/A")
                customerName = customerRecord.get("customerName", "N/A")
                customerPhone = customerRecord.get("customerPhone", "N/A")
            else:
                messagebox.showerror("Database Error", f"Customer with ID {userId} not found")

            # Get order statistics
            customerOrders = [order for order in orderData if order["customerID"] == str(userId)]
            totalOrders = len(customerOrders)
            totalHouses = sum(int(order.get("orderHousesNum", 0)) for order in customerOrders)
            mostRecentOrder = max((order["orderDate"] for order in customerOrders), default="N/A")

            # Get last 3 orders
            recentOrders = sorted(customerOrders, key=lambda x: x["orderDate"], reverse=True)[:3]
            orderResult = [(order["orderPostCode"], order["orderDate"], order["orderStatus"]) for order in recentOrders]

            recentOrders = orderResult
        except Exception as e:
            messagebox.showerror("Database Error", str(e))

        # Account Details
        ttk.Label(customerDetails, text="Account Details").grid(row=0, column=0)
        ttk.Label(customerDetails, text="Name").grid(row=1, column=0, padx=10, pady=10)
        ttk.Label(customerDetails, text="Phone Number").grid(row=2, column=0, padx=10, pady=10)
        ttk.Label(customerDetails, text="Email").grid(row=3, column=0, padx=10, pady=10)

        # Use tk.Entry for readonly fields
        customerNameField = tk.Entry(customerDetails, textvariable=tk.StringVar(value=customerName), state='readonly')
        customerNameField.grid(row=1, column=1, padx=10, pady=10)
        customerPhoneField = tk.Entry(customerDetails, textvariable=StringVar(value=customerPhone), state='readonly')
        customerPhoneField.grid(row=2, column=1, padx=10, pady=10)
        customerEmailField = tk.Entry(customerDetails, textvariable=StringVar(value=customerEmail), state='readonly')
        customerEmailField.grid(row=3, column=1, padx=10, pady=10)

        self.entryFields = {
            "customerName": customerNameField,
            "customerEmail": customerEmailField,
            "customerPhone": customerPhoneField
        }
        # Account Stats
        ttk.Label(customerDetails, text="Account Statistics").grid(row=5, column=0, padx=10, pady=10)
        ttk.Label(customerDetails, text="Total Orders").grid(row=7, column=0, padx=10, pady=10)
        ttk.Label(customerDetails, text="Total Houses Delivered To").grid(row=8, column=0, padx=10, pady=10)
        ttk.Label(customerDetails, text="Most Recent Order").grid(row=9, column=0, padx=10, pady=10)

        # Use tk.Entry for readonly fields
        tk.Entry(customerDetails, textvariable=StringVar(value=totalOrders), state='readonly').grid(row=7, column=1, padx=10, pady=10)
        tk.Entry(customerDetails, textvariable=StringVar(value=totalHouses), state='readonly').grid(row=8, column=1, padx=10, pady=10)
        tk.Entry(customerDetails, textvariable=StringVar(value=mostRecentOrder), state='readonly').grid(row=9, column=1, padx=10, pady=10)

        # Past 3 Orders
        ttk.Label(customerDetails, text="Past 3 Orders").grid(row=0, column=2, padx=10, pady=10)

        # For each order, use tk.Entry for readonly fields
        for i, order in enumerate(orderResult):
            orderPostCode, orderDate, orderStatus = order
            ttk.Label(customerDetails, text="Order PostCode").grid(row=1 + i * 3, column=2, padx=10, pady=10)
            tk.Entry(customerDetails, textvariable=StringVar(value=orderPostCode), state='readonly').grid(row=1 + i * 3, column=3, padx=10, pady=10)
            
            ttk.Label(customerDetails, text="Order Date").grid(row=2 + i * 3, column=2, padx=10, pady=10)
            tk.Entry(customerDetails, textvariable=StringVar(value=orderDate), state='readonly').grid(row=2 + i * 3, column=3, padx=10, pady=10)
            
            ttk.Label(customerDetails, text="Order Status").grid(row=3 + i * 3, column=2, padx=10, pady=10)
            tk.Entry(customerDetails, textvariable=StringVar(value=orderStatus), state='readonly').grid(row=3 + i * 3, column=3, padx=10, pady=10)

        # Functions
        ttk.Button(customerDetails, text="Log Out", command=master.destroy).grid(row=0, column=4, padx=10, pady=10)
        self.editButton = ttk.Button(customerDetails, text="Change Account Details", command=lambda: self.changeDetails())
        self.editButton.grid(row=2, column=4, padx=10, pady=10)
        ttk.Button(customerDetails, text="Complete Order Form", command=lambda: self.customerOrderForm()).grid(row=4, column=4, padx=10, pady=10)
        ttk.Button(customerDetails, text="View All Orders", command=lambda: self.viewAllOrders()).grid(row=6, column=4, padx=10, pady=10)
        ttk.Button(customerDetails, text="Copy Authentication Token", command=lambda: copyAuthKey()).grid(row=7, column=4, padx=10, pady=10)
        ttk.Button(customerDetails, text="Reset Authentication Token", command=lambda: resetAuthKey()).grid(row=8, column=4, padx=10, pady=10)
        ttk.Button(customerDetails, text="View Pending Invoices", command=lambda: self.pendingInvoices()).grid(row=9, column=4, padx=10, pady=10)

    def changeDetails(self):
        if self.editButton["text"] == "Change Account Details":
            # Unlock fields
            for field in self.entryFields.values():
                field.config(state="normal")

            self.editButton.config(text="Submit Changes")
        else:
            # Process data and lock fields again
            updatedData = {label: field.get() for label, field in self.entryFields.items()}

            messagebox.showinfo("Updated Data", f"New Values:\n{updatedData}")

            customerData = loadJson(f"{dbPath}/customer.json")
            indexData = loadJson(f"{dbPath}/_index.json")
            customerIndex = indexData.get("customerIndex", {}).get(str(userId))

            if customerIndex is not None:
                customerRecord = customerData[customerIndex]
                for key, value in updatedData.items():
                    customerRecord[key] = value
                writeJson(f"{dbPath}/customer.json", customerData)
                messagebox.showinfo("Successful Operation", "Record updated successfully.")
            else:
                messagebox.showerror("Database Error", f"Customer with ID {userId} not found")

            for field in self.entryFields.values():
                field.config(state="readonly")

            self.editButton.config(text="Change Account Details")

    def customerOrderForm(self):
        self.customerOrderForm = tk.Toplevel(self)
        self.customerOrderForm.title("Order Form")
        self.customerOrderForm.geometry("400x700")
        tk.Label(self.customerOrderForm, text="Customer Order Form", font=("San Francisco", 24)).pack(pady=10)

        orderForm = tk.Frame(self.customerOrderForm)
        orderForm.pack(pady=20)
        # Define order rows
        orderFields = ["orderDueDate", "orderPostCode", "orderHousesNum"]
        # Create dictionary for Text fields
        self.orderRow = {}
        # Create form by itereating betweeen each row name
        for row in orderFields:
            if row[0] == "o":
                # If the row name starts with "o", remove the first 5 letters, if not, leave it
                tk.Label(orderForm, text=row[5:]).grid(column=0, padx=15, pady=15)
            else:
                tk.Label(orderForm, text=row).grid(column=0, padx=15, pady=15)
            orderRow = tk.Text(orderForm, height = 1, width = 25)
            orderRow.grid(column=1)
            self.orderRow[row] = orderRow
        ttk.Button(orderForm, text="Submit", command=lambda: self.submit(orderFields)).grid(padx=10, pady=5)
        ttk.Button(orderForm, text="Close", command=lambda: self.customerOrderForm.destroy()).grid(padx=10, pady=5)

    def submit(self, orderFields):
        # Get order details from the text fields
        result = [str(orderRow.get("1.0", "end-1c")) for col, orderRow in self.orderRow.items()]

        submit(self, orderFields, result)

        self.customerOrderForm.destroy()
        del self.customerOrderForm
         
    def pendingInvoices(self):
        self.customerPendingInvoices = tk.Toplevel(self)
        self.customerPendingInvoices.title("Order Form")
        self.customerPendingInvoices.geometry("400x700")

        self.columnsToDisplay = ["orderID", "invoiceAmount", "orderStatus"]
        
        tk.Label(self.customerPendingInvoices, text="Pending Invoices", font=("San Francisco", 24)).pack(pady=10)

        # Treeview widget for displaying data
        self.tree = ttk.Treeview(self.customerPendingInvoices, columns=self.columnsToDisplay, show="headings")
        self.tree.pack(fill="both", expand=True)

        # Load data from JSON
        orders = loadJson(f"{dbPath}/order.json")

        # Set up Treeview headings
        for col in self.columnsToDisplay:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="w")

        # Insert data into Treeview
        for order in orders:
            values = [order.get(col, "N/A") for col in self.columnsToDisplay]
            if order["orderStatus"] == "0":
                self.tree.insert("", "end", values=values)

        pendingInvoices = tk.Frame(self.customerPendingInvoices)
        pendingInvoices.pack(pady=10)

        ttk.Button(pendingInvoices, text="Close", command=lambda: self.customerPendingInvoices.destroy()).grid(row=0, column=5, padx=10, pady=5)

class distributorFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        tk.Label(self, text="Distributor Home Page", font=("San Francisco", 24)).pack(pady=10)

        try:
            # Load JSON data
            orderData = loadJson(f"{dbPath}/order.json")
            distributorData = loadJson(f"{dbPath}/distributor.json")
            indexData = loadJson(f"{dbPath}/_index.json")

            # Get distributor details
            distributorIndex = indexData.get("distributorIndex", {}).get(str(userId))
            if distributorIndex is not None:
                distributorRecord = distributorData[distributorIndex]
                distributorLName = distributorRecord.get("distributorLName", "N/A")
                distributorPhone = distributorRecord.get("distributorPhone", "N/A")
                distributorEmail = distributorRecord.get("distributorEmail", "N/A")
                distributorPay = distributorRecord.get("distributorPay", 0)
                distributorRate = distributorRecord.get("distributorRate", 0)
            else:
                messagebox.showerror("Database Error", f"Distributor with ID {userId} not found")

            # Filter orders for this distributor
            distributorOrders = [order for order in orderData if order["distributorID"] == str(userId)]

            # Compute general stats
            totalOrders = len(distributorOrders)
            totalHouses = sum(int(order.get("orderHousesNum", 0)) for order in distributorOrders)

            # Get the most recent 3 orders (sorted by date)
            recentOrders = sorted(distributorOrders, key=lambda x: x["orderDate"])[:3]
            orderResult = [(order["orderPostCode"], order["orderHousesNum"], order["orderDueDate"]) for order in recentOrders]

            if not recentOrders:
                messagebox.showinfo("Recent Order Error", "No recent orders found.")

            # Get current order details (orders with orderStatus <= 7)
            currentOrders = [
                order for order in distributorOrders if int(order.get("orderStatus", 999)) <= 6
            ]

            if currentOrders:
                # Extract details of the most recent current order
                currentOrder = sorted(currentOrders, key=lambda x: x["orderDate"])[0]
                orderPostCode = currentOrder["orderPostCode"]
                orderHousesNum = currentOrder["orderHousesNum"]
                orderDueDate = currentOrder["orderDueDate"]
                orderStatus = currentOrder["orderStatus"]
            else:
                orderPostCode = None  # No active orders

                recentOrders = orderResult 

        except Exception as e:
            messagebox.showerror("Database Error", str(e))

        # Grid Layout
        distributorDetails = tk.Frame(self)
        distributorDetails.pack(pady=20)

        # Account Details
        ttk.Label(distributorDetails, text="Account Details").grid(row=5, column=4)
        ttk.Label(distributorDetails, text="Name").grid(row=6, column=4, padx=10, pady=10)
        ttk.Label(distributorDetails, text="Phone Number").grid(row=7, column=4, padx=10, pady=10)
        ttk.Label(distributorDetails, text="Email").grid(row=8, column=4, padx=10, pady=10)

        # Use tk.Entry for readonly fields
        distributorNameField = tk.Entry(distributorDetails, textvariable=tk.StringVar(value=distributorLName), state='readonly')
        distributorNameField.grid(row=6, column=5, padx=10, pady=10)
        distributorPhoneField = tk.Entry(distributorDetails, textvariable=StringVar(value=distributorPhone), state='readonly')
        distributorPhoneField.grid(row=7, column=5, padx=10, pady=10)
        distributorEmailField = tk.Entry(distributorDetails, textvariable=StringVar(value=distributorEmail), state='readonly')
        distributorEmailField.grid(row=8, column=5, padx=10, pady=10)

        self.entryFields = {
            "distributorLName": distributorNameField,
            "distributorEmail": distributorEmailField,
            "distributorPhone": distributorPhoneField
        }
        # Current Order Details
        if orderPostCode == None:
            ttk.Button(distributorDetails, text="View Available Orders", command = lambda: self.viewAvailableOrders()).grid(row=0, column=0, padx=10, pady=10, columnspan=2, rowspan=5, sticky=NSEW)        
        else:
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

        imagePath = f"./Maps/{orderPostCode}.png"

        image = Image.open(imagePath)
        smallerImage = image.resize((300, 300))
        tkImage = ImageTk.PhotoImage(smallerImage)

        label = tk.Label(distributorDetails, image=tkImage)
        label.grid(row=0, column=5, padx=10, pady=5, rowspan=5, columnspan=2)

        # Statistics Fields
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

        # Functions
        ttk.Button(distributorDetails, text="Log Out", command=master.destroy).grid(row=0, column=4, padx=10, pady=10)
        self.editButton = ttk.Button(distributorDetails, text="Change Account Details", command=lambda: self.changeAccountDetails())
        self.editButton.grid(row=1, column=4, padx=10, pady=10)
        ttk.Button(distributorDetails, text="View all Orders", command=lambda: self.viewAllOrders()).grid(row=2, column=4, padx=10, pady=10)
        ttk.Button(distributorDetails, text="Copy Authentication Token", command=lambda: copyAuthKey()).grid(row=3, column=4, padx=10, pady=10)
        ttk.Button(distributorDetails, text="Reset Authentication Token", command=lambda: resetAuthKey()).grid(row=4, column=4, padx=10, pady=10)
    # Function Buttons
    def viewAvailableOrders(self):
        self.clearFrame()
        tk.Label(self, text="Available Orders", font=("San Francisco", 24)).pack(pady=10)
        # Treeview widget for displaying data
        self.tree = ttk.Treeview(self, columns=["orderID", "orderPostCode", "orderHousesNum", "orderDueDate", "orderPayment"], show="headings")
        self.tree.pack(fill="both", expand=True)
        # Load data from JSON
        orders = loadJson(f"{dbPath}/order.json")
        # Set up Treeview headings
        for col in ["orderID", "orderPostCode", "orderHousesNum", "orderDueDate"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="w")

        distributorData = loadJson(f"{dbPath}/distributor.json")
        indexData = loadJson(f"{dbPath}/_index.json")
        distributorIndex = indexData.get("distributorIndex", {}).get(str(userId))
        distributorRate = distributorData[distributorIndex].get("distributorRate", 5)
        # Insert data into Treeview
        for order in orders:
            if order["orderStatus"] == "2":
                values = [order.get(col, "N/A") for col in ["orderID", "orderPostCode", "orderHousesNum", "orderDueDate"]]
                orderPayment = int(order["orderHousesNum"]) * int(distributorRate) / 20
                values.append(orderPayment)
                self.tree.insert("", "end", values=values)
        buttonsFrame = tk.Frame(self)
        buttonsFrame.pack(pady=10)

        self.tree.bind("<Button-3>", self.rightClick)

        ttk.Button(buttonsFrame, text="Close", command=lambda: self.clearFrame()).grid(row=0, column=5, padx=10, pady=5)

    def rightClick(self, event):
        # Create a context menu
        contextMenu = tk.Menu(self.master, tearoff=0)
    
        # Add a command to the menu
        contextMenu.add_command(label="Accept Order", command=lambda: self.acceptOrder(self.getSelectedID(event)))

        # Display the context menu at the mouse position
        contextMenu.post(event.x_root, event.y_root)

    def getSelectedID(self, event):
        row = self.tree.identify("item", event.x, event.y)
        if row:
            primaryKey = self.tree.item(row)["values"][0]
            return str(primaryKey)
        else:
            messagebox.showerror("No row selected", "Please select a row.")

    def acceptOrder(self, orderID):
        try:
            path = f"{dbPath}/order.json"
            # Load JSON data
            orderData = loadJson(path)
            # Load index
            indexData = loadJson(f"{dbPath}/_index.json")
            # Get the index dictionary for the table
            orderIndex = indexData.get("orderIndex", {})
            # Find record's position using the index
            orderPosition = orderIndex.get(orderID)
            if orderPosition is not None:
                if orderData[orderPosition]["orderStatus"] == "1":
                    # Mark the record as Accepted
                    orderData[orderPosition]["orderStatus"] = "2"
                    # Save updated JSON data
                    writeJson(path, orderData)
                    #Refresh UI
                    self.populateList()
                    messagebox.showinfo("Successful Operation", "Order accepted successfully.")
                else:
                    messagebox.showerror("Order Error", "Order is already accepted.")
            else:
                messagebox.showerror("Database Error", f"Order with ID {orderID} not found in index")
        except Exception as e:
            messagebox.showerror("Database Error", str(e))

    def changeAccountDetails(self):
        if self.editButton["text"] == "Change Account Details":
            # Unlock fields
            for field in self.entryFields.values():
                field.config(state="normal")

            self.editButton.config(text="Submit Changes")
        else:
            # Process data and lock fields again
            updatedData = {label: field.get() for label, field in self.entryFields.items()}

            messagebox.showinfo("Updated Data", f"New Values:\n{updatedData}")

            distributorData = loadJson(f"{dbPath}/distributor.json")
            indexData = loadJson(f"{dbPath}/_index.json")
            distributorIndex = indexData.get("distributorIndex", {}).get(str(userId))

            if distributorIndex is not None:
                distributorRecord = distributorData[distributorIndex]
                for key, value in updatedData.items():
                    distributorRecord[key] = value
                writeJson(f"{dbPath}/distributor.json", distributorData)
                messagebox.showinfo("Successful Operation", "Record updated successfully.")
            else:
                messagebox.showerror("Database Error", f"Distributor with ID {userId} not found")

            for field in self.entryFields.values():
                field.config(state="readonly")

            self.editButton.config(text="Change Account Details")


# Main Running Loop

if __name__ == "__main__":
    app = Application()
    app.mainloop()