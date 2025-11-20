#!/usr/bin/env python3
from fastapi import FastAPI, File, UploadFile, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
import shutil, subprocess, uuid, time, json, logging, openpyxl, os
from cfg import CFG, AI_CFG, PATHS, WEB_CFG

app = FastAPI(title="DMW Validator Web")

UPLOAD_DIR = Path(PATHS.get("uploads", "./uploads")); UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR = Path(PATHS.get("outputs", "./outputs")); OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH   = Path(PATHS.get("logs", "./logs")) / "dmw_web.log"; LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(filename=str(LOG_PATH), level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def save_upload(fileobj:UploadFile)->Path:
    if not fileobj: return None
    path = UPLOAD_DIR / f"{uuid.uuid4()}_{fileobj.filename}"
    with path.open("wb") as f: shutil.copyfileobj(fileobj.file, f)
    return path

def summarize_excel(out_path:Path):
    try:
        wb=openpyxl.load_workbook(out_path, read_only=True, data_only=True)
        ws=wb.active
        headers=[c.value for c in next(ws.iter_rows(min_row=2,max_row=2))]
        idx_status=headers.index("Validation_Status") if "Validation_Status" in headers else None
        counts={"PASS":0,"FAIL":0,"INFO":0}
        if idx_status:
            for row in ws.iter_rows(min_row=3,values_only=True):
                val=str(row[idx_status-1]).upper() if row[idx_status-1] else ""
                if val in counts: counts[val]+=1
        wb.close()
        return counts
    except:
        return {}

def run_validator(cmd, out_path, generate_flag):
    start=time.time()
    try:
        logging.info("Running validator: %s", " ".join(cmd))
        subprocess.run(cmd, check=True)
        if generate_flag:
            logging.info("Triggering artifact generation...")
            gen_cmd = [
                "python3",
                "/app/generate_migration_artifacts.py",
                "--validated-xlsx", str(out_path),
                "--out-dir", str(OUTPUT_DIR / "generated")
            ]
            subprocess.run(gen_cmd, check=True)
            logging.info("Artifact generation completed.")
    except Exception as e:
        logging.error("Validator failed: %s", e)
    logging.info("Run finished in %.1fs", time.time()-start)

# -----------------------------------------------------------
# 🎨 Modern UI Styling
# -----------------------------------------------------------

BASE_STYLE = """
<style>
body {
  font-family: Arial, sans-serif; 
  background-color: #f5f7fa;
  margin: 0; padding: 30px;
  color: #333;
}

h1, h2, h3 {
  font-weight: 600;
}

.card {
  background: white;
  border-radius: 12px;
  padding: 25px;
  margin-bottom: 25px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.08);
}

.input-row {
  margin: 10px 0;
}

input[type=file] {
  padding: 6px;
  border-radius: 6px;
  background: #f1f1f1;
}

button, input[type=submit] {
  background: #1971c2;
  color: white;
  padding: 12px 24px;
  border: none;
  margin-top: 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 15px;
}
button:hover, input[type=submit]:hover {
  background: #0b5798;
}

hr { margin: 40px 0; }

.loader {
  border: 8px solid #e0e0e0;
  border-top: 8px solid #228be6;
  border-radius: 50%;
  width: 70px; height: 70px;
  animation: spin 1s linear infinite;
  margin: auto;
}
@keyframes spin { 100% { transform: rotate(360deg); } }

.small-text { color: #777; font-size: 13px; }

.summary-box {
  display: inline-block;
  background: #f1f3f5;
  padding: 15px;
  border-radius: 10px;
  margin: 10px;
  min-width: 120px;
  text-align: center;
}
.summary-value { font-size: 22px; font-weight: bold; }
</style>
"""

# -----------------------------------------------------------
# 🏠 HOME PAGE
# -----------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def index():
    return f"""
    <html><head><title>DMW Validator</title>{BASE_STYLE}</head>
    <body>
      <h1>📊 DMW Validator</h1>

      <div class='card'>
        <h2>Upload Files</h2>
        <form action="/validate" method="post" enctype="multipart/form-data">

          <div class="input-row"><b>DMW Excel:</b><br>
            <input type="file" name="dmw" required></div>

          <div class="input-row"><b>DDL SQL:</b><br>
            <input type="file" name="ddl" required></div>

          <h3>Optional: Previous Versions</h3>

          <div class="input-row">Previous DMW Excel:<br>
            <input type="file" name="prev_dmw"></div>

          <div class="input-row">Previous DDL SQL:<br>
            <input type="file" name="prev_ddl"></div>

          <div class="input-row">
            <label><input type="checkbox" name="enable_ai" value="1">  
            🧠 Enable AI Suggestions</label>
          </div>

          <div class="input-row">
            <label><input type="checkbox" name="generate_artifacts" value="1">  
            🧱 Generate Migration Scripts</label>
          </div>

          <input type="submit" value="Run Validation">
        </form>
      </div>

      <div class="card small-text">
        <b>System Config</b>
        <pre>{json.dumps(CFG, indent=2)}</pre>
      </div>
    </body></html>
    """

# -----------------------------------------------------------
# ⏳ PROGRESS PAGE
# -----------------------------------------------------------
@app.post("/validate", response_class=HTMLResponse)
async def validate_files(
    background_tasks: BackgroundTasks,
    dmw: UploadFile = File(...),
    ddl: UploadFile = File(...),
    prev_dmw: UploadFile = File(None),
    prev_ddl: UploadFile = File(None),
    enable_ai: str = Form(default="0"),
    generate_artifacts: str = Form(default="0")
):
    dmw_path = save_upload(dmw)
    ddl_path = save_upload(ddl)
    prev_dmw_path = save_upload(prev_dmw) if prev_dmw else None
    prev_ddl_path = save_upload(prev_ddl) if prev_ddl else None

    out_path = OUTPUT_DIR / f"{dmw_path.stem}_validated.xlsx"

    cmd = [
        "python3", "/app/validate_dmw_final.py",
        "--dmw-xlsx", str(dmw_path),
        "--ddl-sql", str(ddl_path),
        "--out", str(out_path)
    ]

    if prev_dmw_path and prev_dmw_path.suffix.lower()==".xlsx":
        cmd += ["--prev-dmw", str(prev_dmw_path)]
    if prev_ddl_path and prev_ddl_path.suffix.lower()==".sql":
        cmd += ["--prev-ddl", str(prev_ddl_path)]
    if enable_ai=="1":
        cmd += ["--enable-ai"]

    background_tasks.add_task(run_validator, cmd, out_path, generate_artifacts=="1")

    return f"""
    <html><head><meta http-equiv='refresh' content='6;url=/result?file={out_path.name}'>{BASE_STYLE}</head>
    <body style="text-align:center">
      <div class="card" style="max-width:500px;margin:auto;">
        <div class="loader"></div>
        <h2>Validation in progress...</h2>
        <p class="small-text">This page refreshes every 6 seconds</p>
        <p>AI: {"🧠 Enabled" if enable_ai=="1" else "⚙️ Disabled"} |
           Artifacts: {"🧱 Yes" if generate_artifacts=="1" else "❌ No"}</p>
      </div>
    </body></html>
    """

# -----------------------------------------------------------
# ✅ RESULT PAGE
# -----------------------------------------------------------
@app.get("/result", response_class=HTMLResponse)
def result(file:str):
    out_path = OUTPUT_DIR / file
    gen_dir = OUTPUT_DIR / "generated"

    # Still processing?
    if not out_path.exists() or os.path.getsize(out_path) < 1500:
        tail = ""
        try: tail = "\n".join(Path(LOG_PATH).read_text().splitlines()[-8:])
        except: tail = "(no logs)"

        return f"""
        <html><head><meta http-equiv='refresh' content='6'>{BASE_STYLE}</head>
        <body style="text-align:center">
          <div class="card" style="max-width:500px;margin:auto;">
            <div class="loader"></div>
            <h2>Still processing...</h2>
            <pre class="small-text">{tail}</pre>
          </div>
        </body></html>
        """

    counts = summarize_excel(out_path)

    # Summary badges
    summary_html = "".join([
        f"<div class='summary-box'><div class='summary-value'>{counts.get(k,0)}</div>{k}</div>"
        for k in ["PASS","FAIL","INFO"]
    ])

    generated_files = "".join(
        [f"<li><a href='/download?file=generated/{p.name}'>{p.name}</a></li>"
         for p in gen_dir.glob('*.sql')]
    ) if gen_dir.exists() else "<i>No SQL generated.</i>"

    return f"""
    <html><head>{BASE_STYLE}</head>
    <body>
      <h1>✅ Validation Completed</h1>

      <div class="card">
        <h2>Summary</h2>
        {summary_html}
        <p><a href='/download?file={out_path.name}'><button>⬇ Download Validated Excel</button></a></p>
      </div>

      <div class="card">
        <h2>🧱 Migration Scripts</h2>
        <ul>{generated_files}</ul>
      </div>

      <div class="card small-text">
        <h3>Recent Logs</h3>
        <pre>{Path(LOG_PATH).read_text()[-800:]}</pre>
      </div>
    </body></html>
    """

@app.get("/download")
def download(file:str):
    path = OUTPUT_DIR / file if not file.startswith("generated/") else OUTPUT_DIR / file
    return FileResponse(path=path, filename=path.name, media_type="application/octet-stream")

def main():
    import uvicorn
    uvicorn.run(app, host=WEB_CFG.get("host","0.0.0.0"), port=int(WEB_CFG.get("port",8085)))

if __name__ == "__main__":
    main()
