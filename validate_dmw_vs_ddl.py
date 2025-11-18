import re
import sys
import argparse
from pathlib import Path
from collections import defaultdict
import pandas as pd

# ============================================================
#  NEW IRIN3 DMW → Column Name Normalisation Layer
#  Supports OLD (62-col) & NEW (63-col) templates
# ============================================================

COLUMN_ALIASES = {
    # Destination
    "destination table": "Destination Table",
    "destination column name": "Destination Column Name",

    # Data Type
    "data type": "Data Type",
    "datatype (destination)": "Data Type",
    "datatype": "Data Type",

    # Max length
    "max length": "Max Length",
    "max_length (in chars)": "Max Length",
    "max_length": "Max Length",

    # Precision
    "precision": "Precision",
    "precision (destination)": "Precision",

    # Scale
    "scale": "Scale",
    "scale (destination)": "Scale",

    # Nullable
    "is it nullable? yes/no": "Is it Nullable? Yes/No",
    "nullable": "Is it Nullable? Yes/No",

    # Default value
    "default value": "Default Value",

    # Transformation
    "transformation description": "Transformation Description",
    "transformation description (transformation logic)": "Transformation Description",
    "transformation logic": "Transformation Description",

    # Migrating flag
    "migrating or not (yes/no)": "Migrating or Not (Yes/No)",
}

def canon_col(col: str) -> str:
    """Normalize header names to NEW IRIN3 column names."""
    if not isinstance(col, str):
        return ""
    c = col.strip().lower()
    return COLUMN_ALIASES.get(c, col.strip())


# ============================================================
#  Normalization helpers
# ============================================================
def norm_ws(s):
    if pd.isna(s):
        return ""
    return str(s).strip()

def canon_yesno(s):
    s = norm_ws(s).upper()
    if s in ("Y","YES","TRUE","1"):
        return "YES"
    if s in ("N","NO","FALSE","0"):
        return "NO"
    return s

def strip_quotes(s):
    s = norm_ws(s)
    if (s.startswith(("'", '"')) 
        and s.endswith(("'", '"')) 
        and len(s) >= 2):
        return s[1:-1]
    return s


# ============================================================
#  Canonical type functions
# ============================================================
def canon_type(t):
    t = norm_ws(t).upper()
    base = re.sub(r"\s*\(.*\)", "", t).strip()

    aliases = {
        "VARCHAR2": "VARCHAR",
        "NVARCHAR2": "NVARCHAR",
        "VARCHAR(MAX)": "VARCHAR",
        "NVARCHAR(MAX)": "NVARCHAR",
        "CHARACTER VARYING": "VARCHAR",
        "NUMBER": "DECIMAL",
        "NUMERIC": "DECIMAL",
        "INT": "INTEGER",
        "INT4": "INTEGER",
        "INT8": "BIGINT",
        "DATETIME2": "DATETIME",
        "TIMESTAMP WITH TIME ZONE": "TIMESTAMP",
        "TIMESTAMP WITHOUT TIME ZONE": "TIMESTAMP",
        "BOOL": "BOOLEAN",
        "BIT": "BOOLEAN",
        "FLOAT4": "FLOAT",
        "FLOAT8": "DOUBLE"
    }
    return aliases.get(base, base)

def parse_type_sizes(t):
    """Extract (maxlen, precision, scale) from a type."""
    t = norm_ws(t)
    m = re.search(r"\(([^)]+)\)", t)
    if not m:
        return ("", "", "")

    parts = [p.strip() for p in m.group(1).split(",")]
    if len(parts) == 1:
        if canon_type(t) in ("CHAR","NCHAR","VARCHAR","NVARCHAR","BINARY","VARBINARY"):
            return (parts[0], "", "")
        else:
            return ("", parts[0], "0")
    elif len(parts) >= 2:
        return ("", parts[0], parts[1])

    return ("", "", "")


# ============================================================
#  DDL SQL → Parser
# ============================================================
CREATE_TABLE_RE = re.compile(r"CREATE\s+TABLE\s+(.+?)\s*\(", re.IGNORECASE | re.DOTALL)

