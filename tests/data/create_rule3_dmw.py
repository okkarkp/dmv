from openpyxl import Workbook

wb = Workbook()

# Baseline Data Model
ws_base = wb.active
ws_base.title = "Baseline Data Model_output"
ws_base.append(["Destination Table"])
ws_base.append(["T_OK"])

# Table Details
ws_tbl = wb.create_sheet("Table Details")
ws_tbl.append(["Destination Table"])
ws_tbl.append(["T_OK"])
ws_tbl.append(["T_MISSING"])
ws_tbl.append(["NA"])

wb.save("tests/data/rule3_dmw.xlsx")
print("[OK] Created tests/data/rule3_dmw.xlsx")
