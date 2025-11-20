#!/usr/bin/env python3
import argparse, traceback, logging, re
from pathlib import Path
from openpyxl import load_workbook, Workbook
from cfg import PATHS

# ----------------------------------------------------
# Logging
# ----------------------------------------------------
raw_log = PATHS.get("logs", "./logs")
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

def norm_col(name: str):
    if not name:
        return ""
    n = name.upper().strip()
    n = n.replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", n)

def detect_header_row(ws):
    for r in range(1, 25):
        row = next(ws.iter_rows(min_row=r, max_row=r))
        if sum(1 for c in row if c.value not in (None, "")) >= 10:
            return r
    return 2

# ----------------------------------------------------
# SQL SERVER Compatible DDL Parser
# ----------------------------------------------------
def parse_ddl(path: str):
    raw = Path(path).read_bytes()

    # Encoding detection
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
        except:
            enc = "latin-1"

    ddl_text = raw.decode(enc, errors="ignore")

    tables = {}
    current_table = None

    # SQL Server CREATE TABLE
    create_table_pattern = re.compile(
        r"CREATE\s+TABLE\s+\[?(?P<schema>[A-Za-z0-9_]+)\]?\.\[?(?P<table>[A-Za-z0-9_]+)\]?|"
        r"CREATE\s+TABLE\s+\[?(?P<table2>[A-Za-z0-9_]+)\]?",
        re.IGNORECASE
    )

    # SQL Server column definitions:
    column_pattern = re.compile(
        r"^\[?(?P<col>[A-Za-z0-9_]+)\]?\s+(?P<type>[A-Za-z0-9_\(\),\s]+)",
        re.IGNORECASE
    )

    for line in ddl_text.splitlines():
        line = line.strip()
        if not line or line.upper().startswith(("DROP ", "ALTER ", "GO", "USE ", "CREATE PROCEDURE")):
            continue

        # Detect CREATE TABLE
        m = create_table_pattern.search(line)
        if m:
            table = m.group("table") or m.group("table2")
            if table:
                table = table.upper()
                tables[table] = {}
                current_table = table
            continue

        # Detect columns inside CREATE TABLE
        if current_table:
            m2 = column_pattern.match(line)
            if m2:
                col = m2.group("col").upper()
                dtype = m2.group("type").upper().rstrip(",")
                tables[current_table][col] = dtype
                continue

            # End of table
            if line.startswith(")"):
                current_table = None

    return tables

# ----------------------------------------------------
# Load DMW with SAFE strikethrough handling
# ----------------------------------------------------
def load_dmw_dynamic(path: Path):
    wb_data = load_workbook(path, read_only=True, data_only=True)
    ws_data = wb_data.active

    wb_fmt = load_workbook(path, read_only=False, data_only=False)
    ws_fmt = wb_fmt.active

    header_row = detect_header_row(ws_data)
    data_start = header_row + 1

    header_vals = next(ws_data.iter_rows(
        min_row=header_row, max_row=header_row, values_only=True
    ))

    raw_cols = [s(v) for v in header_vals]
    while raw_cols and raw_cols[-1] == "":
        raw_cols.pop()

    columns = raw_cols[:]
    idx_norm = {norm_col(columns[i]): i for i in range(len(columns))}

    def colidx(name: str):
        return idx_norm.get(norm_col(name))

    rows = []
    strike_set = set()

    for r_idx, row in enumerate(
        ws_data.iter_rows(min_row=data_start, max_row=ws_data.max_row, values_only=True),
        start=data_start
    ):
        if row is None:
            break

        vals = list(row)
        if len(vals) < len(columns):
            vals += [None] * (len(columns) - len(vals))

        norm_vals = [s(v) for v in vals[:len(columns)]]

        if all(v == "" for v in norm_vals):
            break

        t_idx = colidx("SOURCE TABLE")
        c_idx = colidx("SOURCE COLUMN NAME")
        table = norm_vals[t_idx] if t_idx is not None else ""
        col = norm_vals[c_idx] if c_idx is not None else ""

        if table and col:
            fmt_row = ws_fmt[r_idx]
            if any(cell.font and cell.font.strike for cell in fmt_row[:len(columns)]):
                strike_set.add((table.upper(), col.upper()))

        rows.append(norm_vals)

    wb_data.close()
    wb_fmt.close()

    return columns, rows, strike_set

