#!/usr/bin/env python3
from tests_auto.common import Workdir, make_dmw_xlsx, make_ddl_sql, run_validator, read_sheet_rows

def test_rule7_ddl_drift_detected_in_sheet():
    wd = Workdir("r7a_")
    try:
        dmw = wd.p("dmw.xlsx")
        prev_ddl = wd.p("prev.sql")
        curr_ddl = wd.p("curr.sql")
        out = wd.p("out.xlsx")

        make_dmw_xlsx(dmw, [
            {"Destination Table": "T1", "Destination Column Name": "C1", "Migrating Column": "Yes",
             "Destination Data Type": "INT", "Destination Nullable": "NOT NULL", "Transformation Logic": "copy"},
        ])

        # prev DDL: T1.C1 INT
        make_ddl_sql(prev_ddl, {"T1": {"C1": "INT NOT NULL"}})

        # curr DDL: T1.C1 BIGINT + new column C2
        make_ddl_sql(curr_ddl, {"T1": {"C1": "BIGINT NOT NULL", "C2": "INT NULL"}})

        run_validator(dmw=dmw, ddl=curr_ddl, out=out, prev_ddl=prev_ddl)

        r7 = read_sheet_rows(out, "Rule7_DDL_Drift")
        assert len(r7) >= 2, "Expected drift rows in Rule7_DDL_Drift"

        # We expect at least one MODIFIED (C1) and one ADDED_IN_CURRENT (C2)
        issues = set(str(r[2] or "").strip() for r in r7[1:])
        assert "MODIFIED" in issues or "ADDED_IN_CURRENT" in issues, f"Expected MODIFIED/ADDED_IN_CURRENT, got {issues}"
    finally:
        wd.cleanup()

if __name__ == "__main__":
    test_rule7_ddl_drift_detected_in_sheet()
    print("[OK] Rule7 tests passed")
