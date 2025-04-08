# Import libraries
from turtle import update
import pyotp
import time
import tkinter as tk
from tkinter import NSEW, messagebox, StringVar
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
import ttkbootstrap as ttk
from ttkbootstrap.constants import *


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

        indexData[table + "Index"] = {str(entry.get(table + "Id")): i for i, entry in enumerate(tableData) if table + "Id" in entry}

    writeJson(indexFile, indexData)
    print("Index rebuilt successfully.")

def submit(self, orderFields, result):
    # Load JSON data
    orderData = loadJson(f"{dbPath}/order.json")
    indexData = loadJson(f"{dbPath}/_index.json")

    # Generate necessary fields
    date = str(time.strftime("%d%m%Y"))
    orderStatus = "Recieved, Awaiting Payment"

    # Generate new unique Order Id
    orderId = max([record.get("orderId", 0) for record in orderData], default=0) + 1

    # Validation


    # Ensure all fields are filled

    for field in orderFields:
        if not result[orderFields.index(field)]:
            messagebox.showerror("Missing Fields", f"Please fill in all fields. Missing: {field}")
            return

    # Ensure fields are filled with acceptable values
    print(result)

    # Check if the due date is in the future

    # Check if the date is in the correct format
    try:
        date1 = time.strptime((result[0]), "%d%m%Y")
    except ValueError:
        messagebox.showerror("Invalid Date", "Please enter a valid 8-digit date in the format DDMMYYYY.")
        return

    date2 = time.strptime(date, "%d%m%Y")

    if date1 < date2:
        messagebox.showerror("Invalid Date", "Please enter a date in the future.")
        return

    # Check if the customerId is correct

    for record in loadJson(f"{dbPath}/customer.json"):
        if result[2] == str(record["customerId"]):
            customerRecord = record
            break
    else:
        messagebox.showerror("Invalid Customer", "Please enter a valid customer ID.")
        return

    # Check if the postcode exists and generate map
    try:
        HousesNum = getHouseholdNetwork(result[1])
    except ValueError:
        messagebox.showerror("Invalid Postcode", "Please enter a valid postcode.")
        return

    # Create dyanimc variables for the order

    # Calculate cost based on customer rate

    customerData = loadJson(f"{dbPath}/customer.json")
    customerIndex = indexData.get("customerIndex", {}).get(result[2])
    customerRecord = customerData[customerIndex]
    cost = float(customerRecord.get("customerRate", 0)) * HousesNum / 10

    # Fill in the new order details
    newOrder = {
        "orderId": orderId,
        "orderStatus": str(orderStatus),
        "orderDate": str(date),
        "invoiceAmount": str(cost),
        "orderMap": f"./Maps/{result[1]}.png",
        "orderHousesNum": str(HousesNum),
        "customerId": str(result[2]),
        "distributor": None
    }

    # Add dynamic fields 
    for field, value in zip(orderFields, result):
        newOrder[field] = value

    # Append order to the database
    orderData.append(newOrder)
    writeJson(f"{dbPath}/order.json", orderData)

    # Update the index and save it
    buildIndex()

    # Show confirmation messages
    messagebox.showinfo("Successful Operation", "Record created successfully.")
    messagebox.showinfo("Order Cost", f"The cost for this order will be \u00A3 {cost}")

def backToHome(self):
    clearFrame(self)
    self.initHomePage()

def clearFrame(self):
    for widget in self.winfo_children():
        widget.destroy()

# Functions - Authentication

def copyAuthKey(self):
    # Copies the authentication key for the current user
    authKey = fetchAuthById(userId)
    app.clipboard_clear()
    app.clipboard_append(authKey)
    app.update()  # now it stays on the clipboard after the window is closed
    messagebox.showinfo("Copy Authentication Token", "Authentication key copied to clipboard.")

    backToHome(self)

def resetAuthKey(self):
    # Resets the authentication key for the current user
    authKey = pyotp.random_base32()
    tableFile = f"{dbPath}/{table}.json"
    indexData = loadJson(indexFile)

    if table + "Index" not in indexData or str(userId) not in indexData[table + "Index"]:
        print(f"Error: Record Id {userId} not found in {table}.")

    recordPosition = indexData[table + "Index"][str(userId)]
    tableData = loadJson(tableFile)

    tableData[recordPosition]["authenticationKey"] = authKey
    writeJson(tableFile, tableData)

    messagebox.showinfo("Reset Authentication Token", f"New authentication key generated: {authKey}")
    copyAuthKey(self)

