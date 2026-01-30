from openpyxl import Workbook
from pathlib import Path

Path("tests/data").mkdir(parents=True, exist_ok=True)

wb = Workbook()
ws = wb.active
ws.title = "Baseline Data Model_output"

# Minimal columns needed for Rule4
ws.append(["Destination Table", "Destination Column Name", "Data Type"])

# ✅ MATCH (should PASS)
ws.append(["T_RULE4", "ID", "int"])

# ❌ DMW_ONLY (column not in DDL)
ws.append(["T_RULE4", "EXTRA_COL", "int"])

# ❌ MISMATCH type (DDL has datetime2, DMW has datetimeoffset)
ws.append(["T_RULE4", "CREATED_AT", "datetimeoffset(7)"])

# ✅ SKIP (Destination is NA)
ws.append(["NA", "NA", "NA"])

out = "tests/data/rule4_dmw.xlsx"
wb.save(out)
print(f"[OK] Created {out}")
