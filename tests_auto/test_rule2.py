#!/usr/bin/env python3
from tests_auto.common import Workdir, make_dmw_xlsx, make_ddl_sql, run_validator, read_sheet_rows, assert_any_row_has_value

def test_rule2_sprint_mismatch_requires_changelog():
    wd = Workdir("r2a_")
    try:
        dmw = wd.p("dmw.xlsx")
        ddl = wd.p("ddl.sql")
        out = wd.p("out.xlsx")

        make_dmw_xlsx(dmw, [{
            "Destination Table": "T1",
            "Destination Column Name": "C1",
            "Migrating Column": "Yes",
            "Destination Data Type": "INT",
            "Destination Nullable": "NOT NULL",
            "Transformation Logic": "copy",
            "Introduced Sprint": "S1",
            "Last Updated Sprint": "S2",
            "Change Log": "",
        }])

        make_ddl_sql(ddl, {"T1": {"C1": "INT NOT NULL"}})

        run_validator(dmw=dmw, ddl=ddl, out=out)

        rows = read_sheet_rows(out, "Baseline Data Model_output")
        assert_any_row_has_value(rows, "Rule2", "FAIL")
        assert_any_row_has_value(rows, "Validation_Status", "FAIL")
    finally:
        wd.cleanup()

def test_rule2_same_sprint_no_changelog_ok():
    wd = Workdir("r2b_")
    try:
        dmw = wd.p("dmw.xlsx")
        ddl = wd.p("ddl.sql")
        out = wd.p("out.xlsx")

        make_dmw_xlsx(dmw, [{
            "Destination Table": "T1",
            "Destination Column Name": "C1",
            "Migrating Column": "Yes",
            "Destination Data Type": "INT",
            "Destination Nullable": "NOT NULL",
            "Transformation Logic": "copy",
            "Introduced Sprint": "S1",
            "Last Updated Sprint": "S1",
            "Change Log": "",
        }])

        make_ddl_sql(ddl, {"T1": {"C1": "INT NOT NULL"}})

        run_validator(dmw=dmw, ddl=ddl, out=out)

        rows = read_sheet_rows(out, "Baseline Data Model_output")
        assert_any_row_has_value(rows, "Rule2", "PASS")
    finally:
        wd.cleanup()

if __name__ == "__main__":
    test_rule2_sprint_mismatch_requires_changelog()
    test_rule2_same_sprint_no_changelog_ok()
    print("[OK] Rule2 tests passed")
