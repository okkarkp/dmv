import os, json

def _resolve_table_field(rec):
    """
    Unified resolver for both IRIN3 and legacy IRIN2 extractors.
    Prefers IRIN3 keys.
    """
    # IRIN3 naming
    tbl = rec.get("destination_table") or rec.get("table") or ""
    col = rec.get("destination_column") or rec.get("field") or ""

    return tbl.strip(), col.strip()

def _resolve_logic(rec):
    """
    Unified transformation logic extraction.
    """
    return (rec.get("transformation") or "").strip()

def validate_dmw_vs_ddl(valid_json_path, ddl_schema, baseline_path, out_dir, mode="rules"):
    """
    Lightweight AI-prep validator:
    - Reads extracted rows
    - Normalizes IRIN3 vs IRIN2 data
    - Marks missing logic vs ready for AI review
    """
    os.makedirs(out_dir, exist_ok=True)

    with open(valid_json_path) as f:
        records = json.load(f)

    issues = []
    for rec in records:
        table, field = _resolve_table_field(rec)
        logic = _resolve_logic(rec)

        issues.append({
            "table": table,
            "field": field,
            "logic": logic,
            "migrating": rec.get("migrating", ""),
            "full_row": rec.get("full_row", rec.get("data", {})),  # maintain backward compatibility
            "issue_type": "ai_review" if logic else "missing_logic",
            "description": (
                "Ready for AI review"
                if logic else
                f"No transformation logic for {table}.{field}"
            )
        })

    issues_file = os.path.join(out_dir, "mismatched_fields_ai.json")
    with open(issues_file, "w") as f:
        json.dump(issues, f, indent=2)

    print(f"✅ Validation complete ({len(issues)} rows) → {issues_file}")
    return issues
