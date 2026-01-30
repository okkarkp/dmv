# ------------------------------------------------
# Rule3: Baseline Data Model vs Table Details
# ------------------------------------------------
try:
    wb_td = load_workbook(dmw_xlsx, read_only=True, data_only=True)
    ws_td = None

    for sn in wb_td.sheetnames:
        if norm_col(sn) == norm_col("TABLE DETAILS"):
            ws_td = wb_td[sn]
            break

    table_details_set: Set[str] = set()

    if ws_td is not None:
        hr = detect_header_row_flexible(
            ws_td,
            min_non_empty=1,
            max_scan=10,
            default_row=1
        )
        tcols, tlookup = build_header_index(ws_td, hr)
        start = hr + 1

        # Resolve table column
        table_i = (
            resolve_col(tlookup, "Table Name")
            or resolve_col(tlookup, "Destination Table")
        )

        if table_i is None:
            for k, idxs in tlookup.items():
                if "TABLE" in k:
                    table_i = idxs[0]
                    break

        if table_i is not None:
            for r in ws_td.iter_rows(
                min_row=start,
                max_row=ws_td.max_row,
                values_only=True
            ):
                if not r:
                    break

                vals = [s(v) for v in r[:len(tcols)]]
                if all(v == "" for v in vals):
                    break

                tname = vals[table_i] if table_i < len(vals) else ""
                if not is_na(tname):
                    table_details_set.add(s(tname).upper())

    # ✅ CORRECT CHECK:
    # Tables USED in Baseline but MISSING in Table Details
    missing_tables = sorted(baseline_tables - table_details_set)

    for t in missing_tables:
        ws_r3.append([
            t,
            "MISSING_IN_TABLE_DETAILS",
            "Destination table used in Baseline Data Model but not found in Table Details sheet"
        ])

    wb_td.close()

except Exception:
    logging.exception("Rule3 processing failed")
