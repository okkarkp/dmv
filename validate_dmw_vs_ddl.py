import re
import sys
import argparse
from pathlib import Path
from collections import defaultdict
import pandas as pd

# ---------------------------
# Helpers: normalization
# ---------------------------
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
    return s  # leave as-is for visibility

def strip_quotes(s):
    s = norm_ws(s)
    if s.startswith(("'", '"')) and s.endswith(("'", '"')) and len(s) >= 2:
        return s[1:-1]
    return s

# Map DB-specific types to canonical families for comparison
def canon_type(t):
    t = norm_ws(t).upper()
    # Remove size/precision suffixes for base comparison
    base = re.sub(r"\s*\(.*\)", "", t).strip()

    # Oracle & SQL Server & generic mappings
    aliases = {
        "VARCHAR2": "VARCHAR",
        "NVARCHAR2": "NVARCHAR",
        "VARCHAR(MAX)": "VARCHAR",
        "NVARCHAR(MAX)": "NVARCHAR",
        "CHARACTER VARYING": "VARCHAR",
        "NCHAR VARYING": "NVARCHAR",
        "NUMBER": "DECIMAL",
        "NUMERIC": "DECIMAL",
        "MONEY": "DECIMAL",
        "SMALLMONEY": "DECIMAL",
        "INT": "INTEGER",
        "INT4": "INTEGER",
        "INT8": "BIGINT",
        "SMALLINT": "SMALLINT",
        "TINYINT": "SMALLINT",
        "DATETIME2": "DATETIME",
        "DATETIMEOFFSET": "DATETIME",
        "SMALLDATETIME": "DATETIME",
        "TIMESTAMP WITHOUT TIME ZONE": "TIMESTAMP",
        "TIMESTAMP WITH TIME ZONE": "TIMESTAMP",
        "BOOL": "BOOLEAN",
        "BIT": "BOOLEAN",
        "FLOAT4": "FLOAT",
        "FLOAT8": "DOUBLE",
        "DOUBLE PRECISION": "DOUBLE"
    }
    return aliases.get(base, base)

def parse_type_sizes(t):
    """
    Returns (char_length, precision, scale) as strings or "" when not applicable.
    Examples:
      VARCHAR(50) -> (50, "", "")
      NVARCHAR(200) -> (200, "", "")
      DECIMAL(12,3) -> ("", 12, 3)
      NUMBER(10) -> ("", 10, 0)
      NUMBER -> ("", "", "")
    """
    t = norm_ws(t)
    m = re.search(r"\(([^)]+)\)", t)
    if not m:
        return ("", "", "")
    parts = [p.strip() for p in m.group(1).split(",")]
    if len(parts) == 1:
        # length or precision
        if canon_type(t) in ("VARCHAR","NVARCHAR","CHAR","NCHAR","BINARY","VARBINARY"):
            return (parts[0], "", "")
        else:
            # numeric precision only
            return ("", parts[0], "0")
    elif len(parts) >= 2:
        # precision, scale
        return ("", parts[0], parts[1])
    return ("", "", "")

def null_token_to_yesno(token):
    t = norm_ws(token).upper()
    if t in ("Y","YES","TRUE","1","NOT NULL"):
        return "NO"  # NOT NULL -> Is Nullable? = NO
    if t in ("N","NO","FALSE","0","NULL","NULLABLE"):
        return "YES"
    return t

# ---------------------------
# DDL parsing (raw SQL)
# ---------------------------
CREATE_TABLE_RE = re.compile(r"CREATE\s+TABLE\s+(.+?)\s*\(", re.IGNORECASE | re.DOTALL)
END_RE = re.compile(r"\)\s*;", re.DOTALL)

def split_create_table_statements(sql_text):
    """
    Returns list of (full_stmt_text).
    We look for balanced CREATE TABLE ... (...) ; blocks.
    """
    stmts = []
    i = 0
    n = len(sql_text)
    while True:
        m = CREATE_TABLE_RE.search(sql_text, i)
        if not m:
            break
        start = m.start()
        # find matching closing parenthesis followed by semicolon
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
                    # expect a semicolon after optional whitespace
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
            # fall back: try to next position
            i = m.end()
    return stmts

