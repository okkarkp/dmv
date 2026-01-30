#!/usr/bin/env python3
from tests_auto.common import Workdir, make_dmw_xlsx, make_ddl_sql, run_validator, read_sheet_rows

def test_rule3_table_details_missing_in_baseline_flagged():
    wd = Workdir("r3a_")
    try:
        dmw = wd.p("dmw.xlsx")
        ddl = wd.p("ddl.sql")
        out = wd.p("out.xlsx")

        # Baseline only references T1, but Table Details includes TEST_TABLE too
        make_dmw_xlsx(
            dmw,
            [{
                "Destination Table": "T1",
                "Destination Column Name": "C1",
                "Migrating Column": "Yes",
                "Destination Data Type": "INT",
                "Destination Nullable": "NOT NULL",
                "Transformation Logic": "copy",
            }],
            add_table_details=["T1", "TEST_TABLE"]
        )

        make_ddl_sql(ddl, {"T1": {"C1": "INT NOT NULL"}})
        run_validator(dmw=dmw, ddl=ddl, out=out)

        r3 = read_sheet_rows(out, "Rule3_Table_Mismatch")
        # Expect at least 1 mismatch row (header + something)
        assert len(r3) >= 2, f"Expected Rule3_Table_Mismatch to have rows, got {len(r3)}"
        # Verify TEST_TABLE present
        found = any(str(r[0] or "").strip().upper() == "TEST_TABLE" for r in r3[1:])
        assert found, "Expected TEST_TABLE to be flagged in Rule3_Table_Mismatch"
    finally:
        wd.cleanup()

if __name__ == "__main__":
    test_rule3_table_details_missing_in_baseline_flagged()
    print("[OK] Rule3 tests passed")
