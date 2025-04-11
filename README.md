# LDPSystem

# Website Project README

## Overview

This document provides instructions for operating the system, including how to log in, manage orders, and maintain customer, distributor, and admin records.

---

## User Authentication

### Login Credentials:

- **Admins:**

  - Email: \`10\`
  - Authentication Key: `SMJMPTNFE5KDFVDFCVBHSYOKYNNRJOOE`

- **Distributors:**

  - Example Email: `1001`
  - Authentication Key: `SMJMPTNFE5KDFVDFCVBHSYOKYNNRJOOE`

- **Customers:**

  - Example Email: `10001`
  - Authentication Key: `SMJMPTNFE5KDFVDFCVBHSYOKYNNRJOOE`

Ensure to use your provided authentication key for successful login.

---

## Data Files

The system operates with JSON files for data management:

- **admin.json:** Stores admin details
- **distributor.json:** Stores distributor details
- **customer.json:** Stores customer details
- **order.json:** Stores order details
- **_index.json:** Stores information on the location of Primary IDs within each of the json files, used for keeping 3rd normal form

---

## How to Run the Website

1. Ensure your development environment has Python installed.

2. Install necessary Python packages with this command: `pip install -r requirements.txt`

3. Run the main file called LDPSystem.py

4. To Login without having to use an external verification software like [Microsoft Authenticator](https://www.microsoft.com/en-gb/security/mobile-authenticator-app), or [Google Authenticator](https://support.google.com/accounts/answer/1066447?hl=en&co=GENIE.Platform%3DAndroid):

5. Run `AuthenticationCodes.py`

6. Enter the ID that you'd like to log into using the above IDs

7. The Program will output the next 2 codes that you can use to log in with in 30 second intervals

---

## System Features

### Admin Functionalities:

- View and manage all orders
- Add, edit, or remove distributors
- Add, edit, or remove customers
- Create Orders for any customer
- View and manage Distributor Pay Invoices

### Distributor Functionalities:

- View assigned orders or View Available Orders when no active order exists
- Update order statuses
- Copy or Reset own Authentication Key
- View Assigned Order map

### Customer Functionalities:

- Place orders
- View order history and statuses
- VIew Pending invoices for unpaid orders

---


## Maintenance

### Updating Records:

- Update JSON files directly or through admin dashboard.
- Ensure proper validation to avoid data corruption.

### Security Practices:

- Regularly rotate authentication keys.
- Backup JSON data regularly by archiving the database folder
- Change the Global Variable dbPath in the program to reflect where you'd like to keeo your database files, this can be on a seperate server off-site which the program can connect to

---


## External Libraries

Specify any external libraries used, for example:

- turtle
- pyotp
- osmnx
- geopandas
- networkx
- matplotlib
- contextily
- geopy
- scipy
- shapely
- PIL
- ttkbootstrap

---

## Troubleshooting

- Verify JSON data integrity if encountering login or data issues.
- Confirm correct installation of Python dependencies.

---

**End of README**


