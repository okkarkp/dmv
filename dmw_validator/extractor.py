import os, json, pandas as pd

def _normalize_header(col: str):
    col = str(col).strip().lower()
    synonyms = {
        "target table": "target table name",
        "target field": "target field name",
        "source table": "source table name",
        "source field": "source field name",
        "transformation": "transformation logic",
        "logic": "transformation logic"
    }
    for k, v in synonyms.items():
        if col.startswith(k):
            return v
    return col

def _read_excel_safely(path):
    """Auto-detect correct header row by scanning for 'Target' and 'Source' terms."""
    xls = pd.ExcelFile(path)
    for sheet in xls.sheet_names:
        df = pd.read_excel(path, sheet_name=sheet, header=None)
        for i in range(min(10, len(df))):
            row_values = [str(x).strip().lower() for x in df.iloc[i].tolist()]
            if any("target" in v for v in row_values) and any("source" in v for v in row_values):
                df = pd.read_excel(path, sheet_name=sheet, header=i)
                df.columns = [_normalize_header(c) for c in df.columns]
                print(f"✅ Using sheet '{sheet}' with header row {i+1}")
                return df
    raise ValueError("❌ Could not find a valid header row in Excel")

def extract_dmw_rows(xlsx_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    df = _read_excel_safely(xlsx_path)

    critical_cols = [
        "target table name",
        "target field name",
        "source table name",
        "source field name",
        "transformation logic"
    ]

    missing_cols = [c for c in critical_cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing critical columns in Excel: {missing_cols}")

    valid_rows, missing_rows = [], []

    for idx, row in df.iterrows():
        missing = [c for c in critical_cols if pd.isna(row.get(c)) or row.get(c) == ""]
        if missing:
            missing_rows.append({"row": int(idx)+2, "missing_fields": missing})
        valid_rows.append({
            "table": str(row.get("target table name", "")).strip(),
            "field": str(row.get("target field name", "")).strip(),
            "data": {k: ("" if pd.isna(row.get(k)) else str(row.get(k))) for k in df.columns}
        })

    valid_file = os.path.join(out_dir, os.path.basename(xlsx_path).replace(".xlsx", "_valid.json"))
    missing_file = os.path.join(out_dir, os.path.basename(xlsx_path).replace(".xlsx", "_missing.json"))

    with open(valid_file, "w") as f:
        json.dump(valid_rows, f, indent=2)
    with open(missing_file, "w") as f:
        json.dump(missing_rows, f, indent=2)

    print(f"✅ Processed {xlsx_path}: {len(valid_rows)} rows, {len(missing_rows)} issues")
    print(f"✅ Output → {valid_file}")
    return valid_file, missing_file, None
