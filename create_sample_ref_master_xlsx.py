#!/usr/bin/env python3
from openpyxl import Workbook
from pathlib import Path

# Output file
out_path = Path("/opt/oss-migrate/llm-planner/uploads/sample_ref_master.xlsx")
out_path.parent.mkdir(parents=True, exist_ok=True)

# Workbook & sheet
wb = Workbook()
ws = wb.active
ws.title = "Baseline Data Model"

# Headers (row 2 as per validator)
headers = [
    "Destination Table",
    "Destination Column Name",
    "Migrating or Not (Yes/No)",
    "DataType (Destination)",
    "Max_Length (in Chars)",
    "Is it Nullable? Yes/No",
    "Transformation Description (Transformation Logic)",
    "Table Type",
    "Allowed Values / Codes Table"
]

# Leave row 1 empty (some DMWs use metadata), put headers at row 2
ws.append([""] * len(headers))
ws.append(headers)

# Sample data rows
rows = [
    ["REF_CODES", "CODE_ID", "YES", "INT", "4", "NO", "Direct Map", "REFERENCE", "MASTER_CODES"],
    ["REF_CODES", "CODE_NAME", "YES", "VARCHAR(50)", "50", "YES", "Direct Map", "REFERENCE", "MASTER_CODES"],
    ["MASTER_CODES", "CODE_ID", "YES", "INT", "4", "NO", "Direct Map", "MASTER", ""],
    ["MASTER_CODES", "CODE_NAME", "YES", "VARCHAR(50)", "50", "YES", "Direct Map", "MASTER", ""],
    # Intentionally wrong mapping to test Rule5 FAIL
    ["REF_CODES", "ACTIVE_FLAG", "YES", "CHAR(1)", "1", "YES", "Extra col not in master", "REFERENCE", "MASTER_CODES"]
]

for r in rows:
    ws.append(r)

wb.save(out_path)
print(f"[OK] Sample DMW Excel created → {out_path}")