def parse_create_table(stmt):
    """
    Parse a single CREATE TABLE statement.
    Returns:
      table_name (UPPER)
      columns: dict col_name -> dict(
          data_type, char_length, precision, scale, is_nullable_yesno, default, inline_pk, inline_unique
      )
      table_pk_cols: set()
      table_unique_cols: set() (approx for single-col UNIQUE constraints)
    """
    # Extract table name
    m = CREATE_TABLE_RE.search(stmt)
    if not m:
        return None
    raw_table = m.group(1).strip()
    # Remove quotes/brackets and schema
    raw_table = re.sub(r'[\[\]"]', '', raw_table)
    if '.' in raw_table:
        raw_table = raw_table.split('.')[-1]
    table_name = raw_table.upper()

    # Extract inner body (between first "(" after CREATE TABLE and the matching ")")
    start = m.end()  # position just after '('
    depth = 1
    i = start
    n = len(stmt)
    content = []
    token = []
    while i < n and depth > 0:
        ch = stmt[i]
        token.append(ch)
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        i += 1
    body = ''.join(token[:-1]).strip()  # exclude the last ')'

    # Split by commas at top-level (not inside parentheses)
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
    table_pk_cols = set()
    table_unique_cols = set()

    for line in parts:
        l = line.strip()
        ul = l.upper()
        # Table constraints
        if ul.startswith("CONSTRAINT "):
            # Remove leading CONSTRAINT name
            l2 = re.sub(r"^CONSTRAINT\s+\S+\s+", "", ul, flags=re.IGNORECASE).strip()
            ul2 = l2.upper()
        else:
            ul2 = ul

        if ul2.startswith("PRIMARY KEY"):
            # Table-level PK: PRIMARY KEY (col1, col2)
            cols = re.findall(r"\(([^)]+)\)", ul2)
            if cols:
                for c in cols[0].split(","):
                    table_pk_cols.add(norm_ws(c).strip('"[] ').upper())
            continue
        if ul2.startswith("UNIQUE"):
            # Table-level UNIQUE (approx; only handle single-col cleanly)
            cols = re.findall(r"\(([^)]+)\)", ul2)
            if cols:
                unique_cols = [norm_ws(c).strip('"[] ').upper() for c in cols[0].split(",")]
                if len(unique_cols) == 1:
                    table_unique_cols.add(unique_cols[0])
            continue
        if ul2.startswith("FOREIGN KEY"):
            # Ignore FK at table-level for now
            continue

        # Column definition
        # Pattern: name type [constraints...]
        # e.g., "cust_id VARCHAR2(50) NOT NULL DEFAULT 'X'"
        # Column name = first token
        mcol = re.match(r'^("?[A-Za-z0-9_\$#]+"?)\s+(.+)$', l, flags=re.DOTALL)
        if not mcol:
            continue
        col_name_raw, rest = mcol.group(1), mcol.group(2)
        col_name = col_name_raw.strip('"[]').upper()

        # Data type token: read until we hit a known constraint keyword at top-level
        # We'll collect tokens until NOT|NULL|DEFAULT|PRIMARY|UNIQUE|REFERENCES|CHECK
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
            # track parentheses inside type
            paren_depth += tk.count("(") - tk.count(")")
            dtokens.append(tk)
            i2 += 1
        data_type_str = " ".join(dtokens).strip()

        tail = " ".join(toks[i2:]).upper()

        not_null = ("NOT NULL" in tail)
        has_inline_pk = ("PRIMARY KEY" in tail)
        has_inline_unique = ("UNIQUE" in tail) and not has_inline_pk  # avoid double count
        # Default value (rough parse)
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

    # Merge inline PK into table_pk_cols
    for c, meta in columns.items():
        if meta["inline_pk"]:
            table_pk_cols.add(c)
        if meta["inline_unique"]:
            table_unique_cols.add(c)

    return table_name, columns, table_pk_cols, table_unique_cols

