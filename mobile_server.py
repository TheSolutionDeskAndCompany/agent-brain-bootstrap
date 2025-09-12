from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os


# TODO: wire this to your real agent pipeline
def run_agent(prompt: str) -> str:
    return f"Here’s a concise answer to: {prompt}"


class AgentRequest(BaseModel):
    input: str


app = FastAPI(title="Agent Mobile API", version="0.1.0")

# CORS: Restrict to configured origins if provided; otherwise allow all (dev)
_origins_env = os.getenv("MOBILE_CORS_ORIGINS", "").strip()
_origins = [o.strip() for o in _origins_env.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins if _origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


import time, hmac, hashlib
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "").strip()
AGENT_SIGNING_KEY = os.getenv("AGENT_SIGNING_KEY", "").encode()
SIGNING_SKEW = int(os.getenv("SIGNING_SKEW_SECONDS", "300"))

# Simple per-IP rate limiting for POST /api/agent
_rl_raw = os.getenv("MOBILE_RATE_LIMIT", os.getenv("RATE_LIMIT", "30/10"))
_rl_cfg = _rl_raw.split("/", 1)
try:
    _RL_MAX = int(_rl_cfg[0]); _RL_WIN = int(_rl_cfg[1])
except Exception:
    _RL_MAX, _RL_WIN = 30, 10
app.state._rate = {}

def _rate_limit_ok(ip: str) -> bool:
    now = time.time(); win_start = now - _RL_WIN
    buf = app.state._rate.setdefault(ip, [])
    # drop old entries
    k = 0
    for k, ts in enumerate(buf):
        if ts >= win_start:
            break
    else:
        k = len(buf)
    if k:
        del buf[:k]
    if len(buf) >= _RL_MAX:
        return False
    buf.append(now)
    return True


@app.post("/api/agent")
async def agent(req: AgentRequest, request: Request):
    # Require JSON content type
    ctype = (request.headers.get('content-type') or '').lower()
    if 'application/json' not in ctype:
        return JSONResponse({"ok": False, "error": "unsupported_media_type"}, status_code=415)
    if AGENT_TOKEN:
        provided = request.headers.get("x-agent-token", "").strip()
        if provided != AGENT_TOKEN:
            return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
    if AGENT_SIGNING_KEY:
        ts = request.headers.get("x-agent-timestamp", "").strip()
        sig = request.headers.get("x-agent-sig", "").strip().lower()
        try:
            ts_i = int(ts)
        except Exception:
            return JSONResponse({"ok": False, "error": "missing_or_bad_timestamp"}, status_code=401)
        now = int(time.time())
        if abs(now - ts_i) > SIGNING_SKEW:
            return JSONResponse({"ok": False, "error": "timestamp_skew"}, status_code=401)
        body = await request.body()
        msg = str(ts_i).encode() + b"." + body
        digest = hmac.new(AGENT_SIGNING_KEY, msg, hashlib.sha256).hexdigest()
        import hmac as _h
        if not _h.compare_digest(sig, digest):
            return JSONResponse({"ok": False, "error": "bad_signature"}, status_code=401)
    # Rate limit per client IP
    client_ip = request.client.host if request.client else "unknown"
    if not _rate_limit_ok(client_ip):
        return JSONResponse({"ok": False, "error": "rate_limited"}, status_code=429)
    text = (req.input or "").strip()
    if not text:
        return JSONResponse({"ok": False, "error": "empty_input"}, status_code=400)
    if len(text) > 4000:
        return JSONResponse({"ok": False, "error": "input_too_long"}, status_code=413)
    return {"ok": True, "output": run_agent(text)}


@app.get("/healthz")
async def healthz():
    return {"ok": True}


# Static hosting for mobile UI and RDP profiles
if os.path.isdir("public"):
    app.mount("/public", StaticFiles(directory="public"), name="public")
if os.path.isdir("public/rdp"):
    app.mount("/rdp", StaticFiles(directory="public/rdp"), name="rdp")


if __name__ == "__main__":
    host = os.getenv("MOBILE_HOST", "127.0.0.1")
    if host == "0.0.0.0" and not AGENT_TOKEN and not os.getenv("ALLOW_INSECURE"):
        print("[WARN] Mobile API bound to 0.0.0.0 without AGENT_TOKEN. Set AGENT_TOKEN or MOBILE_HOST=127.0.0.1.")
    uvicorn.run("mobile_server:app", host=host, port=8000, reload=True)
