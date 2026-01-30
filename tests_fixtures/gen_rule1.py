from openpyxl import Workbook
wb = Workbook()
ws = wb.active
ws.title = "Baseline Data Model"

headers = [
    "Source Table","Source Column Name",
    "Destination Table","Destination Column Name",
    "Migrating Column","Reason for Not Migrating",
    "Destination Data Type","Destination Data Length",
    "Destination Nullable","Transformation Logic"
]
ws.append(headers)

# Case 1: Migrating = No, reason blank → FAIL
ws.append(["SRC","A","T1","C1","No","","","","",""])

# Case 2: Migrating = Yes, missing transformation → FAIL
ws.append(["SRC","B","T1","C2","Yes","","INT","","NOT NULL",""])

wb.save("tests_fixtures/dmw/rule1.xlsx")