def fetchAuthById(enteredId):
    # Fetches the authentication key for a given user Id
    indexData = loadJson(indexFile)
    tableFile = f"{dbPath}/{table}.json"

    recordPosition = indexData[table + "Index"][str(enteredId)]
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

        # Set up ttk theme and styling
        style = ttk.Style()
        style.theme_use("vapor")

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
        tk.Label(Login, text="Account Id", borderwidth=2, padx=10, pady=10).grid(row=0, column=0)
        enteredId = tk.Text(Login, height=1, width=5, borderwidth=2)
        enteredId.grid(row=0, column=1)
        tk.Label(Login, text="6 Digit Authentication Code", borderwidth=2, padx=10, pady=10).grid(row=1, column=0)
        userCode = tk.Text(Login, height=1, width=6, wrap="word", borderwidth=2)
        userCode.grid(row=1, column=1)
        ttk.Button(Login, text="Login", command=lambda: self.authUser(enteredId, userCode), bootstyle="Success").grid(row=3, column=0, padx=10, pady=10)

    # Function to Authenticate User

    def authUser(self, enteredId, userCode):        
        global userId
        global table
        enteredId = enteredId.get("1.0", tk.END).strip()
        userCode = userCode.get("1.0", tk.END).strip()
        Id = [[2, 4, 5],["admin", "distributor", "customer"]]
        try:
            arrayPos = Id[0].index(len(enteredId))  # Look for the length in Id[1]
        except ValueError:
            messagebox.showerror("User Error","Not Logged In, Incorrect Id")
        userId = enteredId
        table = Id[1][arrayPos]
        correctKey = generateAuthKey(fetchAuthById(enteredId))
        print(correctKey)
        if userCode in correctKey:
            self.master.switchFrame(f"{table} + Frame")
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
        ttk.Button(buttonsFrame, text="View Orders", command=lambda: self.switchToViewPage("order"), bootstyle="primary").grid(row=0, column=0, padx=10, pady=10)
        ttk.Button(buttonsFrame, text="View Customers", command=lambda: self.switchToViewPage("customer"), bootstyle="primary").grid(row=1, column=0, padx=10, pady=10)
        ttk.Button(buttonsFrame, text="View Distributors", command=lambda: self.switchToViewPage("distributor"), bootstyle="primary").grid(row=2, column=0, padx=10, pady=10)
        ttk.Button(buttonsFrame, text="Log Out", command=self.master.destroy, bootstyle="danger").grid(row=0, column=1, padx=10, pady=10)
        ttk.Button(buttonsFrame, text="Customer Order Form", command=self.customerOrderForm, bootstyle="secondary").grid(row=1, column=1, padx=10, pady=10)
        ttk.Button(buttonsFrame, text="Distributor Pay List", command=self.distributorPayList, bootstyle="primary").grid(row=2, column=1, padx=10, pady=10)

    def switchToViewPage(self, tableName):
        self.tableName = tableName
        if tableName == "order":
            self.columnsToDisplay = ["orderId", 
                                     "orderStatus", 
                                     "orderDate", 
                                     "invoiceAmount",
                                     "orderMap",
                                     "orderDueDate",
                                     "orderPostCode",
                                     "distributorId",
                                     "customerId"
                                     ]
        elif tableName == "customer":
            self.columnsToDisplay = ["customerId", 
                                     "customerEmail",
                                     "customerName",
                                     "customerNotes",
                                     "customerPhone",
                                     "customerRate"
                                     ]
        else:
            self.columnsToDisplay = ["distributorId", 
                                     "distributorFName", 
                                     "distributorLName", 
                                     "distributorPay",
                                     "distributorEmail",
                                     "distributorPhone",
                                     "distributorCurrentOrder",
                                     "distributorRate"
                                     ]
        clearFrame(self)
        self.viewPage()

    def viewPage(self):
        tk.Label(self, text=f"View {self.tableName.capitalize()}", font=("San Francisco", 20)).pack(pady=10)

        # Table frame
        tableFrame = tk.Frame(self)
        tableFrame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Treeview widget for displaying data
        self.tree = ttk.Treeview(tableFrame, columns=self.columnsToDisplay, show="headings")
        for col in self.columnsToDisplay:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="w", width=100, stretch=True)
       
        
        self.tree.pack(fill="both", expand=True)

        # Bind intialisation to auto-resize columns
        def resizeColumns(event):
            totalWidth = event.width
            nCols = len(self.columnsToDisplay)
            if nCols > 0:
                colWidth = totalWidth // nCols
                for col in self.columnsToDisplay:
                    self.tree.column(col, width=colWidth)
        self.tree.bind("<Configure>", resizeColumns)

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
        ttk.Button(filterFrame, text="Apply Filter", command=self.applyFilter, bootstyle="info").grid(row=0, column=4, padx=10, pady=5)
        ttk.Button(filterFrame, text="Back to Home", command=lambda: backToHome(self), bootstyle="danger").grid(row=0, column=5, padx=10, pady=5)

        if not self.tableName == "order":
            ttk.Button(self, text="Add Record", command=self.addRecord, bootstyle="success").pack(pady=10)

    def rightClick(self, event):
        # Create a context menu
        contextMenu = tk.Menu(self.master, tearoff=0)
    
        # Add a command to the menu
        contextMenu.add_command(label="Remove Record", command=lambda: self.removeRecord(self.getSelectedId(event)))
        if self.tableName == "order":
            contextMenu.add_command(label="Mark as Paid", command=lambda: self.markAsPaid(self.getSelectedId(event)))
    
        # Display the context menu at the mouse position
        contextMenu.post(event.x_root, event.y_root)

    def getSelectedId(self, event):
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
                messagebox.showerror("Database Error", f"Record with Id {record} not found in index")
        except Exception as e:
            messagebox.showerror("Database Error", str(e))

    def markAsPaid(self, record):
        try:
            # Load JSON data
            orderData = loadJson(f"{dbPath}/order.json")
            indexData = loadJson(f"{dbPath}/_index.json")
            orderIndex = indexData.get("orderIndex", {})
            # Find record's position using the index
            recordPosition = orderIndex.get(record)
            if recordPosition is not None:
                if orderData[recordPosition]["orderStatus"] == "Recieved, Awaiting Payment":
                    # Mark the record as paid
                    orderData[recordPosition]["orderStatus"] = "Paid, to be Devlivered"
                  
                    messagebox.showinfo("Successful Operation", "Record marked as paid successfully")

                    # Attempt to assign distributor to paid order
                    distributorData = loadJson(f"{dbPath}/distributor.json")


                    for distributor in distributorData:
                        if distributor["distributorCurrentOrder"] == None:
                            orderData[recordPosition]["distributorId"] = distributor["distributorId"]
                            orderData[recordPosition]["orderStatus"] = "Out for Delivery"
                            
                            distributor["distributorCurrentOrder"] = orderData[recordPosition]["orderId"]
                            
                            messagebox.showinfo("Distributor Assinged", "A distributor has been assigned, the order should be delivered soon")
                            
                            break
                    else:
                        messagebox.showinfo("No Distributor Available", "No available distributors at the moment, order will be placed in queue.")
                        orderData[recordPosition]["distributorId"] = None
                    
                    # Save updated JSON data
                    writeJson(f"{dbPath}/order.json", orderData)
                    writeJson(f"{dbPath}/distributor.json", distributorData)

                    messagebox.showinfo("Successful Operation", "Database Updated")
                    # Rebuild index to maintain consistency
                    buildIndex()
                    # Refresh UI
                    self.populateList()
                else:
                    messagebox.showerror("Database Error", "Record is already marked as paid.")
            else:
                messagebox.showerror("Database Error", f"Record with Id {record} not found in index")
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
        ttk.Button(self.addRecord, text="Submit", command=self.submit, bootstyle="success").grid()

    def submit(self):
        result = []
        # Collect values from all dynamic text widgets
        for col, textWidget in self.newRecord.items():
            text = str(textWidget.get("1.0", "end-1c")).strip()
            result.append(text)

        # Distributor Validation
        if self.tableName == "distributor":
            # Load input values
            distributorId, distributorFName, distributorLName, distributorEmail, distributorPhone, distributorPay = result
            
            if not distributorFName or not distributorLName:
                messagebox.showerror("Validation Error", "Distributor first and last names cannot be empty.")
                return
            if "@" not in distributorEmail:
                messagebox.showerror("Validation Error", "Please enter a valid distributor email.")
                return
            if not distributorPhone.isdigit():
                messagebox.showerror("Validation Error", "Distributor phone number must be numeric.")
                return
            distributorPay = 0

            result = [distributorId, distributorFName, distributorLName, distributorEmail, distributorPhone, distributorPay]

        elif self.tableName == "customer":
            # Load input values
            customerId, customerName, customerEmail, customerPhone, customerNotes, customerRate = result
            
            if not customerName:
                messagebox.showerror("Validation Error", "Customer name cannot be empty.")
                return
            
            if "@" not in customerEmail:
                messagebox.showerror("Validation Error", "Please enter a valid customer email.")
                return
            
            if not customerPhone.isdigit():
                messagebox.showerror("Validation Error", "Customer phone number must be numeric.")
                return

            if not customerRate:
                messagebox.showinfo("Default Rate", "Customer Rate will be defaulted.")
                customerRate = "5"
            else:
                if not customerRate.isdigit():
                    messagebox.showerror("Validation Error", "Customer rate must be numeric.")
                    return

            result = [customerId, customerName, customerEmail, customerPhone, customerNotes, customerRate]

        elif self.tableName == "admin":
            adminId, adminEmail, adminPhone = result
            if "@" not in adminEmail:
                messagebox.showerror("Validation Error", "Please enter a valid admin email.")
                return


        # Create Required Fields

        # Generate auth key
        authKey = pyotp.random_base32()
        messagebox.showinfo("Authentication Key", f"This account's authentication key used to log in is {authKey}, we recommend the user to reset this for security reasons!")

        # Build the record data dictionary
        recordData = {"authenticationKey": authKey}
        recordData.update({col: value for col, value in zip(self.columnsToDisplay, result)})

        path = f"{dbPath}/{self.tableName}.json"
        tableData = loadJson(path)

        # Determine a unique Id
        if not result[0]:
            recordData[self.tableName + "Id"] = max([record.get(self.tableName + "Id", 0) for record in tableData], default=0) + 1
        else:
            recordData[self.tableName + "Id"] = result[0]

        # Append new record and update JSON storage
        tableData.append(recordData)
        writeJson(path, tableData)
        buildIndex()

        messagebox.showinfo("Successful Operation", "Record created successfully.")
        self.addRecord.destroy()
        self.populateList()

    def customerOrderForm(self):
        clearFrame(self)
        tk.Label(self, text="Customer Order Form", font=("San Francisco", 24)).pack(pady=10)

        orderForm = tk.Frame(self)
        orderForm.pack(pady=20)
        # Define order rows
        orderFields = ["orderDueDate", "orderPostCode", "customerId"]
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
        ttk.Button(orderForm, text="Submit", command=lambda: self.orderSubmit(orderFields), bootstyle="success").grid(padx=10, pady=5)
        ttk.Button(orderForm, text="Back to Home", command=lambda: backToHome(self), bootstyle="danger").grid(padx=10, pady=5)

    def orderSubmit(self, orderFields):
        # Get order details from the text fields
        result = [str(orderRow.get("1.0", "end-1c")) for col, orderRow in self.orderRow.items()]
        print(result)
        submit(self, orderFields, result)

        # Switch frame after submission
        backToHome(self)

    def distributorPayList(self):
        clearFrame(self)
        tk.Label(self, text="Distributor Pay List", font=("San Francisco", 24)).pack(pady=10)

        # Treeview widget for displaying data
        self.tree = ttk.Treeview(self, columns=["distributorId", "distributorFName", "distributorLName", "distributorPay"], show="headings")
        self.tree.pack(fill="both", expand=True)

        # Load data from JSON
        distributors = loadJson(f"{dbPath}/distributor.json")

        # Set up Treeview headings
        for col in ["distributorId", "distributorFName", "distributorLName", "distributorPay"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="w")

        # Insert data into Treeview
        for distributor in distributors:
            values = [distributor.get(col, "N/A") for col in ["distributorId", "distributorFName", "distributorLName", "distributorPay"]]
            self.tree.insert("", "end", values=values)

        buttonsFrame = tk.Frame(self)
        buttonsFrame.pack(pady=10)

        ttk.Button(buttonsFrame, text="Reset Payments", command=lambda: self.resetPayments(), bootstyle="primary").grid(row=0, column=4, padx=10, pady=5)
        ttk.Button(buttonsFrame, text="Back to Home", command=lambda: backToHome(self), bootstyle="danger").grid(row=0, column=5, padx=10, pady=5)

    def resetPayments(self):
        distributors = loadJson(f"{dbPath}/distributor.json")

        for distributor in distributors:
            distributor["distributorPay"] = 0

        writeJson(f"{dbPath}/distributor.json", distributors)
        messagebox.showinfo("Payment Reset", "All distributor payments have been reset to \u00A3 0.")

class customerFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master

        self.initHomePage()

    def initHomePage(self):
        tk.Label(self, text="Customer Home Page", font=("San Francisco", 24)).pack(pady=10)

        # Grid layout
        customerDetails = tk.Frame(self)
        customerDetails.pack(pady=20)
        try:
            # Fetch JSON data
            customerData = loadJson(f"{dbPath}/customer.json")
            orderData = loadJson(f"{dbPath}/order.json")
            indexData = loadJson(f"{dbPath}/_index.json")

            # Get customer details
            customerIndex = indexData.get("customerIndex", {}).get(str(userId))
            if customerIndex is not None:
                customerRecord = customerData[customerIndex]
                customerEmail = customerRecord.get("customerEmail", "N/A")
                customerName = customerRecord.get("customerName", "N/A")
                customerPhone = customerRecord.get("customerPhone", "N/A")
            else:
                messagebox.showerror("Database Error", f"Customer with Id {userId} not found")

            # Get order statistics
            customerOrders = [order for order in orderData if order["customerId"] == str(userId)]
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

        # Use ttk.Entry for readonly fields
        customerNameVar = tk.StringVar(value=customerName)
        customerPhoneVar = tk.StringVar(value=customerPhone)
        customerEmailVar = tk.StringVar(value=customerEmail)

        customerNameField = ttk.Entry(customerDetails, textvariable=customerNameVar, state='readonly', style="TEntry")
        customerNameField.grid(row=1, column=1, padx=10, pady=10)
        customerPhoneField = ttk.Entry(customerDetails, textvariable=customerPhoneVar, state='readonly', style="TEntry")
        customerPhoneField.grid(row=2, column=1, padx=10, pady=10)
        customerEmailField = ttk.Entry(customerDetails, textvariable=customerEmailVar, state='readonly', style="TEntry")
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

        # Use ttk.Entry for readonly fields
        totalOrdersVar = tk.StringVar(value=str(totalOrders))
        totalHousesVar = tk.StringVar(value=str(totalHouses))
        mostRecentOrderVar = tk.StringVar(value=str(mostRecentOrder))

        ttk.Entry(customerDetails, textvariable=totalOrdersVar, state='readonly', style="TEntry").grid(row=7, column=1, padx=10, pady=10)
        ttk.Entry(customerDetails, textvariable=totalHousesVar, state='readonly', style="TEntry").grid(row=8, column=1, padx=10, pady=10)
        ttk.Entry(customerDetails, textvariable=mostRecentOrderVar, state='readonly', style="TEntry").grid(row=9, column=1, padx=10, pady=10)


        # Past 3 Orders
        ttk.Label(customerDetails, text="Past 3 Orders").grid(row=0, column=2, padx=10, pady=10)

        # For each order, use ttk.Entry for readonly fields
        orderPostCodeVars = []
        orderDateVars = []
        orderStatusVars = []

        for i, order in enumerate(orderResult):
            orderPostCode, orderDate, orderStatus = order
            orderPostCodeVar = tk.StringVar(value=orderPostCode)
            orderDateVar = tk.StringVar(value=orderDate)
            orderStatusVar = tk.StringVar(value=orderStatus)
            orderPostCodeVars.append(orderPostCodeVar)
            orderDateVars.append(orderDateVar)
            orderStatusVars.append(orderStatusVar)
    
            ttk.Label(customerDetails, text="Order PostCode").grid(row=1 + i * 3, column=2, padx=10, pady=10)
            ttk.Entry(customerDetails, textvariable=orderPostCodeVar, state='readonly').grid(row=1 + i * 3, column=3, padx=10, pady=10)
    
            ttk.Label(customerDetails, text="Order Date").grid(row=2 + i * 3, column=2, padx=10, pady=10)
            ttk.Entry(customerDetails, textvariable=orderDateVar, state='readonly').grid(row=2 + i * 3, column=3, padx=10, pady=10)
    
            ttk.Label(customerDetails, text="Order Status").grid(row=3 + i * 3, column=2, padx=10, pady=10)
            ttk.Entry(customerDetails, textvariable=orderStatusVar, state='readonly').grid(row=3 + i * 3, column=3, padx=10, pady=10)

        # Functions
        ttk.Button(customerDetails, text="Log Out", command=self.master.destroy, bootstyle="danger").grid(row=0, column=4, padx=10, pady=10)
        self.editButton = ttk.Button(customerDetails, text="Change Account Details", command=lambda: self.changeDetails(), bootstyle="info")
        self.editButton.grid(row=2, column=4, padx=10, pady=10)
        ttk.Button(customerDetails, text="Complete Order Form", command=lambda: self.customerOrderForm(), bootstyle="primary").grid(row=4, column=4, padx=10, pady=10)
        ttk.Button(customerDetails, text="Copy Authentication Token", command=lambda: copyAuthKey(self), bootstyle="secondary").grid(row=5, column=4, padx=10, pady=10)
        ttk.Button(customerDetails, text="Reset Authentication Token", command=lambda: resetAuthKey(self), bootstyle="secondary").grid(row=6, column=4, padx=10, pady=10)
        ttk.Button(customerDetails, text="View Pending Invoices", command=lambda: self.pendingInvoices(), bootstyle="warning").grid(row=7, column=4, padx=10, pady=10)

    def changeDetails(self):
        if self.editButton["text"] == "Change Account Details":
            # Unlock fields
            for field in self.entryFields.values():
                field.config(state="normal")

            self.editButton.config(text="Submit Changes")
        else:
            # Process data and lock fields again
            updatedData = {label: field.get() for label, field in self.entryFields.items()}

            # Validate input
            if not updatedData["customerName"]:
                messagebox.showerror("Validation Error", "Customer name cannot be empty.")
                return
            if "@" not in updatedData["customerEmail"]:
                messagebox.showerror("Validation Error", "Please enter a valid customer email.")
                return
            if not updatedData["customerPhone"].isdigit() or not len(updatedData["customerPhone"]) == 11 or not str(updatedData["customerPhone"][:2]) == "07":
                messagebox.showerror("Validation Error", "Customer phone number must be numeric in the format of 07XXXXXXXXX")
                return

            customerData = loadJson(f"{dbPath}/customer.json")
            indexData = loadJson(f"{dbPath}/_index.json")
            customerIndex = indexData.get("customerIndex", {}).get(str(userId))

            if customerIndex is not None:
                customerRecord = customerData[customerIndex]
                for key, value in updatedData.items():
                    customerRecord[key] = value
                writeJson(f"{dbPath}/customer.json", customerData)
                messagebox.showinfo("Updated Data", "Values updated successfully.")
            else:
                messagebox.showerror("Database Error", f"Customer with Id {userId} not found")

            for field in self.entryFields.values():
                field.config(state="readonly")

            self.editButton.config(text="Change Account Details")
            backToHome(self)

    def customerOrderForm(self):
        self.customerOrderForm = tk.Toplevel(self)
        self.customerOrderForm.title("Order Form")
        self.customerOrderForm.geometry("400x400")
        tk.Label(self.customerOrderForm, text="Customer Order Form", font=("San Francisco", 24)).pack(pady=10)

        orderForm = tk.Frame(self.customerOrderForm)
        orderForm.pack(pady=20)
        # Define order rows
        orderFields = ["orderDueDate", "orderPostCode"]
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
        ttk.Button(orderForm, text="Submit", command=lambda: self.submit(orderFields), bootstyle="success").grid(padx=10, pady=5)
        ttk.Button(orderForm, text="Close", command=lambda: backToHome(self), bootstyle="danger").grid(padx=10, pady=5)

    def submit(self, orderFields):
        # Get order details from the text fields
        result = [str(orderRow.get("1.0", "end-1c")) for col, orderRow in self.orderRow.items()]

        # Add customerId to the result
        result.append(str(userId))

        submit(self, orderFields, result)

        self.customerOrderForm.destroy()
        del self.customerOrderForm
        backToHome(self)
         
    def pendingInvoices(self):
        self.customerPendingInvoices = tk.Toplevel(self)
        self.customerPendingInvoices.title("Order Form")
        self.customerPendingInvoices.geometry("400x700")

        self.columnsToDisplay = ["orderId", "invoiceAmount", "orderStatus"]
        
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
            if order["orderStatus"] == "Recieved, Awaiting Payment":
                self.tree.insert("", "end", values=values)

        pendingInvoices = tk.Frame(self.customerPendingInvoices)
        pendingInvoices.pack(pady=10)

        ttk.Button(pendingInvoices, text="Close", command=lambda: backToHome(self), bootstyle="danger").grid(row=0, column=5, padx=10, pady=5)

class distributorFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master

        self.initHomePage()

    def initHomePage(self):
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
                currentOrderId = distributorRecord.get("distributorCurrentOrder", "N/A")
            else:
                messagebox.showerror("Database Error", f"Distributor with Id {userId} not found")

            # Filter orders for this distributor
            distributorOrders = [order for order in orderData if str(order["distributorId"]) == str(userId)]

            # Compute general stats
            totalOrders = len(distributorOrders)
            totalHouses = sum(int(order.get("orderHousesNum", 0)) for order in distributorOrders)

            # Get the most recent 3 orders (sorted by date)
            recentOrders = sorted(distributorOrders, key=lambda x: x["orderDate"])[:3]
            orderResult = [(order["orderPostCode"], order["orderHousesNum"], order["orderDueDate"]) for order in recentOrders]

            if not recentOrders:
                messagebox.showinfo("Recent Order Error", "No recent orders found.")


            # Get current order details, where orderId matches the currentOrderId
            if not currentOrderId == None:
                print(currentOrderId)
                print(distributorOrders)
                currentOrder = [order for order in distributorOrders if int(order["orderId"]) == int(currentOrderId)]

                # Extract details of the most recent current order
                currentOrder = sorted(currentOrder, key=lambda x: x["orderDate"])[0]
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

        # Use ttk.Entry for readonly fields
        distributorNameVar = tk.StringVar(value=distributorLName)
        distributorPhoneVar = tk.StringVar(value=distributorPhone)
        distributorEmailVar = tk.StringVar(value=distributorEmail)

        distributorNameField = ttk.Entry(distributorDetails, textvariable=distributorNameVar, state='readonly')
        distributorNameField.grid(row=6, column=5, padx=10, pady=10)
        distributorPhoneField = ttk.Entry(distributorDetails, textvariable=distributorPhoneVar, state='readonly')
        distributorPhoneField.grid(row=7, column=5, padx=10, pady=10)
        distributorEmailField = ttk.Entry(distributorDetails, textvariable=distributorEmailVar, state='readonly')
        distributorEmailField.grid(row=8, column=5, padx=10, pady=10)


        self.entryFields = {
            "distributorLName": distributorNameField,
            "distributorEmail": distributorEmailField,
            "distributorPhone": distributorPhoneField
        }
        # Current Order Details
        if orderPostCode == None:
            ttk.Button(distributorDetails, text="View Available Orders", command = lambda: self.viewAvailableOrders(), bootstyle="info").grid(row=0, column=0, padx=10, pady=10, columnspan=2, rowspan=5, sticky=NSEW)        
        else:
            ttk.Label(distributorDetails, text="Current Order").grid(row=0, column=0, padx=10, pady=10)
            ttk.Label(distributorDetails, text="Post Code").grid(row=1, column=0, padx=10, pady=10)
            ttk.Label(distributorDetails, text="Number of Houses").grid(row=2, column=0, padx=10, pady=10)
            ttk.Label(distributorDetails, text="Due Date").grid(row=3, column=0, padx=10, pady=10)
            ttk.Label(distributorDetails, text="Price").grid(row=4, column=0, padx=10, pady=10)

            orderPostCodeVar = tk.StringVar(value=orderPostCode)
            orderHousesNumVar = tk.StringVar(value=str(orderHousesNum))
            orderDueDateVar = tk.StringVar(value=orderDueDate)
            orderCalculatedVar = tk.StringVar(value=str(int(orderHousesNum) * int(distributorRate) / 20))

            ttk.Entry(distributorDetails, textvariable=orderPostCodeVar, state='readonly').grid(row=1, column=1, padx=10, pady=10)
            ttk.Entry(distributorDetails, textvariable=orderHousesNumVar, state='readonly').grid(row=2, column=1, padx=10, pady=10)
            ttk.Entry(distributorDetails, textvariable=orderDueDateVar, state='readonly').grid(row=3, column=1, padx=10, pady=10)
            ttk.Entry(distributorDetails, textvariable=orderCalculatedVar, state='readonly').grid(row=4, column=1, padx=10, pady=10)


            # Map Image
            imagePath = f"./Maps/{orderPostCode}.png"

            image = Image.open(imagePath)
            smallerImage = image.resize((300, 300))
            tkImage = ImageTk.PhotoImage(smallerImage)

            label = tk.Label(distributorDetails, image=tkImage)
            label.grid(row=0, column=5, padx=10, pady=5, rowspan=5, columnspan=2)

        # Account Statistics
        ttk.Label(distributorDetails, text="Account Statistics").grid(row=6, column=0, padx=10, pady=10)
        ttk.Label(distributorDetails, text="Total Orders Completed").grid(row=7, column=0, padx=10, pady=10)
        ttk.Label(distributorDetails, text="Total Houses Delivered To").grid(row=8, column=0, padx=10, pady=10)
        ttk.Label(distributorDetails, text="Distributor Pending Pay").grid(row=9, column=0, padx=10, pady=10)

        # Statistics Fields
        totalOrdersVar = tk.StringVar(value=str(totalOrders))
        totalHousesVar = tk.StringVar(value=str(totalHouses))
        distributorPayVar = tk.StringVar(value=str(distributorPay))

        ttk.Entry(distributorDetails, textvariable=totalOrdersVar, state='readonly').grid(row=7, column=1, padx=10, pady=10)
        ttk.Entry(distributorDetails, textvariable=totalHousesVar, state='readonly').grid(row=8, column=1, padx=10, pady=10)
        ttk.Entry(distributorDetails, textvariable=distributorPayVar, state='readonly').grid(row=9, column=1, padx=10, pady=10)


        # Past 3 Orders
        ttk.Label(distributorDetails, text="Past 3 Orders").grid(row=0, column=2, padx=10, pady=10)

        # Iteration Loop for past orders
        orderPostCodeVars = []
        orderDateVars = []
        orderBalanceVars = []

        for i, order in enumerate(orderResult):
            orderPostCode, orderHousesNum, orderDueDate = order
            orderAmount = int(distributorRate) * int(orderHousesNum) / 20

            orderPostCodeVar = tk.StringVar(value=str(orderPostCode))
            orderDateVar = tk.StringVar(value=str(orderDueDate))
            orderBalanceVar = tk.StringVar(value=str(orderAmount))
    
            orderPostCodeVars.append(orderPostCodeVar)
            orderDateVars.append(orderDateVar)
            orderBalanceVars.append(orderBalanceVar)
    
            ttk.Label(distributorDetails, text="Order PostCode").grid(row=3*i + 1, column=2, padx=10, pady=10)
            ttk.Entry(distributorDetails, textvariable=orderPostCodeVar, state='readonly').grid(row=3*i + 1, column=3, padx=10, pady=10)
    
            ttk.Label(distributorDetails, text="Order Date").grid(row=3*i + 2, column=2, padx=10, pady=10)
            ttk.Entry(distributorDetails, textvariable=orderDateVar, state='readonly').grid(row=3*i + 2, column=3, padx=10, pady=10)
    
            ttk.Label(distributorDetails, text="Balance Added").grid(row=3*i + 3, column=2, padx=10, pady=10)
            ttk.Entry(distributorDetails, textvariable=orderBalanceVar, state='readonly').grid(row=3*i + 3, column=3, padx=10, pady=10)


        # Functions
        ttk.Button(distributorDetails, text="Log Out", command=self.master.destroy, bootstyle="danger").grid(row=0, column=4, padx=10, pady=10)
        self.editButton = ttk.Button(distributorDetails, text="Change Account Details", command=lambda: self.changeAccountDetails(), bootstyle="info")
        self.editButton.grid(row=1, column=4, padx=10, pady=10)
        ttk.Button(distributorDetails, text="Completed Order", command=lambda: self.markOrderCompleted(), bootstyle="primary").grid(row=2, column=4, padx=10, pady=10)
        ttk.Button(distributorDetails, text="Copy Authentication Token", command=lambda: copyAuthKey(self), bootstyle="secondary").grid(row=3, column=4, padx=10, pady=10)
        ttk.Button(distributorDetails, text="Reset Authentication Token", command=lambda: resetAuthKey(self), bootstyle="secondary").grid(row=4, column=4, padx=10, pady=10)

    def viewAvailableOrders(self):
        
        clearFrame(self)
        
        tk.Label(self, text="Available Orders", font=("San Francisco", 24)).pack(pady=10)
        
        # Treeview widget for displaying data
        self.tree = ttk.Treeview(self, columns=["orderId", "orderPostCode", "orderHousesNum", "orderDueDate", "orderPayment"], show="headings")
        self.tree.pack(fill="both", expand=True)
        
        # Load data from JSON
        orders = loadJson(f"{dbPath}/order.json")
        
        # Set up Treeview headings
        for col in ["orderId", "orderPostCode", "orderHousesNum", "orderDueDate"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="w", width=100, stretch=True)

        # Bind configure event to auto-resize columns

        def resize_columns(event):
            totalWidth = event.width
            nCols = len(self.tree["columns"])
            if nCols > 0:
                colWidth = totalWidth // nCols
                for col in self.tree["columns"]:
                    self.tree.column(col, width=colWidth)

        self.tree.bind("<Configure>", resize_columns)

        # Get distributorRate
        distributorData = loadJson(f"{dbPath}/distributor.json")
        indexData = loadJson(f"{dbPath}/_index.json")
        distributorIndex = indexData.get("distributorIndex", {}).get(str(userId))
        distributorRate = distributorData[distributorIndex].get("distributorRate", 5)
        
        # Filter for only OrderStatus Paid, to be Devlivered
        filteredOrders = [order for order in orders if order["orderStatus"] == "Paid, to be Devlivered"]

        print(filteredOrders)
        # Sort orders by orderDueDate
        sortedOrders = sorted(filteredOrders, key=lambda x: x["orderDueDate"])
        
        # Insert data into Treeview
        for order in sortedOrders:
            values = [order.get(col, "N/A") for col in ["orderId", "orderPostCode", "orderHousesNum", "orderDueDate"]]
            orderPayment = int(order["orderHousesNum"]) * int(distributorRate) / 20
            values.append(orderPayment)
            self.tree.insert("", "end", values=values)
        
        buttonsFrame = tk.Frame(self)
        buttonsFrame.pack(pady=10)

        self.tree.bind("<Button-3>", self.rightClick)
        ttk.Button(buttonsFrame, text="Close", command=lambda: backToHome(self), bootstyle="danger").grid(row=0, column=5, padx=10, pady=5)

    def rightClick(self, event):
        # Create a context menu
        contextMenu = tk.Menu(self.master, tearoff=0)
    
        # Add a command to the menu
        contextMenu.add_command(label="Accept Order", command=lambda: self.acceptOrder(self.getSelectedId(event)))

        # Display the context menu at the mouse position
        contextMenu.post(event.x_root, event.y_root)

    def getSelectedId(self, event):
        row = self.tree.identify("item", event.x, event.y)
        if row:
            primaryKey = self.tree.item(row)["values"][0]
            return str(primaryKey)
        else:
            messagebox.showerror("No row selected", "Please select a row.")

    def acceptOrder(self, orderId):
        try:
            # Load JSON data
            orderData = loadJson(f"{dbPath}/order.json")
            distributorData = loadJson(f"{dbPath}/distributor.json")
            indexData = loadJson(f"{dbPath}/_index.json")
            # Get the index dictionary for the table
            orderIndex = indexData.get("orderIndex", {})
            # Find record's position using the index
            orderPosition = orderIndex.get(orderId)
            if orderPosition is not None:
                if orderData[orderPosition]["orderStatus"] == "Paid, to be Devlivered":
                    # Mark the record as Accepted
                    
                    orderData[orderPosition]["orderStatus"] = "Out for Delivery"
                    orderData[orderPosition]["distributorId"] = str(userId)
                    # Save updated JSON data
                    
                    writeJson(f"{dbPath}/order.json", orderData)
                    # Update the distributor's current order
                    
                    distributorData = loadJson(f"{dbPath}/distributor.json")
                    distributorIndex = indexData.get("distributorIndex", {}).get(str(userId))
                    distributorData[distributorIndex]["distributorCurrentOrder"] = orderId

                    writeJson(f"{dbPath}/distributor.json", distributorData)
                    
                    messagebox.showinfo("Successful Operation", "Order accepted successfully")
                else:
                    messagebox.showerror("Order Error", "Order is already accepted.")
            else:
                messagebox.showerror("Database Error", f"Order with Id {orderId} not found in index")
        except Exception as e:
            messagebox.showerror("Database Error", str(e))

        backToHome(self)

    def changeAccountDetails(self):
        if self.editButton["text"] == "Change Account Details":
            # Unlock fields
            for field in self.entryFields.values():
                field.config(state="normal")

            self.editButton.config(text="Submit Changes")
        else:
            # Process data and lock fields again
            updatedData = {label: field.get() for label, field in self.entryFields.items()}

            # Validate input
            if not updatedData["distributorLName"]:
                messagebox.showerror("Validation Error", "Distributor name cannot be empty.")
                return
            if not updatedData["distributorPhone"].isdigit() or not len(updatedData["distributorPhone"]) == 11 or not str(updatedData["distributorPhone"][:2]) == "07":
                messagebox.showerror("Validation Error", "Distributor phone number must be numeric in the format of 07XXXXXXXXX")
                return
            if "@" not in updatedData["distributorEmail"]:
                messagebox.showerror("Validation Error", "Please enter a valid distributor email.")
                return


            distributorData = loadJson(f"{dbPath}/distributor.json")
            indexData = loadJson(f"{dbPath}/_index.json")
            distributorIndex = indexData.get("distributorIndex", {}).get(str(userId))

            if distributorIndex is not None:
                distributorRecord = distributorData[distributorIndex]
                for key, value in updatedData.items():
                    distributorRecord[key] = value
                writeJson(f"{dbPath}/distributor.json", distributorData)
                messagebox.showinfo("Updated Data", "Values updated successfully.")
            else:
                messagebox.showerror("Database Error", f"Distributor with Id {userId} not found")

            for field in self.entryFields.values():
                field.config(state="readonly")

            self.editButton.config(text="Change Account Details")

            backToHome(self)

    def markOrderCompleted(self):
        # Get current orderId
        distributorData = loadJson(f"{dbPath}/distributor.json")
        indexData = loadJson(f"{dbPath}/_index.json")
        distributorIndex = indexData.get("distributorIndex", {}).get(str(userId))
        currentOrderId = distributorData[distributorIndex].get("distributorCurrentOrder", "N/A")
        if currentOrderId == None:
            messagebox.showerror("No Order", "No current order found.")
        else:
            # Load JSON data
            orderData = loadJson(f"{dbPath}/order.json")
            orderIndex = indexData.get("orderIndex", {})
            
            # Find record's position using the index
            orderPosition = orderIndex.get(currentOrderId)
            
            if orderPosition is not None:
                # Mark the record as Completed
                orderData[orderPosition]["orderStatus"] = "Order Completed"
                
                # Update the distributor's current order
                distributorData[distributorIndex]["distributorCurrentOrder"] = None

                #Update distributor payment
                distributorData[distributorIndex]["distributorPay"] = float(distributorData[distributorIndex]["distributorPay"]) + (int(orderData[orderPosition]["orderHousesNum"]) * float(distributorData[distributorIndex]["distributorRate"]) / 20)


                # Save updated JSON data
                writeJson(f"{dbPath}/order.json", orderData)
                writeJson(f"{dbPath}/distributor.json", distributorData)
                
                messagebox.showinfo("Successful Operation", "Order marked as completed successfully.")

                buildIndex()
            else:
                messagebox.showerror("Database Error", f"Order with Id {currentOrderId} not found in index")

        backToHome(self)


# Main Running Loop

if __name__ == "__main__":
    buildIndex()
    app = Application()
    app.mainloop()