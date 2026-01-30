#!/usr/bin/env python3
from tests_auto.common import Workdir, make_dmw_xlsx, make_ddl_sql, run_validator, read_sheet_rows

def test_rule5_reference_subset_of_master():
    wd = Workdir("r5a_")
    try:
        master = wd.p("master.xlsx")
        ref = wd.p("ref.xlsx")
        dmw = wd.p("dmw.xlsx")
        ddl = wd.p("ddl.sql")
        out = wd.p("out.xlsx")

        # Master has C1,C2; Ref has C1,C2,C3 -> C3 should be flagged NOT_IN_MASTER
        make_dmw_xlsx(master, [
            {"Destination Table": "TREF", "Destination Column Name": "C1"},
            {"Destination Table": "TREF", "Destination Column Name": "C2"},
        ])
        make_dmw_xlsx(ref, [
            {"Destination Table": "TREF", "Destination Column Name": "C1"},
            {"Destination Table": "TREF", "Destination Column Name": "C2"},
            {"Destination Table": "TREF", "Destination Column Name": "C3"},
        ])

        # Primary run DMW just needs any mapping; Rule5 reads ref/master separately
        make_dmw_xlsx(dmw, [
            {"Destination Table": "T1", "Destination Column Name": "C1", "Migrating Column": "Yes",
             "Destination Data Type": "INT", "Destination Nullable": "NOT NULL", "Transformation Logic": "copy"},
        ])
        make_ddl_sql(ddl, {"T1": {"C1": "INT NOT NULL"}})

        run_validator(dmw=dmw, ddl=ddl, out=out, ref_dmw=ref, master_dmw=master)

        r5 = read_sheet_rows(out, "Rule5_Ref_Master_Mismatch")
        assert len(r5) >= 2, f"Expected Rule5_Ref_Master_Mismatch to have mismatch rows, got {len(r5)}"
        found = any(str(r[3] or "").strip() == "NOT_IN_MASTER" for r in r5[1:])
        assert found, "Expected NOT_IN_MASTER to be present in Rule5 mismatch sheet"
    finally:
        wd.cleanup()

if __name__ == "__main__":
    test_rule5_reference_subset_of_master()
    print("[OK] Rule5 tests passed")
