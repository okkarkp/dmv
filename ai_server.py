#!/usr/bin/env python3
import argparse, re, ast, operator as op
from fastapi import FastAPI, Body, Form
from fastapi.responses import HTMLResponse, StreamingResponse
import uvicorn
from llama_cpp import Llama

app = FastAPI(title="DMW Validator AI Microservice with ChatUI")

MODEL_PATH = "/app/models/Phi-4-mini-instruct-Q3_K_S.gguf"
llm = Llama(model_path=MODEL_PATH, n_threads=8, n_ctx=2048)

# ------------------  MATH FALLBACK ------------------
import ast, operator as op, re
_ALLOWED = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
            ast.Div: op.truediv, ast.Pow: op.pow, ast.USub: op.neg,
            ast.FloorDiv: op.floordiv, ast.Mod: op.mod}
_MATH_RE = re.compile(r"^\s*(?:what\s+is\s+(?:the\s+value\s+of\s+)?|calculate\s+|compute\s+|evaluate\s+|)\s*([0-9\.\s\+\-\*\/\%\(\)\^]+)\s*=?\s*\?*\s*$", re.I)

def _eval_ast(node):
    if isinstance(node, ast.Num): return node.n
    if isinstance(node, ast.Constant) and isinstance(node.value,(int,float)): return node.value
    if isinstance(node, ast.BinOp): return _ALLOWED[type(node.op)](_eval_ast(node.left), _eval_ast(node.right))
    if isinstance(node, ast.UnaryOp): return _ALLOWED[type(node.op)](_eval_ast(node.operand))
    raise ValueError

def try_math(prompt:str):
    m = _MATH_RE.match(prompt or "")
    if not m: return None
    expr = m.group(1).replace("^","**")
    try:
        val = _eval_ast(ast.parse(expr, mode="eval").body)
        return str(int(val)) if isinstance(val,(int,)) or (isinstance(val,float) and val.is_integer()) else str(val)
    except: return None
# ----------------------------------------------------

SYS_PREAMBLE = "You are a concise assistant. Return only the answer, no explanation."
def llm_complete(prompt:str,max_tokens=80):
    out = llm(f"{SYS_PREAMBLE}\nQ:{prompt}\nA:", max_tokens=max_tokens,
              temperature=0.2, top_p=0.9, stop=["</s>","\nQ:"])
    return out["choices"][0]["text"].strip()

# ------------- Simple ChatGPT-like UI -------------
HTML_PAGE = """
<!DOCTYPE html><html><head><title>DMW Validator AI</title>
<style>
body{font-family:Arial;background:#1e1e1e;color:#ddd;margin:0;padding:0}
#chat{height:80vh;overflow:auto;padding:1em}
.msg-user{background:#0078d7;color:#fff;padding:8px 12px;border-radius:12px;margin:6px 0 6px auto;width:fit-content;max-width:80%}
.msg-ai{background:#333;padding:8px 12px;border-radius:12px;margin:6px auto 6px 0;width:fit-content;max-width:80%}
#prompt{width:80%;padding:10px;font-size:1em;border-radius:8px;border:none}
button{padding:10px 16px;font-size:1em;border:none;border-radius:8px;background:#0078d7;color:#fff;margin-left:8px}
</style></head><body>
<h2 style="padding:1em;margin:0;background:#111">DMW Validator AI Chat</h2>
<div id="chat"></div>
<div style="padding:1em;background:#111;position:fixed;bottom:0;width:100%">
<form id="f"><input id="prompt" autocomplete="off"><button>Send</button></form>
</div>
<script>
const chat=document.getElementById('chat');
document.getElementById('f').onsubmit=async e=>{
 e.preventDefault();
 const p=document.getElementById('prompt');
 const q=p.value.trim(); if(!q)return;
 chat.innerHTML+=`<div class='msg-user'>${q}</div>`;
 p.value=''; chat.scrollTop=chat.scrollHeight;
 const r=await fetch('/ask',{method:'POST',body:new URLSearchParams({prompt:q})});
 const t=await r.text();
 chat.innerHTML+=`<div class='msg-ai'>${t}</div>`;
 chat.scrollTop=chat.scrollHeight;
};
</script></body></html>
"""
@app.get("/", response_class=HTMLResponse)
def index(): return HTML_PAGE

@app.post("/ask")
def ask(prompt:str=Form(...)):
    ans = try_math(prompt)
    if ans is not None: return ans
    return llm_complete(prompt)
# -------------------------------------------------

@app.post("/v1/completions")
def complete(data:dict=Body(...)):
    prompt=(data or {}).get("prompt","")
    if not prompt: return {"error":"Missing prompt"}
    ans=try_math(prompt)
    if ans is not None: return {"text":ans}
    return {"text":llm_complete(prompt)}

if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--port",type=int,default=8081)
    args=parser.parse_args()
    uvicorn.run(app,host="0.0.0.0",port=args.port)
