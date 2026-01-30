#!/usr/bin/env python3
from tests_auto.common import Workdir, make_dmw_xlsx, make_ddl_sql, run_validator, read_sheet_rows, assert_any_row_has_value

def test_rule6_dmw_drift_added_detected_and_baseline_marked():
    wd = Workdir("r6a_")
    try:
        prev = wd.p("prev.xlsx")
        curr = wd.p("curr.xlsx")
        ddl = wd.p("ddl.sql")
        out = wd.p("out.xlsx")

        # prev has T1.C1
        make_dmw_xlsx(prev, [
            {"Destination Table": "T1", "Destination Column Name": "C1"},
        ])

        # curr has T1.C1 and T1.C2 -> C2 is ADDED_IN_CURRENT
        make_dmw_xlsx(curr, [
            {"Destination Table": "T1", "Destination Column Name": "C1", "Migrating Column": "Yes",
             "Destination Data Type": "INT", "Destination Nullable": "NOT NULL", "Transformation Logic": "copy"},
            {"Destination Table": "T1", "Destination Column Name": "C2", "Migrating Column": "Yes",
             "Destination Data Type": "INT", "Destination Nullable": "NOT NULL", "Transformation Logic": "copy"},
        ])

        make_ddl_sql(ddl, {"T1": {"C1": "INT NOT NULL", "C2": "INT NOT NULL"}})

        run_validator(dmw=curr, ddl=ddl, out=out, prev_dmw=prev)

        r6 = read_sheet_rows(out, "Rule6_DMW_Drift")
        assert len(r6) >= 2, "Expected drift rows in Rule6_DMW_Drift"
        found_added = any(str(r[2] or "").strip() == "ADDED_IN_CURRENT" for r in r6[1:])
        assert found_added, "Expected ADDED_IN_CURRENT in Rule6_DMW_Drift"

        base = read_sheet_rows(out, "Baseline Data Model_output")
        # Your implementation marks Rule6 as FAIL for drifted columns and propagates Validation_Status FAIL
        assert_any_row_has_value(base, "Rule6", "FAIL")
        assert_any_row_has_value(base, "Validation_Status", "FAIL")
    finally:
        wd.cleanup()

if __name__ == "__main__":
    test_rule6_dmw_drift_added_detected_and_baseline_marked()
    print("[OK] Rule6 tests passed")
