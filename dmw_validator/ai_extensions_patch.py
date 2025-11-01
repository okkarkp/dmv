import os, json, time
from dmw_validator.utils import resolve_table_field, extract_logic
from dmw_validator.ai_extensions import _run_batch  # reuse model + parser

def run_ai_extensions_fixed(issues, out_dir="outputs/job1/ai", model="light", prompt_profile=None):
    """Row-by-row AI validation for guaranteed parsed JSON."""
    os.makedirs(out_dir, exist_ok=True)
    if not issues:
        print("ℹ️ No issues detected, AI extensions skipped.")
        return []

    results, dq_sqls, recon_sqls = [], [], []
    start = time.time()
    print(f"⚙️ AI validation (row-by-row strict JSON) started… {len(issues)} rows")

    for idx, rec in enumerate(issues, 1):
        table, field = resolve_table_field(rec)
        logic = extract_logic(rec)
        row_text = f"RowID={idx} | Target Table={table} | Target Field={field} | Logic={logic}"

        parsed = _run_batch([rec], offset=idx-1, focus="Check logic")
        p = parsed[0] if parsed else {}

        results.append({
            "Target Table": table,
            "Target Field": field,
            "Logic": logic,
            "AI_Judgement": p.get("judgement", "Unclear"),
            "AI_Explanation": p.get("explanation", "No explicit output from model"),
            "AI_Suggested_Followup": p.get("suggested_followup", "Review transformation manually")
        })

        if p.get("dq_sql"): dq_sqls.append(p["dq_sql"])
        if p.get("recon_sql"): recon_sqls.append(p["recon_sql"])

    with open(os.path.join(out_dir, "logic_quality.json"), "w") as f:
        json.dump(results, f, indent=2)
    with open(os.path.join(out_dir, "dq_checks_ai.sql"), "w") as f:
        f.write("\n\n".join(dq_sqls) or "-- No DQ SQL generated")
    with open(os.path.join(out_dir, "recon_ai.sql"), "w") as f:
        f.write("\n\n".join(recon_sqls) or "-- No Recon SQL generated")

    print(f"✅ AI validation complete → {out_dir} ({len(results)} rows, {time.time()-start:.1f}s)")
    return results
