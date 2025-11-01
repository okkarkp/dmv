import json, re

def safe_json_parse(text: str):
    """Try to clean Markdown fences and parse as JSON."""
    if not text:
        return [{"judgement": "Unparsed", "explanation": "Empty response"}]

    # Remove Markdown code fences
    text = re.sub(r"^```(?:json)?", "", text.strip(), flags=re.I | re.M)
    text = re.sub(r"```$", "", text.strip(), flags=re.M)

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            parsed = [parsed]
        return parsed
    except Exception:
        objs = re.findall(r"\{[^\{\}]+\}", text, re.S)
        parsed = []
        for o in objs:
            try:
                parsed.append(json.loads(o))
            except Exception:
                continue
        if parsed:
            return parsed
        return [{"judgement": "Unparsed", "explanation": text[:400]}]
