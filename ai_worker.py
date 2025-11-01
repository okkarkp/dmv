#!/usr/bin/env python3
import json, time, subprocess, argparse, yaml
from pathlib import Path

def run_llama(prompt, model):
    cmd=["llama-cli","--model",model,"--prompt",prompt,"--n-predict","64","--temp","0.2"]
    try:
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=20)
        return r.stdout.strip()
    except Exception as e: return f"ERROR:{e}"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",default="outputs/ai_pending.json")
    ap.add_argument("--out",default="outputs/ai_results.json")
    ap.add_argument("--config",default="/opt/oss-migrate/llm-planner/config.yaml")
    a=ap.parse_args()
    if not Path(a.input).exists(): return print("No pending file.")
    cfg=yaml.safe_load(Path(a.config).read_text()) if Path(a.config).exists() else {}
    model=cfg.get("ai",{}).get("offline_model","./models/tinyllama.Q4_K_M.gguf")
    data=json.loads(Path(a.input).read_text())
    res=[]
    for i,it in enumerate(data,1):
        if it["type"]=="Transformation_Quality":
            prompt=f"Assess completeness. Reply PASS or FLAG. Logic: '{it['text']}'"
        else:
            prompt=f"Is this reason clear? Reply PASS or FLAG. Text: '{it['text']}'"
        out=run_llama(prompt,model)
        res.append({**it,"ai_result":out})
        print(f"[{i}/{len(data)}] {out[:60]}")
        time.sleep(0.05)
    Path(a.out).write_text(json.dumps(res,indent=2))
    print(f"[OK] AI results saved to {a.out}")
if __name__=="__main__": main()
