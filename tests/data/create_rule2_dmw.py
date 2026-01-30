from openpyxl import Workbook

wb = Workbook()
ws = wb.active

ws.append([
    "Source Table",
    "Destination Table",
    "Introduced Sprint (for data migration sprint)",
    "Last Updated in Sprint/Pass",
    "Chang Log (for data migration reference)"
])

# 1. Same sprint, no changelog -> PASS
ws.append(["SRC", "DST", "S1", "S1", ""])

# 2. Different sprint, changelog present -> PASS
ws.append(["SRC", "DST", "S1", "S2", "Updated mapping logic"])

# 3. Different sprint, changelog missing -> FAIL
ws.append(["SRC", "DST", "S1", "S2", ""])

# 4. Missing Introduced Sprint -> FAIL
ws.append(["SRC", "DST", "", "S1", "Initial"])

# 5. Helper row -> N/A
ws.append(["NA", "NA", "", "", ""])

wb.save("tests/data/rule2_dmw.xlsx")
print("[OK] Created tests/data/rule2_dmw.xlsx")