def split_create_table_statements(sql_text):
    """Extract CREATE TABLE (…) blocks."""
    stmts = []
    i = 0
    n = len(sql_text)

    while True:
        m = CREATE_TABLE_RE.search(sql_text, i)
        if not m:
            break
        start = m.start()

        depth = 0
        j = m.end() - 1
        found = False
        while j < n:
            ch = sql_text[j]
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth <= 0:
                    k = j + 1
                    while k < n and sql_text[k].isspace():
                        k += 1
                    if k < n and sql_text[k] == ';':
                        stmts.append(sql_text[start:k+1])
                        i = k + 1
                        found = True
                        break
            j += 1
        if not found:
            i = m.end()
    return stmts


def parse_create_table(stmt):
    """Parse full CREATE TABLE → dict of column metadata."""
    m = CREATE_TABLE_RE.search(stmt)
    if not m:
        return None

    raw_table = m.group(1).strip()
    raw_table = re.sub(r'[\[\]"]', '', raw_table)
    if '.' in raw_table:
        raw_table = raw_table.split('.')[-1]

    table_name = raw_table.upper()

    start = m.end()
    depth = 1
    i = start
    n = len(stmt)
    token = []
    while i < n and depth > 0:
        ch = stmt[i]
        token.append(ch)
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        i += 1
    body = ''.join(token[:-1]).strip()

    parts = []
    buf = []
    depth = 0
    for ch in body:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        if ch == ',' and depth == 0:
            parts.append(''.join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append(''.join(buf).strip())

    columns = {}
    pk_cols = set()
    unique_cols = set()

    for line in parts:
        l = line.strip()
        ul = l.upper()

        if ul.startswith("CONSTRAINT "):
            l2 = re.sub(r"^CONSTRAINT\s+\S+\s+", "", ul, flags=re.IGNORECASE).strip()
            ul2 = l2
        else:
            ul2 = ul

        if ul2.startswith("PRIMARY KEY"):
            cols = re.findall(r"\(([^)]+)\)", ul2)
            if cols:
                for c in cols[0].split(","):
                    pk_cols.add(norm_ws(c).strip('"[] ').upper())
            continue

        if ul2.startswith("UNIQUE"):
            cols = re.findall(r"\(([^)]+)\)", ul2)
            if cols:
                ucols = [norm_ws(c).strip('"[] ').upper() for c in cols[0].split(",")]
                if len(ucols) == 1:
                    unique_cols.add(ucols[0])
            continue

        mcol = re.match(r'^("?[A-Za-z0-9_\$#]+"?)\s+(.+)$', l, flags=re.DOTALL)
        if not mcol:
            continue

        col_name_raw, rest = mcol.group(1), mcol.group(2)
        col_name = col_name_raw.strip('"[]').upper()

        dtokens = []
        toks = re.split(r'\s+', rest.strip())
        i2 = 0
        paren_depth = 0
        while i2 < len(toks):
            tk = toks[i2]
            u = tk.upper()
            if u in ("NOT","NULL","DEFAULT","PRIMARY","UNIQUE","REFERENCES","CHECK","CONSTRAINT"):
                if paren_depth == 0:
                    break
            paren_depth += tk.count("(") - tk.count(")")
            dtokens.append(tk)
            i2 += 1
        data_type_str = " ".join(dtokens).strip()

        tail = " ".join(toks[i2:]).upper()
        not_null = ("NOT NULL" in tail)
        has_inline_pk = ("PRIMARY KEY" in tail)
        has_inline_unique = ("UNIQUE" in tail and not has_inline_pk)

        def_m = re.search(r"DEFAULT\s+([^ ]+)", " ".join(toks[i2:]), flags=re.IGNORECASE)
        default_val = strip_quotes(def_m.group(1)) if def_m else ""

        char_len, prec, scale = parse_type_sizes(data_type_str)

        columns[col_name] = {
            "data_type": data_type_str,
            "char_length": norm_ws(char_len),
            "precision": norm_ws(prec),
            "scale": norm_ws(scale),
            "is_nullable_yesno": "NO" if not_null else "YES",
            "default": default_val,
            "inline_pk": bool(has_inline_pk),
            "inline_unique": bool(has_inline_unique),
        }

    for c, meta in columns.items():
        if meta["inline_pk"]:
            pk_cols.add(c)
        if meta["inline_unique"]:
            unique_cols.add(c)

    return table_name, columns, pk_cols, unique_cols


def build_ddl_index(sql_text):
    ddl = {}
    pk_index = defaultdict(set)
    unique_index = defaultdict(set)

    for stmt in split_create_table_statements(sql_text):
        parsed = parse_create_table(stmt)
        if not parsed:
            continue
        table_name, columns, pk_cols, uniq_cols = parsed

        ddl[table_name] = columns
        pk_index[table_name] |= set(pk_cols)
        unique_index[table_name] |= set(uniq_cols)

    return ddl, pk_index, unique_index


# ============================================================
#  Main Row Comparison (DMW vs DDL)
# ============================================================
def compare_row(row, ddl, pk_index, unique_index):
    issues = []
    norm_row = {canon_col(k): norm_ws(v) for k, v in row.items()}

    # Destination table & column
    dest_table = norm_ws(norm_row.get("Destination Table", "")).upper()
    dest_col   = norm_ws(norm_row.get("Destination Column Name", "")).upper()

    table_missing = dest_table == "" or dest_table not in ddl
    col_missing = False
    if not table_missing:
        col_missing = dest_col == "" or dest_col not in ddl[dest_table]

    flags = {
        "Table_Missing_in_DDL": "YES" if table_missing else "NO",
        "Column_Missing_in_DDL": "YES" if (not table_missing and col_missing) else ("NO" if not table_missing else ""),
        "DataType_Mismatch": "",
        "Length_Mismatch": "",
        "Precision_Mismatch": "",
        "Scale_Mismatch": "",
        "Nullable_Mismatch": "",
        "DefaultValue_Mismatch": "",
        "Missing_Transformation_Logic": "",
    }

    mig = canon_yesno(norm_row.get("Migrating or Not (Yes/No)", ""))
    trans = norm_ws(norm_row.get("Transformation Description", ""))

    if mig == "YES" and trans == "":
        flags["Missing_Transformation_Logic"] = "YES"
        issues.append("Missing Transformation Description")

    if table_missing:
        issues.append("Destination table not found in DDL")
        return flags, issues

    if col_missing:
        issues.append("Destination column not found in DDL")
        return flags, issues

    # DMW values — NEW column names
    dmw_dtype = norm_row.get("Data Type", "")
    dmw_len   = norm_row.get("Max Length", "")
    dmw_prec  = norm_row.get("Precision", "")
    dmw_scale = norm_row.get("Scale", "")
    dmw_nullable = canon_yesno(norm_row.get("Is it Nullable? Yes/No", ""))
    dmw_default  = strip_quotes(norm_row.get("Default Value", ""))

    # DDL values
    meta = ddl[dest_table][dest_col]
    ddl_dtype = meta["data_type"]
    ddl_len   = meta["char_length"]
    ddl_prec  = meta["precision"]
    ddl_scale = meta["scale"]
    ddl_nullable = meta["is_nullable_yesno"]
    ddl_default  = meta["default"]

    # Compare canonical data types
    if canon_type(dmw_dtype) != canon_type(ddl_dtype):
        flags["DataType_Mismatch"] = "YES"
        issues.append(f"DataType mismatch (DMW={dmw_dtype}, DDL={ddl_dtype})")
    else:
        flags["DataType_Mismatch"] = "NO"

    # Length
    if canon_type(dmw_dtype) in ("CHAR","NCHAR","VARCHAR","NVARCHAR","BINARY","VARBINARY"):
        if (dmw_len or ddl_len) and (str(dmw_len) != str(ddl_len)):
            flags["Length_Mismatch"] = "YES"
            issues.append(f"Length mismatch (DMW={dmw_len}, DDL={ddl_len})")
        else:
            flags["Length_Mismatch"] = "NO"
    else:
        flags["Length_Mismatch"] = "NO"

    # Precision / Scale
    if canon_type(dmw_dtype) in ("DECIMAL","NUMERIC","NUMBER","FLOAT","DOUBLE","INTEGER","BIGINT","SMALLINT"):
        if (dmw_prec or ddl_prec) and (str(dmw_prec) != str(ddl_prec)):
            flags["Precision_Mismatch"] = "YES"
            issues.append(f"Precision mismatch (DMW={dmw_prec}, DDL={ddl_prec})")
        else:
            flags["Precision_Mismatch"] = "NO"
        if (dmw_scale or ddl_scale) and (str(dmw_scale) != str(ddl_scale)):
            flags["Scale_Mismatch"] = "YES"
            issues.append(f"Scale mismatch (DMW={dmw_scale}, DDL={ddl_scale})")
        else:
            flags["Scale_Mismatch"] = "NO"
    else:
        flags["Precision_Mismatch"] = "NO"
        flags["Scale_Mismatch"] = "NO"

    # Nullable
    if dmw_nullable and ddl_nullable and dmw_nullable != ddl_nullable:
        flags["Nullable_Mismatch"] = "YES"
        issues.append(f"Nullable mismatch (DMW={dmw_nullable}, DDL={ddl_nullable})")
    else:
        flags["Nullable_Mismatch"] = "NO"

    # Default values
    if (dmw_default or ddl_default) and (strip_quotes(dmw_default) != strip_quotes(ddl_default)):
        flags["DefaultValue_Mismatch"] = "YES"
        issues.append(f"Default mismatch (DMW={dmw_default}, DDL={ddl_default})")
    else:
        flags["DefaultValue_Mismatch"] = "NO"

    return flags, issues


# ============================================================
#  Change Log Computation
# ============================================================
def add_change_log(df):
    col_change = "Change Log (for data migration reference)"
    if col_change not in df.columns:
        df[col_change] = ""

    def _derive(row):
        lu = norm_ws(row.get("Last Updated in Sprint", ""))
        intro = norm_ws(row.get("Introduced Sprint (for data migration sprint)", "")) \
                or norm_ws(row.get("Introduced Sprint", ""))

        if lu and intro and lu != intro:
            return f"Changed in Sprint {lu}"

        return norm_ws(row.get(col_change, ""))

    df[col_change] = df.apply(_derive, axis=1)
    return df


# ============================================================
#  Main
# ============================================================
def main():
    ap = argparse.ArgumentParser(
        description="Validate DMW Baseline Data Model vs DDL (IRIN3 NEW 63-col supported)"
    )
    ap.add_argument("--dmw-xlsx", required=True)
    ap.add_argument("--sheet", default="Baseline Data Model")
    ap.add_argument("--ddl-sql", required=True)
    ap.add_argument("--out", default="Baseline Data Model_output.xlsx")

    args = ap.parse_args()

    xlsx_path = Path(args.dmw_xlsx)
    ddl_path = Path(args.ddl_sql)

    # Load Excel with patch reader
    from patch_excel_reader import load_dmw_sheet
    df = load_dmw_sheet(xlsx_path, args.sheet)

    # Normalize header names
    df.columns = [canon_col(c) for c in df.columns]

    # Build DDL index
    ddl_text = ddl_path.read_text(encoding="utf-8", errors="ignore")
    ddl, pk_index, unique_index = build_ddl_index(ddl_text)

    # Add validation result fields
    out_cols = [
        "Table_Missing_in_DDL",
        "Column_Missing_in_DDL",
        "DataType_Mismatch",
        "Length_Mismatch",
        "Precision_Mismatch",
        "Scale_Mismatch",
        "Nullable_Mismatch",
        "DefaultValue_Mismatch",
        "Missing_Transformation_Logic",
        "Validation_Status",
        "Validation_Remarks",
        "Change Log (for data migration reference)",
    ]
    for c in out_cols:
        if c not in df.columns:
            df[c] = ""

    for idx, row in df.iterrows():
        flags, issues = compare_row(row, ddl, pk_index, unique_index)

        for k, v in flags.items():
            df.at[idx, k] = v

        status = "FAIL" if any(
            v == "YES" for k, v in flags.items() if k not in ("Validation_Status","Validation_Remarks")
        ) else "PASS"

        df.at[idx, "Validation_Status"] = status
        df.at[idx, "Validation_Remarks"] = "; ".join(issues)

    df = add_change_log(df)

    # Preserve original Excel column order + appended
    original_order = list(pd.read_excel(xlsx_path, sheet_name=args.sheet, nrows=0).columns)
    original_order = [canon_col(c) for c in original_order]

    appended = [c for c in out_cols if c not in original_order]
    final_cols = original_order + appended

    from patch_safe_export import safe_export
    safe_export(df, args.out, final_cols)

    print(f"[OK] Wrote {args.out}")

if __name__ == "__main__":
    main()
