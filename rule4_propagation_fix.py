def apply_rule4_result(row, rule4_failed, existing_status, existing_remarks):
    """
    Rule-4 is informational.
    It must NOT override overall Validation_Status.
    """
    if not rule4_failed:
        return row

    # Rule4 column index = -6 (based on current layout)
    row[-6] = "FAIL"

    # DO NOT TOUCH Validation_Status
    # row[-2] stays as-is

    if existing_remarks:
        row[-1] = existing_remarks + " | Rule4 mismatch – see Rule4_DDL_Mismatch"
    else:
        row[-1] = "Rule4 mismatch – see Rule4_DDL_Mismatch"

    return row
