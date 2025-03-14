# Import libraries
import sqlite3
import pyotp
import time

# Connect to SQLite db
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Define Globar Vars
ID = [[2, 4, 5],["tblAdmin", "tblDistributor", "tblCustomer"]]

# Function to fetch the authentication key of an account by primary key
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
            print(f"No user found with ID: {enteredID}")
            return None
    except sqlite3.Error as e:
        print(f"Error occurred: {e}")
        return None

# Function to generate OTP based off of authKey
def generateAuthKey(authKey):
    currentTime = int(time.time())
    totp = pyotp.TOTP(str(authKey))
    otp1 = totp.at(currentTime)
    otp2 = totp.at(currentTime+30)
    otp = [otp1, otp2]
    print(f"The next 2 keys are: ", otp)
    return otp

while True:
    userID = input("Please enter the ID you'd like to login to: ")
    try:
        arrayPos = ID[0].index(len(userID))  # Look for the length in ID[1]
        print(f"Array position: {arrayPos}")
        table = ID[1][arrayPos]
        correctKey = generateAuthKey(fetchAuthByID(userID, table))
    except ValueError:
        print("Length not found in the array.", "Please try a different ID")

