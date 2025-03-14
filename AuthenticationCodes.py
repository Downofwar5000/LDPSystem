# Import libraries
import json
import pyotp
import time

def loadJson(filename):
    # Loads a JSON file and returns its contents
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []  # Return an empty list if file doesn't exist or is corrupted


# Define Globar Vars
ID = [[2, 4, 5],["admin", "distributor", "customer"]]
dbPath = "./_database"


# Function to fetch the authentication key of an account by primary key
def fetchAuthByID(enteredID, table):
    # Fetches the authentication key for a given user ID
    indexData = loadJson(f"{dbPath}/_index.json")
    tableFile = f"{dbPath}/{table}.json"

    recordPosition = indexData[table + "Index"][str(enteredID)]
    tableData = loadJson(tableFile)

    authKey = tableData[recordPosition]["authenticationKey"]
    
    print(authKey)
    return authKey

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
        table = ID[1][arrayPos]
        correctKey = generateAuthKey(fetchAuthByID(userID))
    except ValueError:
        print("Length not found in the array.", "Please try a different ID")

