import os, json
import pandas as pd

INPUT_FILES = [
    "DataMappingWorkbook_Enforcement.xlsx",
    "DataMappingWorkbook_Withholding v1.2.xlsx"
]

CRITICAL_COLUMNS = [
    "Target Table Name",
    "Target Field Name",
    "Source Table Name",
    "Source Field Name",
    "Transformation Logic"
]

output_folder = "outputs/dmw"
os.makedirs(output_folder, exist_ok=True)

for file in INPUT_FILES:
    wb = pd.ExcelFile(file)
    all_valid_rows = []
    all_issues = []

    for sheet in wb.sheet_names:
        try:
            df = wb.parse(sheet, dtype=str)
            df = df.fillna("").astype(str)

            # Normalize column names
            df.columns = [col.strip() for col in df.columns]

            for i, row in df.iterrows():
                row_data = {col: row.get(col, "").strip() for col in CRITICAL_COLUMNS}
                missing = [k for k, v in row_data.items() if not v]

                if missing:
                    all_issues.append({
                        "sheet": sheet,
                        "row": i + 2,
                        "missing_fields": missing,
                        "data": row_data
                    })
                else:
                    all_valid_rows.append(row_data)
        except Exception as e:
            print(f"❌ Failed to parse {file} [{sheet}]: {e}")

    # Save outputs
    base = os.path.splitext(os.path.basename(file))[0]
    with open(f"{output_folder}/{base}_valid.json", "w") as f:
        json.dump(all_valid_rows, f, indent=2)

    with open(f"{output_folder}/{base}_missing.json", "w") as f:
        json.dump(all_issues, f, indent=2)

    print(f"✅ Processed {file}: {len(all_valid_rows)} valid rows, {len(all_issues)} issues")
