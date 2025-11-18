import os, json, pandas as pd

# ----------------------------------------------------------
# Header normalisation for BOTH IRIN2 & IRIN3 DMW templates
# ----------------------------------------------------------
HEADER_MAP = {
    # IRIN3 naming
    "destination table": "destination_table",
    "destination column name": "destination_column",
    "source table": "source_table",
    "source column name": "source_column",
    "transformation description": "transformation",
    "migrating or not (yes/no)": "migrating",

    # IRIN2 / legacy naming
    "target table name": "destination_table",
    "target field name": "destination_column",
    "source table name": "source_table",
    "source field name": "source_column",
    "transformation logic": "transformation",
    "logic": "transformation",
    "transformation": "transformation",
}

def _normalize(col: str):
    if not isinstance(col, str):
        return ""
    c = col.strip().lower()
    return HEADER_MAP.get(c, c)


# ----------------------------------------------------------
# Auto-detect real header row (IRAS DMW format)
# ----------------------------------------------------------
def _read_excel_safely(path):
    xls = pd.ExcelFile(path)

    for sheet in xls.sheet_names:
        df = pd.read_excel(path, sheet_name=sheet, header=None, dtype=str)
        df = df.fillna("")

        for i in range(min(10, len(df))):
            row_values = [str(v).strip().lower() for v in df.iloc[i].tolist()]

            # IRIN3 header detection: Source DB, Source Table, Source Column Name
            if row_values[:3] == ["source db", "source table", "source column name"]:
                df2 = pd.read_excel(path, sheet_name=sheet, header=i, dtype=str)
                df2 = df2.fillna("")
                df2.columns = [_normalize(c) for c in df2.columns]
                print(f"✅ Detected IRIN3 header in sheet '{sheet}' at row {i+1}")
                return df2

            # IRIN2 header detection: target + source pair
            if any("target" in v for v in row_values) and any("source" in v for v in row_values):
                df2 = pd.read_excel(path, sheet_name=sheet, header=i, dtype=str)
                df2 = df2.fillna("")
                df2.columns = [_normalize(c) for c in df2.columns]
                print(f"⚠️ Detected legacy (IRIN2-style) header in sheet '{sheet}' at row {i+1}")
                return df2

    raise ValueError("❌ Could not detect valid DMW header row.")


# ----------------------------------------------------------
# Main IRIN3-compatible extractor
# ----------------------------------------------------------
def extract_dmw_rows(xlsx_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    df = _read_excel_safely(xlsx_path)

    REQUIRED = [
        "destination_table",
        "destination_column",
        "source_table",
        "source_column",
        "transformation",
        # IRIN3-specific
        "migrating",
    ]

    missing_cols = [c for c in REQUIRED if c not in df.columns]
    if missing_cols:
        print(f"⚠️ Missing columns (some may be legacy IRIN2): {missing_cols}")

    valid_rows, missing_rows = [], []

    for idx, row in df.iterrows():
        row_norm = {k: ("" if pd.isna(v) else str(v).strip()) for k, v in row.items()}

        # Check if mandatory transformation fields present
        missing_fields = [
            c for c in REQUIRED if c in df.columns and row_norm.get(c, "") == ""
        ]

        if missing_fields:
            missing_rows.append({
                "row": int(idx)+2,
                "missing_fields": missing_fields
            })

        valid_rows.append({
            "destination_table": row_norm.get("destination_table", ""),
            "destination_column": row_norm.get("destination_column", ""),
            "source_table": row_norm.get("source_table", ""),
            "source_column": row_norm.get("source_column", ""),
            "transformation": row_norm.get("transformation", ""),
            "migrating": row_norm.get("migrating", ""),
            "full_row": row_norm
        })

    # Save JSON outputs
    base = os.path.basename(xlsx_path).replace(".xlsx", "")
    valid_file = os.path.join(out_dir, f"{base}_valid.json")
    missing_file = os.path.join(out_dir, f"{base}_missing.json")

    with open(valid_file, "w") as f:
        json.dump(valid_rows, f, indent=2)

    with open(missing_file, "w") as f:
        json.dump(missing_rows, f, indent=2)

    print(f"✅ Processed {xlsx_path}: {len(valid_rows)} rows, {len(missing_rows)} issues")
    print(f"📝 Output written to {valid_file}")

    return valid_file, missing_file, None

