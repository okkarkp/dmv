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
    except Exception as e:
        logging.warning(f"Summary failed: {e}")
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
        logging.error("Validator or generation failed: %s", e)
    logging.info("Run finished in %.1fs", time.time()-start)

@app.get("/", response_class=HTMLResponse)
def index():
    return f"""
    <html><head><title>DMW Validator</title></head>
    <body style='font-family:Arial; margin:50px'>
      <h2>📊 Data Mapping Workbook Validator</h2>
      <form action="/validate" method="post" enctype="multipart/form-data">
        <p><b>Current Files</b></p>
        <p>DMW Excel: <input type="file" name="dmw" required></p>
        <p>DDL SQL: <input type="file" name="ddl" required></p>

        <p><b>Previous Versions (optional)</b></p>
        <p>Previous DMW Excel: <input type="file" name="prev_dmw"></p>
        <p>Previous DDL SQL: <input type="file" name="prev_ddl"></p>

        <p><label><input type="checkbox" name="enable_ai" value="1" {"checked" if AI_CFG.get("enabled") else ""}>
           🧠 Enable AI Suggestions</label></p>
        <p><label><input type="checkbox" name="generate_artifacts" value="1">
           🧱 Generate Migration Scripts (DDL / Recon / Insert-Select)</label></p>

        <input type="submit" value="Validate">
      </form>
      <hr>
      <pre>Config: {json.dumps(CFG, indent=2)}</pre>
    </body></html>
    """

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

    # Only include prev files if they exist and are valid
    if prev_dmw_path and prev_dmw_path.suffix.lower() == ".xlsx":
        cmd += ["--prev-dmw", str(prev_dmw_path)]
    if prev_ddl_path and prev_ddl_path.suffix.lower() == ".sql":
        cmd += ["--prev-ddl", str(prev_ddl_path)]

    if enable_ai == "1":
        cmd += ["--enable-ai",
                "--ai-host", AI_CFG.get("ai_host","127.0.0.1"),
                "--ai-port", str(AI_CFG.get("ai_port",8081)),
                "--ai-model", AI_CFG.get("ai_model","local-model")]

    background_tasks.add_task(run_validator, cmd, out_path, generate_artifacts=="1")

    return f"""
    <html><head>
      <meta http-equiv='refresh' content='6;url=/result?file={out_path.name}'>
      <style>
        .loader {{border:8px solid #f3f3f3;border-top:8px solid #3498db;border-radius:50%;width:60px;height:60px;animation:spin 1s linear infinite}}
        @keyframes spin {{0% {{transform: rotate(0deg)}}100% {{transform: rotate(360deg)}}}}
      </style>
    </head>
    <body style='font-family:Arial; margin:50px; text-align:center'>
      <div class='loader' style='margin:auto'></div>
      <h3>Validation in progress...</h3>
      <p>⏳ This page refreshes every 6 seconds.</p>
      <p>AI: {"🧠 Enabled" if enable_ai=="1" else "⚙️ Disabled"} |
         Generate Artifacts: {"🧱 Yes" if generate_artifacts=="1" else "❌ No"}</p>
      <p><i>Logs: {LOG_PATH}</i></p>
    </body></html>
    """

@app.get("/result", response_class=HTMLResponse)
def result(file:str):
    import os
    out_path = OUTPUT_DIR / file
    gen_dir = OUTPUT_DIR / "generated"

    if not out_path.exists() or os.path.getsize(out_path) < 1024:
        tail = ""
        try:
            tail = "\n".join(Path(LOG_PATH).read_text().splitlines()[-8:])
        except Exception:
            tail = "(no recent logs)"
        return f"""
        <html><head><meta http-equiv='refresh' content='6'></head>
        <body style='font-family:Arial;margin:50px;text-align:center'>
        <div style='border:8px solid #f3f3f3;border-top:8px solid #3498db;border-radius:50%;width:60px;height:60px;margin:auto;animation:spin 1s linear infinite'></div>
        <h3>⏳ Still processing...</h3>
        <p>Refreshes every 6 seconds until validation completes.</p>
        <pre>{tail}</pre>
        </body></html>
        """

    counts = summarize_excel(out_path)
    generated_files = "".join(
        [f"<li><a href='/download?file=generated/{p.name}'>{p.name}</a></li>"
         for p in gen_dir.glob('*.sql')]
    ) if gen_dir.exists() else "<i>No generated SQL files</i>"

    return f"""
    <html><body style='font-family:Arial;margin:50px'>
      <h2>✅ Validation Completed</h2>
      <p><b>Summary:</b> {json.dumps(counts)}</p>
      <p><a href='/download?file={out_path.name}'>⬇️ Download validated Excel</a></p>
      <h3>🧱 Generated Migration Scripts</h3>
      <ul>{generated_files}</ul>
      <hr><pre>{Path(LOG_PATH).read_text()[-600:]}</pre>
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
