#!/usr/bin/env python3
from openpyxl import Workbook
from pathlib import Path

OUT_DIR = Path("/app/sim_data")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def make_ddl(filename, tables):
    sql=[]
    for t, cols in tables.items():
        sql.append(f"CREATE TABLE {t} (")
        for c, dtype, nullable in cols:
            nn = "NOT NULL" if nullable == "NO" else ""
            sql.append(f"  {c} {dtype} {nn},")
        sql[-1] = sql[-1].rstrip(",")
        sql.append(");\n")
    (OUT_DIR/filename).write_text("\n".join(sql))
    print(f"[OK] Created {filename}")

def make_dmw(filename):
    wb = Workbook()
    ws = wb.active
    ws.title = "Baseline Data Model"

    headers = [
        "Source DB","Source Table","Source Column Name","Source Column Descrption",
        "Data Type","Max Length","Scale","Format Example","DB Default Value","PK/FK/UK/NA",
        "Table Type","Allowed Values / Codes Table","Remarks","Migrating or Not (Yes/No)",
        "Reason for Not Migrating","Destination Table","Master Domain","Table in P3AB? Yes/No",
        "Destination Column Name","Destination Column Description","Column in P3AB? Yes/No",
        "DataType (Destination)","Max_Length (in Chars)","Precision","Scale","PK/FK/UK/NA",
        "Is it Nullable? Yes/No","Default Value","Transformation Description (Transformation Logic)",
        "Is Recon Requirement Mandatory or Optional?","Reconn Requirements to Col Level","TPR",
        "Is the Field visible in IRIN3 P3 UI?","Code Table Name in IRIN3 P3 (if any)","Code Table Name in IRIN2 (if any)",
        "Last Updated in Sprint/Pass","Introduced Sprint (for data migration sprint)","Chang Log (for data migration reference)",
        "Owner Squad","Remarks","Phase","S/N"
    ]
    ws.append(headers)
    ws.append(headers)

    data = [
        # ✅ Rule2 PASS (same sprint)
        ("SRCDB","SRC_TAX","SRC_TAX_ID","Tax Identifier","VARCHAR",10,"","","","","DATA","","",
         "YES","","TGT_TAX","","YES","TAX_ID","Tax Identifier","YES","VARCHAR",10,"","","PK","NO","","UPPER(SRC_TAX_ID)",
         "MANDATORY","","","","","","Sprint1","Sprint1","","","","",1),

        # ❌ Rule2 FAIL (missing sprint)
        ("SRCDB","SRC_TAX","SRC_TAX_NAME","Tax Name","VARCHAR",100,"","","","","DATA","","",
         "YES","","TGT_TAX","","YES","TAX_NAME","Tax Name","YES","VARCHAR",100,"","","PK","NO","","TRIM(SRC_TAX_NAME)",
         "OPTIONAL","","","","","","","","","","","",2),

        # ❌ Rule2 FAIL (mismatch + no changelog)
        ("SRCDB","SRC_TAX","SRC_OLD_FIELD","Old Field","VARCHAR",50,"","","","","DATA","","",
         "YES","","TGT_TAX","","YES","OLD_FIELD","Old Field","YES","VARCHAR",50,"","","PK","NO","","",
         "MANDATORY","","","","","","Sprint1","Sprint3","","","","",3),

        # ✅ Rule2 PASS (different sprints + change log provided)
        ("SRCDB","SRC_TAX","SRC_NEW_FIELD","New Computed","VARCHAR",20,"","","","","DATA","","",
         "YES","","TGT_TAX","","YES","NEW_FIELD","New Computed","YES","VARCHAR",20,"","","PK","NO","","SRC1+SRC2",
         "MANDATORY","","","","","","Sprint2","Sprint3","Column newly added","", "",4),
    ]
    for row in data: ws.append(list(row))

    wb.save(OUT_DIR/filename)
    print(f"[OK] Created {filename}")

ddl_v2 = {
    "TGT_TAX": [
        ("TAX_ID","VARCHAR(10)","NO"),
        ("TAX_NAME","VARCHAR(100)","YES"),
        ("NEW_FIELD","VARCHAR(20)","YES")
    ]
}
make_ddl("DDL_WithholdingDB_v2.sql", ddl_v2)
make_dmw("DataMappingWorkbook_Withholding_v2.xlsx")
