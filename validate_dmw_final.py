#!/usr/bin/env python3
import argparse, traceback, logging, re
from pathlib import Path
from openpyxl import load_workbook, Workbook
from cfg import PATHS

# ----------------------------------------------------
# Logging setup
# ----------------------------------------------------
raw_log = PATHS.get("logs", "./logs")
# When running outside Docker (/app), avoid permission issues
LOG_DIR = Path("./logs") if str(raw_log).startswith("/app") else Path(raw_log)
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "dmw_validator.log"

logging.basicConfig(
    filename=str(LOG_PATH),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def s(v):
    return "" if v is None else str(v).strip()

def norm_col(name: str) -> str:
    if not name:
        return ""
    n = str(name).upper().strip()
    n = n.replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", n)

def detect_header_row(ws):
    """
    Try to find the header row by looking for a row with many non-empty cells.
    """
    for r in range(1, 30):
        row = next(ws.iter_rows(min_row=r, max_row=r))
        if sum(1 for c in row if c.value not in (None, "")) >= 10:
            return r
    return 2

# ----------------------------------------------------
# Dynamic SQL Server / Azure SQL DDL parser (Option A)
# ----------------------------------------------------
def parse_ddl(path: str):
    """
    Dynamic SQL Server / Azure SQL DDL parser.

    - Handles:
      * CREATE TABLE [schema].[Table] ( ... )
      * Temporal tables (SYSTEM_VERSIONING, PERIOD FOR SYSTEM_TIME)
      * GENERATED ALWAYS AS ROW START / ROW END
      * IF EXISTS / DROP TABLE wrappers in the same file
    - Only extracts CREATE TABLE column definitions.
    """

    raw = Path(path).read_bytes()

    # Basic encoding detection
    if raw.startswith(b"\xff\xfe"):
        enc = "utf-16-le"
    elif raw.startswith(b"\xfe\xff"):
        enc = "utf-16-be"
    elif raw.startswith(b"\xef\xbb\xbf"):
        enc = "utf-8-sig"
    else:
        try:
            raw.decode("utf-8")
            enc = "utf-8"
        except UnicodeDecodeError:
            enc = "latin-1"

    ddl_text = raw.decode(enc, errors="ignore")

    tables = {}

    # Match "CREATE TABLE [schema].[TableName](" or "CREATE TABLE [TableName]("
    create_re = re.compile(
        r"CREATE\s+TABLE\s+(?:\[(?P<schema>\w+)\]\.)?\[(?P<table>\w+)\]\s*\(",
        re.IGNORECASE
    )

    # Column definition inside the parentheses block:
    #    NOT NULL,
    #    GENERATED ALWAYS AS ROW START NOT NULL,
    col_re = re.compile(
        r"^\s*\[(?P<col>\w+)\]\s+\[?(?P<type>[A-Za-z0-9_]+(?:\s*\([^)]*\))?)\]?",
        re.IGNORECASE
    )

    for m in create_re.finditer(ddl_text):
        table_name = m.group("table").upper()
        # Starting position is right after the "(" matched by create_re
        start = m.end()
        depth = 1
        i = start

        # Walk forward to find the matching closing parenthesis at depth 0
        while i < len(ddl_text) and depth > 0:
            ch = ddl_text[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            i += 1

        # Extract everything inside the CREATE TABLE (...) block
        block = ddl_text[start:i-1]

        # Initialize table entry
        cols = {}
        for line in block.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            up = stripped.upper()

            # Skip constraint / index / temporal lines
            if up.startswith((
                "CONSTRAINT",
                "PRIMARY KEY",
                "FOREIGN KEY",
                "CHECK",
                "UNIQUE",
                "INDEX",
                "PERIOD FOR SYSTEM_TIME",
                "WITH"
            )):
                continue

            # Try column match
            m2 = col_re.match(stripped)
            if m2:
                col = m2.group("col").upper()
                dtype = m2.group("type").upper()
                cols[col] = dtype
                continue

        tables[table_name] = cols

    return tables

# ----------------------------------------------------
# Load DMW with dynamic headers + strikethrough detection
# ----------------------------------------------------
def load_dmw_dynamic(path: Path):
    # Data-only workbook for values
    wb_data = load_workbook(path, read_only=True, data_only=True)
    ws_data = wb_data.active

    # Full workbook for formatting (strikethrough)
    wb_fmt = load_workbook(path, read_only=False, data_only=False)
    ws_fmt = wb_fmt.active

    header_row = detect_header_row(ws_data)
    data_start = header_row + 1

    header_vals = next(
        ws_data.iter_rows(min_row=header_row, max_row=header_row, values_only=True)
    )
    columns = [s(v) for v in header_vals]
    # trim trailing blanks
    while columns and columns[-1] == "":
        columns.pop()

    idx_norm = {norm_col(columns[i]): i for i in range(len(columns))}
    def colidx(name: str):
        return idx_norm.get(norm_col(name))

    rows = []
    strike_src = set()

    for r_idx, row in enumerate(
        ws_data.iter_rows(min_row=data_start, max_row=ws_data.max_row, values_only=True),
        start=data_start
    ):
        if row is None:
            break
        vals = [s(v) for v in row[:len(columns)]]
        if all(v == "" for v in vals):
            break

        # detect strikethrough via SOURCE TABLE + SOURCE COLUMN NAME
        st_i = colidx("SOURCE TABLE")
        sc_i = colidx("SOURCE COLUMN NAME")
        st = vals[st_i] if st_i is not None else ""
        sc = vals[sc_i] if sc_i is not None else ""
        if st and sc:
            fmt_row = ws_fmt[r_idx]
            if any(c.font and c.font.strike for c in fmt_row[:len(columns)]):
                strike_src.add((st.upper(), sc.upper()))

        rows.append(vals)

    wb_data.close()
    wb_fmt.close()
    return columns, rows, strike_src

# ----------------------------------------------------
# Main validation (set-based Rule4, strikethrough aware)
# ----------------------------------------------------
def validate(dmw_xlsx, ddl_sql, out_xlsx, ai_cfg):
    columns, rows, strike_src = load_dmw_dynamic(Path(dmw_xlsx))
    ddl = parse_ddl(ddl_sql)

    idx_norm = {norm_col(columns[i]): i for i in range(len(columns))}
    def colidx(name: str):
        return idx_norm.get(norm_col(name))

    src_t_idx = colidx("SOURCE TABLE")
    src_c_idx = colidx("SOURCE COLUMN NAME")
    dest_t_idx = colidx("DESTINATION TABLE")
    dest_c_idx = colidx("DESTINATION COLUMN NAME")

    # Destination Data Type index (first DATA TYPE after destination table)
    data_type_indices = [i for i, col in enumerate(columns) if norm_col(col) == "DATA TYPE"]
    dest_dt_idx = None
    if dest_t_idx is not None and data_type_indices:
        for i in data_type_indices:
            if i > dest_t_idx:
                dest_dt_idx = i
                break
        if dest_dt_idx is None and data_type_indices:
            dest_dt_idx = data_type_indices[-1]

    out_wb = Workbook()
    ws_main = out_wb.active
    ws_main.title = "Baseline Data Model_output"

    ws_r4 = out_wb.create_sheet("Rule4_DDL_Mismatch")
    ws_r4.append(["Table", "Column", "Issue", "Details"])

    RULE_COLS = [
        "Rule1","Rule2","Rule3","Rule4",
        "Rule5","Rule6","Rule7",
        "Validation_Status","Validation_Remarks","AI_Suggestion"
    ]
    ws_main.append(columns + RULE_COLS)

    # ------------------------------------------------
    # 1) Build set of DMW destination columns per table
    # ------------------------------------------------
    dmw_dest_map = {}    # TABLE → set(columns)
    striked_dest = set() # (TABLE, COLUMN) cancelled by strikethrough

    for r in rows:
        ST = r[src_t_idx].upper() if src_t_idx is not None and r[src_t_idx] else ""
        SC = r[src_c_idx].upper() if src_c_idx is not None and r[src_c_idx] else ""
        src_key = (ST, SC)

        DT = r[dest_t_idx].upper() if dest_t_idx is not None and r[dest_t_idx] else ""
        DC = r[dest_c_idx].upper() if dest_c_idx is not None and r[dest_c_idx] else ""

        if src_key in strike_src:
            # cancel this destination too
            if DT and DC:
                striked_dest.add((DT, DC))
            continue

        if not DT or not DC:
            continue

        dmw_dest_map.setdefault(DT, set()).add(DC)

    # ------------------------------------------------
    # 2) Row-by-row main sheet (Rule4 initially PASS/N/A)
    #    Actual mismatches discovered in Rule4 sheet
    # ------------------------------------------------
    for r in rows:
        ST = r[src_t_idx].upper() if src_t_idx is not None and r[src_t_idx] else ""
        SC = r[src_c_idx].upper() if src_c_idx is not None and r[src_c_idx] else ""
        src_key = (ST, SC)

        DT = r[dest_t_idx].upper() if dest_t_idx is not None and r[dest_t_idx] else ""
        DC = r[dest_c_idx].upper() if dest_c_idx is not None and r[dest_c_idx] else ""

        # 2.1 Strikethrough → skip all rules
        if src_key in strike_src:
            ws_main.append(
                r + [
                    "N/A","N/A","N/A","N/A",
                    "N/A","N/A","N/A",
                    "N/A",
                    "Strikethrough: field cancelled by Apps team",
                    ""
                ]
            )
            continue

        # 2.2 Destination missing → skip Rule4 only (your Option B)
        if not DT or not DC:
            ws_main.append(
                r + [
                    "PASS","PASS","PASS","N/A",
                    "PASS","PASS","PASS",
                    "N/A",
                    "No Destination mapping — Rule4 skipped",
                    ""
                ]
            )
            continue

        # 2.3 Normal mapped row – tentatively mark Rule4 PASS here
        #     We will flip to FAIL later if mismatch exists.
        ws_main.append(
            r + [
                "PASS","PASS","PASS","PASS",
                "PASS","PASS","PASS",
                "PASS",
                "",
                ""
            ]
        )

    # ------------------------------------------------
    # 3) Set-based Rule4: DMW ↔ DDL (populate Rule4_DDL_Mismatch sheet)
    # ------------------------------------------------
    for tbl, ddl_cols in ddl.items():
        tbl_upper = tbl.upper()
        ddl_set = set(ddl_cols.keys())
        dmw_set = dmw_dest_map.get(tbl_upper, set())

        # exclude cancelled destinations (strikethrough)
        dmw_set = {
            c for c in dmw_set
            if (tbl_upper, c) not in striked_dest
        }

        # 3A) DMW → DDL (DMW_ONLY)
        for col in sorted(dmw_set):
            if col not in ddl_set:
                ws_r4.append([
                    tbl_upper,
                    col,
                    "DMW_ONLY",
                    "Destination column appears in DMW but not in DDL"
                ])

        # 3B) DDL → DMW (MISSING_IN_DMW)
        for col in sorted(ddl_set):
            if col not in dmw_set:
                ws_r4.append([
                    tbl_upper,
                    col,
                    "MISSING_IN_DMW",
                    f"Column exists in DDL but not mapped in DMW Destination (DDL type={ddl_cols[col]})"
                ])

    # ------------------------------------------------
    # 4) Propagate Rule4 mismatches back to Baseline sheet
    # ------------------------------------------------
    mismatch_set = set()
    for row in ws_r4.iter_rows(min_row=2, values_only=True):
        tbl, col, issue, details = row
        if not tbl or not col:
            continue
        mismatch_set.add((str(tbl).upper(), str(col).upper()))

    # If we can't locate dest indices, just leave rows as-is
    if dest_t_idx is not None and dest_c_idx is not None:
        # Read all data rows from main sheet
        all_rows = list(ws_main.iter_rows(min_row=2, values_only=True))
        # Clear them (keep header)
        ws_main.delete_rows(2, ws_main.max_row)

        for r in all_rows:
            # r = data columns + 10 rule/remarks/ai columns
            data_cols = list(r[:-10])
            rule1, rule2, rule3, rule4_val, rule5, rule6, rule7, status, remarks, ai = r[-10:]

            DT = data_cols[dest_t_idx].upper() if dest_t_idx < len(data_cols) and data_cols[dest_t_idx] else ""
            DC = data_cols[dest_c_idx].upper() if dest_c_idx < len(data_cols) and data_cols[dest_c_idx] else ""

            # If Rule4 is N/A (strikethrough or no-destination), keep as-is
            if rule4_val == "N/A":
                new_r4 = "N/A"
                new_status = status
                new_remarks = remarks
            else:
                # If this (table, column) is in mismatch_set → FAIL
                if (DT, DC) in mismatch_set:
                    new_r4 = "FAIL"
                    new_status = "FAIL"
                    # If there is already some remark, append; else set fresh
                    if remarks:
                        new_remarks = f"{remarks} | Rule4 mismatch – see Rule4_DDL_Mismatch"
                    else:
                        new_remarks = "Rule4 mismatch – see Rule4_DDL_Mismatch"
                else:
                    new_r4 = "PASS"
                    new_status = status
                    new_remarks = remarks

            ws_main.append(
                data_cols + [
                    rule1, rule2, rule3, new_r4,
                    rule5, rule6, rule7,
                    new_status,
                    new_remarks,
                    ai
                ]
            )

    out_wb.save(out_xlsx)
    print(f"[OK] Validation completed → {out_xlsx}")
    logging.info(f"Validation completed → {out_xlsx}")

# ----------------------------------------------------
# CLI entry point
# ----------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dmw-xlsx", required=True)
    ap.add_argument("--ddl-sql", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--enable-ai", action="store_true")
    # for compatibility with older web UI even if we ignore them
    ap.add_argument("--prev-dmw", default=None)
    ap.add_argument("--prev-ddl", default=None)

    args = ap.parse_args()

    ai_cfg = {
        "enabled": args.enable_ai
    }

    try:
        validate(args.dmw_xlsx, args.ddl_sql, args.out, ai_cfg)
    except Exception:
        traceback.print_exc()
        logging.exception("FATAL ERROR")

if __name__ == "__main__":
    main()