def build_ddl_index(sql_text):
    ddl = {}
    pk_index = defaultdict(set)
    unique_index = defaultdict(set)

    for stmt in split_create_table_statements(sql_text):
        parsed = parse_create_table(stmt)
        if not parsed:
            continue
        table_name, columns, table_pk_cols, table_unique_cols = parsed
        ddl[table_name] = columns
        pk_index[table_name] |= set(table_pk_cols)
        unique_index[table_name] |= set(table_unique_cols)
    return ddl, pk_index, unique_index

# ---------------------------
# Validation logic
# ---------------------------
def compare_row(row, ddl, pk_index, unique_index):
    issues = []

    dest_table = norm_ws(row.get("Destination Table")).upper()
    dest_col = norm_ws(row.get("Destination Column Name")).upper()

    # Presence checks
    table_missing = dest_table == "" or dest_table not in ddl
    col_missing = False
    if not table_missing:
        col_missing = dest_col == "" or dest_col not in ddl[dest_table]

    # Initialize per-metric flags
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

    # Missing transformation logic (when migrating = Yes)
    mig = canon_yesno(row.get("Migrating or Not (Yes/No)", ""))
    trans = norm_ws(row.get("Transformation Description (Transformation Logic)", ""))
    if mig == "YES" and trans == "":
        flags["Missing_Transformation_Logic"] = "YES"
        issues.append("Missing Transformation Logic")

    # If table/col missing, we cannot compare structural attrs
    if table_missing:
        issues.append("Destination table not found in DDL")
        return flags, issues
    if col_missing:
        issues.append("Destination column not found in DDL")
        return flags, issues

    # DMW values
    dmw_dtype = norm_ws(row.get("DataType (Destination)", ""))
    dmw_len = norm_ws(row.get("Max_Length (in Chars)", ""))
    dmw_prec = norm_ws(row.get("Precision (Destination)", ""))
    dmw_scale = norm_ws(row.get("Scale (Destination)", ""))
    dmw_nullable = canon_yesno(row.get("Is it Nullable? Yes/No", ""))
    dmw_default = strip_quotes(row.get("Default Value", ""))

    # DDL values
    meta = ddl[dest_table][dest_col]
    ddl_dtype = meta["data_type"]
    ddl_len = meta["char_length"]
    ddl_prec = meta["precision"]
    ddl_scale = meta["scale"]
    ddl_nullable = meta["is_nullable_yesno"]  # YES/NO
    ddl_default = meta["default"]

    # Compare canonical types
    if canon_type(dmw_dtype) != canon_type(ddl_dtype):
        flags["DataType_Mismatch"] = "YES"
        issues.append(f"DataType mismatch (DMW={dmw_dtype}, DDL={ddl_dtype})")
    else:
        flags["DataType_Mismatch"] = "NO"

    # Length: only meaningful for char-ish types
    if canon_type(dmw_dtype) in ("CHAR","NCHAR","VARCHAR","NVARCHAR","BINARY","VARBINARY"):
        if (dmw_len or ddl_len) and (str(dmw_len or "") != str(ddl_len or "")):
            flags["Length_Mismatch"] = "YES"
            issues.append(f"Length mismatch (DMW={dmw_len}, DDL={ddl_len})")
        else:
            flags["Length_Mismatch"] = "NO"
    else:
        flags["Length_Mismatch"] = "NO"

    # Precision/Scale: for numeric types
    if canon_type(dmw_dtype) in ("DECIMAL","NUMERIC","NUMBER","FLOAT","DOUBLE","INTEGER","BIGINT","SMALLINT"):
        if (dmw_prec or ddl_prec) and (str(dmw_prec or "") != str(ddl_prec or "")):
            flags["Precision_Mismatch"] = "YES"
            issues.append(f"Precision mismatch (DMW={dmw_prec}, DDL={ddl_prec})")
        else:
            flags["Precision_Mismatch"] = "NO"

        if (dmw_scale or ddl_scale) and (str(dmw_scale or "") != str(ddl_scale or "")):
            flags["Scale_Mismatch"] = "YES"
            issues.append(f"Scale mismatch (DMW={dmw_scale}, DDL={ddl_scale})")
        else:
            flags["Scale_Mismatch"] = "NO"
    else:
        flags["Precision_Mismatch"] = "NO"
        flags["Scale_Mismatch"] = "NO"

    # Nullable mapping: DMW (Yes/No) vs DDL YES/NO
    dmw_nullable_yesno = canon_yesno(dmw_nullable)
    if dmw_nullable_yesno not in ("YES","NO"):
        # leave visible but still compare if possible
        pass
    if dmw_nullable_yesno and ddl_nullable and dmw_nullable_yesno != ddl_nullable:
        flags["Nullable_Mismatch"] = "YES"
        issues.append(f"Nullable mismatch (DMW={dmw_nullable_yesno}, DDL={ddl_nullable})")
    else:
        flags["Nullable_Mismatch"] = "NO"

    # Default value: text compare after stripping quotes
    if (dmw_default or ddl_default) and (strip_quotes(dmw_default) != strip_quotes(ddl_default)):
        flags["DefaultValue_Mismatch"] = "YES"
        issues.append(f"Default mismatch (DMW={dmw_default}, DDL={ddl_default})")
    else:
        flags["DefaultValue_Mismatch"] = "NO"

    return flags, issues