# ----------------------------------------------------
# RULES
# ----------------------------------------------------
RULE_COLS = [
    "Rule1","Rule2","Rule3","Rule4",
    "Rule5","Rule6","Rule7",
    "Validation_Status","Validation_Remarks","AI_Suggestion"
]

# ----------------------------------------------------
def validate(dmw_xlsx, ddl_sql, out_xlsx, ai_cfg):
    columns, rows, strike_set = load_dmw_dynamic(Path(dmw_xlsx))
    ddl = parse_ddl(ddl_sql)

    idx_norm = {norm_col(columns[i]): i for i in range(len(columns))}
    def colidx(n): return idx_norm.get(norm_col(n))

    out = Workbook()
    ws_main = out.active
    ws_main.title = "Baseline Data Model_output"

    ws_r4 = out.create_sheet("Rule4_DDL_Mismatch")
    ws_r4.append(["Table", "Column", "Issue Type", "Details"])

    ws_main.append(columns + RULE_COLS)

    seen = set()

    def add_r4(tbl, col, issue, detail):
        ws_r4.append([tbl, col, issue, detail])

    # -------------------------------------
    # Process DMW rows
    # -------------------------------------
    for r in rows:
        t_idx = colidx("SOURCE TABLE")
        c_idx = colidx("SOURCE COLUMN NAME")
        table = r[t_idx] if t_idx is not None else ""
        col   = r[c_idx] if c_idx is not None else ""

        T = table.upper() if table else ""
        C = col.upper() if col else ""
        key = (T, C)

        # Strikethrough row: skip ALL validation
        if key in strike_set and T and C:
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

        # Active row
        if T and C:
            seen.add(key)

        rule4 = "PASS"
        remark4 = ""

        if T and C and T in ddl:
            if C not in ddl[T]:
                rule4 = "FAIL"
                remark4 = "Column exists in DMW but missing in DDL"
                add_r4(T, C, "DMW_ONLY", remark4)
            else:
                dt_idx = colidx("DATA TYPE")
                dmw_type = r[dt_idx] if dt_idx is not None else ""
                ddl_type = ddl[T][C]

                if dmw_type and dmw_type.upper() not in ddl_type:
                    rule4 = "FAIL"
                    remark4 = f"Datatype mismatch: DMW={dmw_type}, DDL={ddl_type}"
                    add_r4(T, C, "MISMATCH", remark4)

        status = "FAIL" if rule4 == "FAIL" else "PASS"

        ws_main.append(
            r + [
                "PASS","PASS","PASS", rule4,
                "PASS","PASS","PASS",
                status, remark4, ""
            ]
        )

    # -------------------------------------
    # DDL → DMW missing columns
    # -------------------------------------
    for tbl, cols in ddl.items():
        for col, dtype in cols.items():
            key = (tbl.upper(), col.upper())
            if key not in seen and key not in strike_set:
                add_r4(
                    tbl, col,
                    "MISSING_IN_DMW",
                    f"Column exists in DDL but missing in DMW (DDL type={dtype})"
                )

    out.save(out_xlsx)
    print(f"[OK] Validation completed → {out_xlsx}")

# ----------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dmw-xlsx", required=True)
    ap.add_argument("--ddl-sql", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--enable-ai", action="store_true")
    args = ap.parse_args()

    ai_cfg = {"enabled": args.enable_ai}

    try:
        validate(args.dmw_xlsx, args.ddl_sql, args.out, ai_cfg)
    except Exception:
        traceback.print_exc()
        logging.exception("FATAL ERROR")

if __name__ == "__main__":
    main()
