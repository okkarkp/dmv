from openpyxl import Workbook

wb = Workbook()
ws = wb.active

ws.append([
    "Source Table",
    "Source Column Name",
    "Migrating or Not (Yes/No)",
    "Reason for Not Migrating",
    "Destination Table",
    "Destination Column Name",
    "Data Type",
    "Max Length",
    "Precision",
    "Scale",
    "Is it Nullable? Yes/No",
    "Transformation Description"
])

# A: Migrating YES – valid
ws.append(["SRC", "COL1", "Yes", "", "DST", "COL1", "INT", "10", "", "", "No", "Direct"])

# A: Migrating YES – missing datatype
ws.append(["SRC", "COL2", "Yes", "", "DST", "COL2", "", "10", "", "", "No", "Direct"])

# B: Migrating NO – valid
ws.append(["SRC", "COL3", "No", "Dropped in IRIN3", "NA", "NA", "", "", "", "", "", ""])

# B: Migrating NO – missing reason
ws.append(["SRC", "COL4", "No", "", "NA", "NA", "", "", "", "", "", ""])

# C: Destination-only – valid
ws.append(["NA", "NA", "Yes", "", "DST", "NEWCOL", "NVARCHAR", "50", "", "", "Yes", "Derived"])

# C: Destination-only – invalid
ws.append(["NA", "NA", "Yes", "", "DST", "BADCOL", "", "", "", "", "", ""])

wb.save("tests/data/rule1_dmw.xlsx")
print("[OK] Created tests/data/rule1_dmw.xlsx")
