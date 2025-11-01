import os

def build_viewer(out_dir):
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>DMW Validation Report</title>
  <style>
    body {{ font-family: sans-serif; margin: 2em; background: #f8f8f8; }}
    h1 {{ color: #333; }}
    pre {{ background: #fff; border: 1px solid #ccc; padding: 1em; overflow-x: auto; }}
    .section {{ margin-bottom: 3em; }}
  </style>
</head>
<body>
<h1>📋 DMW Validation Report</h1>

<div class="section"><h2>🚨 Detected Issues</h2><pre id="mismatches">Loading...</pre></div>
<div class="section"><h2>🤖 AI Logic Review</h2><pre id="ai-logic">Loading...</pre></div>
<div class="section"><h2>🧾 AI DQ Checks</h2><pre id="ai-dq-sql">Loading...</pre></div>
<div class="section"><h2>🔄 AI Recon Checks</h2><pre id="ai-recon-sql">Loading...</pre></div>

<script>
fetch("mismatched_fields.json").then(r => r.text()).then(d => document.getElementById("mismatches").innerText = d);
fetch("ai/logic_quality.json").then(r => r.text()).then(d => document.getElementById("ai-logic").innerText = d);
fetch("ai/dq_checks_ai.sql").then(r => r.text()).then(d => document.getElementById("ai-dq-sql").innerText = d);
fetch("ai/recon_ai.sql").then(r => r.text()).then(d => document.getElementById("ai-recon-sql").innerText = d);
</script>
</body></html>
"""
    out_file = os.path.join(out_dir, "viewer.html")
    with open(out_file, "w") as f:
        f.write(html)
    print(f"✅ Viewer built → {out_file}")
