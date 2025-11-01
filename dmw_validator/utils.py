def ci_get(d: dict, key: str, default: str = "") -> str:
    """Case-insensitive dict get."""
    if not isinstance(d, dict):
        return default
    lk = key.strip().lower()
    for k, v in d.items():
        if str(k).strip().lower() == lk:
            return "" if v is None else str(v)
    return default

def resolve_table_field(rec: dict):
    """Resolve table/field from multiple possible key styles."""
    table = (
        rec.get("table")
        or rec.get("Target Table")
        or rec.get("Target Table Name")
        or ci_get(rec, "target table")
        or ci_get(rec, "target table name")
        or ""
    )
    field = (
        rec.get("field")
        or rec.get("Target Field")
        or rec.get("Target Field Name")
        or ci_get(rec, "target field")
        or ci_get(rec, "target field name")
        or ""
    )
    return table, field

def extract_logic(rec: dict) -> str:
    """Get Transformation Logic from the embedded data dict (case-insensitive)."""
    data = rec.get("data", {}) or {}
    # primary expected key (lower-case from extractor normalization)
    logic = ci_get(data, "transformation logic")
    if logic:
        return logic
    # fallback if any variant sneaks in
    return (
        ci_get(data, "Transformation Logic")
        or ci_get(data, "TRANSFORMATION LOGIC")
        or ""
    )
