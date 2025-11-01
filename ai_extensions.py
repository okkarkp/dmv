import os, json
from llm_runner import run_llm

def evaluate_flagged_issues(issue_file, out_dir="outputs/job1/ai"):
    os.makedirs(out_dir, exist_ok=True)
    if not os.path.exists(issue_file):
        print(f"⚠️ No issue file found at {issue_file}")
        return []

    with open(issue_file) as f:
        issues = json.load(f)

    results = []
    dq_sqls = []
    recon_sqls = []

    for issue in issues:
        tgt_table = issue.get("table", "")
        tgt_field = issue.get("field", "")
        logic = issue.get("data", {}).get("Transformation Logic", "") if "data" in issue else ""

        if not tgt_table or not tgt_field:
            continue

        # --- AI evaluation prompt ---
        prompt = f"""
You are reviewing a flagged data mapping issue.

Target Table: {tgt_table}
Target Field: {tgt_field}
Transformation Logic: {logic}

1. Evaluate if the logic is valid or unclear.
2. Suggest a follow-up question for clarification.
3. Propose a DQ SQL check (e.g., null/uniqueness check).
4. Propose a Recon SQL check comparing source and target counts.

Respond in JSON with keys:
judgement, explanation, suggested_followup, dq_sql, recon_sql.
"""
        llm_out = run_llm(prompt)

        try:
            parsed = json.loads(llm_out)
        except:
            parsed = {
                "judgement": "Unparsed",
                "explanation": llm_out.strip(),
                "suggested_followup": "",
                "dq_sql": "",
                "recon_sql": ""
            }

        results.append({
            "Target Table": tgt_table,
            "Target Field": tgt_field,
            "Logic": logic,
            "AI_Judgement": parsed.get("judgement", "Unknown"),
            "AI_Explanation": parsed.get("explanation", ""),
            "AI_Suggested_Followup": parsed.get("suggested_followup", "")
        })

        if parsed.get("dq_sql"):
            dq_sqls.append(parsed["dq_sql"])
        if parsed.get("recon_sql"):
            recon_sqls.append(parsed["recon_sql"])

    # Save structured evaluation
    with open(os.path.join(out_dir, "logic_quality.json"), "w") as f:
        json.dump(results, f, indent=2)

    # Save SQLs separately
    with open(os.path.join(out_dir, "dq_checks_ai.sql"), "w") as f:
        f.write("\n\n".join(dq_sqls) if dq_sqls else "-- No DQ SQL generated")

    with open(os.path.join(out_dir, "recon_ai.sql"), "w") as f:
        f.write("\n\n".join(recon_sqls) if recon_sqls else "-- No Recon SQL generated")

    print(f"✅ AI logic + SQL generation complete → {out_dir}")
    return results
