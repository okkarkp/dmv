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

logging.basicConfig(
    filename=str(LOG_PATH),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def save_upload(fileobj:UploadFile)->Path:
    if not fileobj: return None
    path = UPLOAD_DIR / f"{uuid.uuid4()}_{fileobj.filename}"
    with path.open("wb") as f:
        shutil.copyfileobj(fileobj.file, f)
    return path

def summarize_excel(out_path:Path):
    try:
        wb=openpyxl.load_workbook(out_path, read_only=True, data_only=True)
        ws=wb.active
        headers=[c.value for c in next(ws.iter_rows(min_row=2,max_row=2))]
        idx=headers.index("Validation_Status") if "Validation_Status" in headers else None
        counts={"PASS":0,"FAIL":0,"INFO":0}
        if idx is not None:
            for row in ws.iter_rows(min_row=3,values_only=True):
                val=str(row[idx]).upper() if row[idx] else ""
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
            gen_cmd = [
                "python3",
                "/app/generate_migration_artifacts.py",
                "--validated-xlsx", str(out_path),
                "--out-dir", str(OUTPUT_DIR / "generated")
            ]
            subprocess.run(gen_cmd, check=True)
    except Exception as e:
        logging.error("Validator failed: %s", e)
    logging.info("Run finished in %.1fs", time.time()-start)

# ---------------- UI ----------------

BASE_STYLE = """<style> /* unchanged UI */ </style>"""

@app.get("/", response_class=HTMLResponse)
def index():
    return "<html><body><h1>DMW Validator</h1></body></html>"

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

    if prev_dmw_path: cmd += ["--prev-dmw", str(prev_dmw_path)]
    if prev_ddl_path: cmd += ["--prev-ddl", str(prev_ddl_path)]
    if enable_ai=="1": cmd += ["--enable-ai"]

    background_tasks.add_task(run_validator, cmd, out_path, generate_artifacts=="1")
    return "Validation started..."

@app.get("/download")
def download(file:str):
    path = OUTPUT_DIR / file
    return FileResponse(path=path, filename=path.name)

def main():
    import uvicorn
    uvicorn.run(app, host=WEB_CFG.get("host","0.0.0.0"), port=int(WEB_CFG.get("port",8085)))

if __name__ == "__main__":
    main()
