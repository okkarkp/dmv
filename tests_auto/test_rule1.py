#!/usr/bin/env python3
from pathlib import Path
from tests_auto.common import Workdir, make_dmw_xlsx, make_ddl_sql, run_validator, read_sheet_rows, assert_any_row_has_value

def test_rule1_migrating_no_reason_fails():
    wd = Workdir("r1a_")
    try:
        dmw = wd.p("dmw.xlsx")
        ddl = wd.p("ddl.sql")
        out = wd.p("out.xlsx")

        # Migrating Column = No but Reason blank -> Rule1 FAIL
        make_dmw_xlsx(dmw, [{
            "Source Table": "S1",
            "Source Column Name": "A",
            "Destination Table": "T1",
            "Destination Column Name": "C1",
            "Migrating Column": "No",
            "Reason for Not Migrating": "",
        }])

        make_ddl_sql(ddl, {"T1": {"C1": "INT NOT NULL"}})

        run_validator(dmw=dmw, ddl=ddl, out=out)

        rows = read_sheet_rows(out, "Baseline Data Model_output")
        assert_any_row_has_value(rows, "Rule1", "FAIL")
        assert_any_row_has_value(rows, "Validation_Status", "FAIL")
    finally:
        wd.cleanup()

def test_rule1_migrating_yes_missing_dest_fields_fails():
    wd = Workdir("r1b_")
    try:
        dmw = wd.p("dmw.xlsx")
        ddl = wd.p("ddl.sql")
        out = wd.p("out.xlsx")

        # Migrating = Yes but missing dtype/nullable/transform -> FAIL
        make_dmw_xlsx(dmw, [{
            "Destination Table": "T1",
            "Destination Column Name": "C1",
            "Migrating Column": "Yes",
            "Destination Data Type": "",
            "Destination Data Length": "",
            "Destination Nullable": "",
            "Transformation Logic": "",
        }])

        make_ddl_sql(ddl, {"T1": {"C1": "INT NOT NULL"}})

        run_validator(dmw=dmw, ddl=ddl, out=out)

        rows = read_sheet_rows(out, "Baseline Data Model_output")
        assert_any_row_has_value(rows, "Rule1", "FAIL")
        assert_any_row_has_value(rows, "Validation_Status", "FAIL")
    finally:
        wd.cleanup()

def test_rule1_migrating_yes_complete_passes():
    wd = Workdir("r1c_")
    try:
        dmw = wd.p("dmw.xlsx")
        ddl = wd.p("ddl.sql")
        out = wd.p("out.xlsx")

        make_dmw_xlsx(dmw, [{
            "Destination Table": "T1",
            "Destination Column Name": "C1",
            "Migrating Column": "Yes",
            "Destination Data Type": "INT",
            "Destination Data Length": "",
            "Destination Nullable": "NOT NULL",
            "Transformation Logic": "copy",
        }])

        make_ddl_sql(ddl, {"T1": {"C1": "INT NOT NULL"}})

        run_validator(dmw=dmw, ddl=ddl, out=out)

        rows = read_sheet_rows(out, "Baseline Data Model_output")
        assert_any_row_has_value(rows, "Rule1", "PASS")
    finally:
        wd.cleanup()

if __name__ == "__main__":
    test_rule1_migrating_no_reason_fails()
    test_rule1_migrating_yes_missing_dest_fields_fails()
    test_rule1_migrating_yes_complete_passes()
    print("[OK] Rule1 tests passed")
