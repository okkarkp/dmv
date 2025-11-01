def build_strict_prompt(rows_text: str, focus: str):
    return {
        "role": "user",
        "content": (
            f"{focus}\n"
            "Return ONLY a JSON array of objects with keys "
            "judgement, explanation, suggested_followup, dq_sql, recon_sql. "
            "Do not include markdown, text, or SQL outside JSON.\n"
            "<BEGIN_ANALYSIS>\n"
            f"{rows_text}\n"
            "</BEGIN_ANALYSIS>"
        )
    }
