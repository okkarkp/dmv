#!/usr/bin/env python3
from tests_auto.common import (
    Workdir, make_dmw_xlsx, make_ddl_sql, run_validator,
    read_sheet_rows, assert_sheet_has_issue, assert_any_row_has_value
)

def test_rule4_dmw_only_flagged_and_baseline_fail():
    wd = Workdir("r4a_")
    try:
        dmw = wd.p("dmw.xlsx")
        ddl = wd.p("ddl.sql")
        out = wd.p("out.xlsx")

        # DMW has C2 but DDL only has C1 -> DMW_ONLY mismatch on (T1,C2)
        make_dmw_xlsx(dmw, [
            {"Destination Table": "T1", "Destination Column Name": "C2", "Migrating Column": "Yes",
             "Destination Data Type": "INT", "Destination Nullable": "NOT NULL", "Transformation Logic": "copy"},
        ])

        make_ddl_sql(ddl, {"T1": {"C1": "INT NOT NULL"}})

        run_validator(dmw=dmw, ddl=ddl, out=out)

        assert_sheet_has_issue(out, "Rule4_DDL_Mismatch", "Issue", "DMW_ONLY")

        base = read_sheet_rows(out, "Baseline Data Model_output")
        assert_any_row_has_value(base, "Rule4", "FAIL")
        assert_any_row_has_value(base, "Validation_Status", "FAIL")
    finally:
        wd.cleanup()

def test_rule4_nullable_mismatch_flagged():
    wd = Workdir("r4b_")
    try:
        dmw = wd.p("dmw.xlsx")
        ddl = wd.p("ddl.sql")
        out = wd.p("out.xlsx")

        # Same column exists but nullable differs: DMW NOT NULL, DDL NULL
        make_dmw_xlsx(dmw, [
            {"Destination Table": "T1", "Destination Column Name": "C1", "Migrating Column": "Yes",
             "Destination Data Type": "INT", "Destination Nullable": "NOT NULL", "Transformation Logic": "copy"},
        ])
        make_ddl_sql(ddl, {"T1": {"C1": "INT NULL"}})

        run_validator(dmw=dmw, ddl=ddl, out=out)

        assert_sheet_has_issue(out, "Rule4_DDL_Mismatch", "Issue", "NULLABLE_MISMATCH")
        base = read_sheet_rows(out, "Baseline Data Model_output")
        assert_any_row_has_value(base, "Rule4", "FAIL")
    finally:
        wd.cleanup()

def test_rule4_type_mismatch_flagged():
    wd = Workdir("r4c_")
    try:
        dmw = wd.p("dmw.xlsx")
        ddl = wd.p("ddl.sql")
        out = wd.p("out.xlsx")

        make_dmw_xlsx(dmw, [
            {"Destination Table": "T1", "Destination Column Name": "C1", "Migrating Column": "Yes",
             "Destination Data Type": "INT", "Destination Nullable": "NOT NULL", "Transformation Logic": "copy"},
        ])
        make_ddl_sql(ddl, {"T1": {"C1": "BIGINT NOT NULL"}})

        run_validator(dmw=dmw, ddl=ddl, out=out)

        assert_sheet_has_issue(out, "Rule4_DDL_Mismatch", "Issue", "TYPE_MISMATCH")
        base = read_sheet_rows(out, "Baseline Data Model_output")
        assert_any_row_has_value(base, "Rule4", "FAIL")
    finally:
        wd.cleanup()

def test_rule4_missing_in_dmw_creates_synthetic_fail_row():
    wd = Workdir("r4d_")
    try:
        dmw = wd.p("dmw.xlsx")
        ddl = wd.p("ddl.sql")
        out = wd.p("out.xlsx")

        # Table appears in DMW (C1), but DDL has extra C2 -> MISSING_IN_DMW for C2
        make_dmw_xlsx(dmw, [
            {"Destination Table": "T1", "Destination Column Name": "C1", "Migrating Column": "Yes",
             "Destination Data Type": "INT", "Destination Nullable": "NOT NULL", "Transformation Logic": "copy"},
        ])
        make_ddl_sql(ddl, {"T1": {"C1": "INT NOT NULL", "C2": "INT NOT NULL"}})

        run_validator(dmw=dmw, ddl=ddl, out=out)

        assert_sheet_has_issue(out, "Rule4_DDL_Mismatch", "Issue", "MISSING_IN_DMW")

        base = read_sheet_rows(out, "Baseline Data Model_output")
        # Synthetic row should have Rule4 FAIL and Validation_Status FAIL somewhere
        assert_any_row_has_value(base, "Rule4", "FAIL")
        assert_any_row_has_value(base, "Validation_Status", "FAIL")
    finally:
        wd.cleanup()

if __name__ == "__main__":
    test_rule4_dmw_only_flagged_and_baseline_fail()
    test_rule4_nullable_mismatch_flagged()
    test_rule4_type_mismatch_flagged()
    test_rule4_missing_in_dmw_creates_synthetic_fail_row()
    print("[OK] Rule4 tests passed")