def add_change_log(df):
    col_change = "Change Log (for data migration reference)"
    if col_change not in df.columns:
        df[col_change] = ""
    def _derive(row):
        lu = norm_ws(row.get("Last Updated in Sprint", ""))
        intro = norm_ws(row.get("Introduced Sprint (for data migration sprint)", "")) or norm_ws(row.get("Introduced Sprint", ""))
        if lu and intro and lu != intro:
            return f"Changed in Sprint {lu}"
        return norm_ws(row.get(col_change, ""))
    df[col_change] = df.apply(_derive, axis=1)
    return df

# ---------------------------
# Main
# ---------------------------
def main():
    ap = argparse.ArgumentParser(description="Validate DMW 'Baseline Data Model' against raw SQL DDL.")
    ap.add_argument("--dmw-xlsx", required=True, help="Path to DataMappingWorkbook xlsx")
    ap.add_argument("--sheet", default="Baseline Data Model", help="Sheet name (default: Baseline Data Model)")
    ap.add_argument("--ddl-sql", required=True, help="Path to raw SQL DDL file containing CREATE TABLE statements")
    ap.add_argument("--out", default="Baseline Data Model_output.xlsx", help="Output Excel file (default: Baseline Data Model_output.xlsx)")
    args = ap.parse_args()

    xlsx_path = Path(args.dmw_xlsx)
    ddl_path = Path(args.ddl_sql)

    # Load DMW sheet
    from patch_excel_reader import load_dmw_sheet
    df = load_dmw_sheet(xlsx_path, args.sheet)

    # Build DDL index
    ddl_text = ddl_path.read_text(encoding="utf-8", errors="ignore")
    ddl, pk_index, unique_index = build_ddl_index(ddl_text)

    # Prepare output columns
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

    # Row-wise compare
    remarks_all = []
    for idx, row in df.iterrows():
        flags, issues = compare_row(row, ddl, pk_index, unique_index)
        for k, v in flags.items():
            df.at[idx, k] = v
        # Status & remarks
        fail_flags = [k for k, v in flags.items() if v == "YES" and k not in ("Validation_Status","Validation_Remarks")]
        status = "FAIL" if any(flags[k] == "YES" for k in flags if k not in ("Validation_Status","Validation_Remarks")) else "PASS"
        df.at[idx, "Validation_Status"] = status
        df.at[idx, "Validation_Remarks"] = "; ".join(issues)

    # Sprint change log
    df = add_change_log(df)

    # Write output keeping original columns order + appended
    original_order = [c for c in pd.read_excel(xlsx_path, sheet_name=args.sheet, nrows=0).columns]
    appended = [c for c in out_cols if c not in original_order]
    final_cols = original_order + appended
    from patch_safe_export import safe_export
    safe_export(df, args.out, final_cols)
    print(f"Wrote: {args.out}")

if __name__ == "__main__":
    main()
