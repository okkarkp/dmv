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

def norm_col(name: str) -> str:
    if not name:
        return ""
    n = str(name).upper().strip().replace("_"," ").replace("-"," ")
    return re.sub(r"\s+"," ",n)

def is_na(v: str) -> bool:
    if v is None:
        return True
    t = s(v).upper()
    return t in ("", "NA", "N/A", "NIL")

def detect_header_row(ws):
    """Heuristic: first row with >= 10 non-empty cells."""
    for r in range(1, 30):
        row = next(ws.iter_rows(min_row=r, max_row=r))
        if sum(1 for c in row if c.value not in (None, "")) >= 10:
            return r
    return 2

# ----------------------------------------------------
# DDL PARSER (SQL Server / Azure SQL)
# ----------------------------------------------------
def parse_ddl(path: str):
    raw = Path(path).read_bytes()
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

    create_re = re.compile(
        r"CREATE\s+TABLE\s+(?:\[(?P<schema>\w+)\]\.)?\[(?P<table>\w+)\]\s*\(",
        re.IGNORECASE
    )

    col_re = re.compile(
        r"^\s*\[(?P<col>\w+)\]\s+\[?(?P<type>[A-Za-z0-9_]+(?:\s*\([^)]*\))?)\]?",
        re.IGNORECASE
    )

    for m in create_re.finditer(ddl_text):
        tbl = m.group("table").upper()
        start = m.end()
        depth = 1
        i = start
        while i < len(ddl_text) and depth > 0:
            ch = ddl_text[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            i += 1

        block = ddl_text[start:i-1]
        cols = {}

        for line in block.splitlines():
            l = line.strip()
            if not l:
                continue
            up = l.upper()
            if up.startswith((
                "CONSTRAINT","PRIMARY KEY","FOREIGN KEY","CHECK",
                "UNIQUE","INDEX","PERIOD FOR SYSTEM_TIME","WITH"
            )):
                continue
            m2 = col_re.match(l)
            if m2:
                c = m2.group("col").upper()
                t = m2.group("type").upper()
                cols[c] = t

        tables[tbl] = cols

    return tables

# ----------------------------------------------------
# MAIN VALIDATION (memory-light, single-pass over DMW)
# ----------------------------------------------------
def validate(dmw_xlsx, ddl_sql, out_xlsx, ai_cfg):
    # 1) Load DMW in read-only mode (no styles → fast, low RAM)
    wb_data = load_workbook(dmw_xlsx, read_only=True, data_only=True)
    ws_data = wb_data.active

    header_row = detect_header_row(ws_data)
    data_start = header_row + 1

    header_cells = next(
        ws_data.iter_rows(min_row=header_row, max_row=header_row, values_only=True)
    )
    columns = [s(v) for v in header_cells]
    while columns and columns[-1] == "":
        columns.pop()

    idx = {norm_col(columns[i]): i for i in range(len(columns))}
    def colidx(name): return idx.get(norm_col(name))

    st_i = colidx("SOURCE TABLE")
    sc_i = colidx("SOURCE COLUMN NAME")
    dt_i = colidx("DESTINATION TABLE")
    dc_i = colidx("DESTINATION COLUMN NAME")

    # 2) Prepare output workbook
    out_wb = Workbook()
    ws_main = out_wb.active
    ws_main.title = "Baseline Data Model_output"

    ws_r4 = out_wb.create_sheet("Rule4_DDL_Mismatch")
    ws_r4.append(["Table","Column","Issue","Details"])

    RULE_COLS = [
        "Rule1","Rule2","Rule3","Rule4",
        "Rule5","Rule6","Rule7",
        "Validation_Status","Validation_Remarks","AI_Suggestion"
    ]
    ws_main.append(columns + RULE_COLS)

    # dest_map: DEST_TABLE -> set(DEST_COLUMNS) from DMW
    dest_map = {}

    # 3) Single pass over DMW rows
    for row_cells in ws_data.iter_rows(
        min_row=data_start, max_row=ws_data.max_row, values_only=True
    ):
        if row_cells is None:
            break
        vals = [s(v) for v in row_cells[:len(columns)]]
        if all(v == "" for v in vals):
            break  # reached end of data

        ST = vals[st_i] if st_i is not None and st_i < len(vals) else ""
        SC = vals[sc_i] if sc_i is not None and sc_i < len(vals) else ""
        DT = vals[dt_i] if dt_i is not None and dt_i < len(vals) else ""
        DC = vals[dc_i] if dc_i is not None and dc_i < len(vals) else ""

        source_na = is_na(ST) and is_na(SC)
        dest_na   = is_na(DT) and is_na(DC)

        # Case A – helper row: both source and destination NA
        if source_na and dest_na:
            ws_main.append(vals + [
                "N/A","N/A","N/A","N/A",
                "N/A","N/A","N/A",
                "N/A",
                "Source Table is NA — not applicable",
                ""
            ])
            continue

        # Case B – destination missing / NA → Rule4 N/A, others PASS
        if is_na(DT) or is_na(DC):
            ws_main.append(vals + [
                "PASS","PASS","PASS","N/A",
                "PASS","PASS","PASS",
                "N/A",
                "No Destination mapping — Rule4 skipped",
                ""
            ])
            # Do NOT add to dest_map
            continue

        # Case C – normal row (includes Source NA but Destination exists)
        ws_main.append(vals + [
            "PASS","PASS","PASS","PASS",
            "PASS","PASS","PASS",
            "PASS",
            "",
            ""
        ])

        # Build destination map (destination-driven, source can be NA)
        tblU = DT.upper()
        colU = DC.upper()
        dest_map.setdefault(tblU, set()).add(colU)

    wb_data.close()

    # 4) Parse DDL and build Rule4 mismatches
    ddl = parse_ddl(ddl_sql)
    for tbl, ddl_cols in ddl.items():
        tblU = tbl.upper()
        ddl_set = set(ddl_cols.keys())
        dmw_set = dest_map.get(tblU, set())

        # DMW_ONLY
        for col in sorted(dmw_set - ddl_set):
            ws_r4.append([
                tblU, col,
                "DMW_ONLY",
                "Destination column appears in DMW but not in DDL"
            ])

        # MISSING_IN_DMW (only if table appears in DMW at all)
        if dmw_set:
            for col in sorted(ddl_set - dmw_set):
                ws_r4.append([
                    tblU, col,
                    "MISSING_IN_DMW",
                    f"Column exists in DDL but not mapped in DMW (DDL type={ddl_cols[col]})"
                ])

    # 5) Propagate Rule4 FAIL back into Baseline
    mismatch = set()
    for row in ws_r4.iter_rows(min_row=2, values_only=True):
        t, c, issue, details = row
        if not t or not c:
            continue
        mismatch.add((str(t).upper(), str(c).upper()))

    if dt_i is not None and dc_i is not None:
        all_rows = list(ws_main.iter_rows(min_row=2, values_only=True))
        ws_main.delete_rows(2, ws_main.max_row)

        for r in all_rows:
            data = list(r[:-10])
            r1, r2, r3, r4_val, r5, r6, r7, status, remarks, ai = r[-10:]

            DT = s(data[dt_i]) if dt_i < len(data) else ""
            DC = s(data[dc_i]) if dc_i < len(data) else ""
            key = (DT.upper(), DC.upper())

            if r4_val == "N/A":
                new_r4 = "N/A"
                new_status = status
                new_remarks = remarks
            else:
                if key in mismatch:
                    new_r4 = "FAIL"
                    new_status = "FAIL"
                    new_remarks = (
                        f"{remarks} | Rule4 mismatch – see Rule4_DDL_Mismatch"
                        if remarks else
                        "Rule4 mismatch – see Rule4_DDL_Mismatch"
                    )
                else:
                    new_r4 = "PASS"
                    new_status = status
                    new_remarks = remarks

            ws_main.append(
                data + [r1, r2, r3, new_r4, r5, r6, r7, new_status, new_remarks, ai]
            )

    out_wb.save(out_xlsx)
    print(f"[OK] Validation completed → {out_xlsx}")
    logging.info(f"Validation completed → {out_xlsx}")

# ----------------------------------------------------
# CLI
# ----------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dmw-xlsx", required=True)
    ap.add_argument("--ddl-sql", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--enable-ai", action="store_true")
    ap.add_argument("--prev-dmw", default=None)
    ap.add_argument("--prev-ddl", default=None)

    args = ap.parse_args()
    ai_cfg = {"enabled": args.enable_ai}

    try:
        validate(args.dmw_xlsx, args.ddl_sql, args.out, ai_cfg)
    except Exception:
        traceback.print_exc()
        logging.exception("FATAL ERROR")

if __name__ == "__main__":
    main()
