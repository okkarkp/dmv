def evaluate_rule1(
    migrating,
    reason,
    src_table,
    src_col,
    dest_table,
    dest_col
):
    """
    Rule-1: Source → Destination mapping completeness
    """

    migrating = (migrating or "").strip().upper()
    reason = (reason or "").strip()

    src_na = not src_table or src_table.upper() == "NA"
    dest_present = bool(dest_table and dest_col)

    # Case 1: Migrating = YES → destination MUST exist
    if migrating == "YES":
        if dest_present:
            return "PASS", ""
        else:
            return "FAIL", "Migrating=YES but destination mapping is missing"

    # Case 2: Migrating = NO → reason MUST exist
    if migrating == "NO":
        if reason:
            return "PASS", ""
        else:
            return "FAIL", "Migrating=NO but reason for not migrating is missing"

    # Case 3: New destination column (source NA, dest exists)
    if src_na and dest_present:
        return "PASS", ""

    # Fallback (should not normally hit)
    return "PASS", ""
