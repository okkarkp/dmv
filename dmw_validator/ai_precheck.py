import re

def quick_syntax_check(logic: str):
    """
    Lightweight syntax sanity check before sending to AI model.
    Returns: (status, message)
    """
    if not logic or logic.strip() == "":
        return "EMPTY", "No transformation logic provided."

    # Count parentheses
    open_p = logic.count("(")
    close_p = logic.count(")")
    if open_p != close_p:
        return "ERROR", f"Parentheses mismatch: {open_p} '(' vs {close_p} ')'."

    # Check for basic SQL keywords or functions
    if not re.search(r"[A-Za-z]+\s*\(", logic):
        return "WARN", "No SQL-like function detected."

    # Check if the logic looks like valid SQL expression
    if not re.search(r"[A-Za-z_]+\.[A-Za-z_]+", logic):
        return "WARN", "No table.field pattern detected."

    return "OK", "Syntax appears valid."
