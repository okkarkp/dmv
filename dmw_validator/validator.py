import os, json
from dmw_validator.utils import resolve_table_field, extract_logic

def validate_dmw_vs_ddl(valid_json_path, ddl_schema, baseline_path, out_dir, mode="rules"):
    """Forward rows with table/field/logic intact; keep logic case-insensitive."""
    os.makedirs(out_dir, exist_ok=True)

    with open(valid_json_path) as f:
        records = json.load(f)

    issues = []
    for rec in records:
        table, field = resolve_table_field(rec)
        logic = extract_logic(rec)
        # basic pass-through record; downstream AI adds meaning
        issues.append({
            "table": table,
            "field": field,
            "data": rec.get("data", {}),
            "issue_type": "ai_review" if logic else "missing_logic",
            "description": "Ready for AI review" if logic else f"No transformation logic for {table}.{field}"
        })

    issues_file = os.path.join(out_dir, "mismatched_fields_ai.json")
    with open(issues_file, "w") as f:
        json.dump(issues, f, indent=2)

    print(f"✅ Validation complete ({len(issues)} rows) → {issues_file}")
    return issues
