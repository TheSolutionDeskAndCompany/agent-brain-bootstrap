import os
import time
import hmac
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi import Response
from pydantic import BaseModel
from enum import Enum

# Bridge that safely calls optional functions in decision_engine
from .controller_bridge import AgentBridge

APP_PORT = int(os.getenv("AGENT_PORT", "8765"))
PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"
LOG_FILE = Path.cwd() / "logs" / "agent.log"
MACROS_DEFAULT = Path(__file__).resolve().parent / "config" / "macros.json"
MACROS_USER = Path.cwd() / "logs" / "macros.json"
MAX_TEXT_LEN = int(os.getenv("MAX_TEXT_LEN", "4000"))

app = FastAPI(title="AgentBrain Controller")
bridge = AgentBridge()

# Optional token to protect state-changing commands (start/stop/dictate)
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "").strip()
AGENT_SIGNING_KEY = os.getenv("AGENT_SIGNING_KEY", "").encode()
SIGNING_SKEW = int(os.getenv("SIGNING_SKEW_SECONDS", "300"))  # 5 minutes default

# Simple per-IP rate limiting for POST /api/command
_rl_cfg = os.getenv("RATE_LIMIT", "30/10").split("/", 1)
try:
    _RL_MAX = int(_rl_cfg[0])
    _RL_WIN = int(_rl_cfg[1])
except Exception:
    _RL_MAX, _RL_WIN = 30, 10
app.state._rate = {}

def _rate_limit_ok(ip: str) -> bool:
    now = time.time()
    win_start = now - _RL_WIN
    buf = app.state._rate.setdefault(ip, [])
    # drop old
    i = 0
    for i, ts in enumerate(buf):
        if ts >= win_start:
            break
    else:
        i = len(buf)
    if i:
        del buf[:i]
    if len(buf) >= _RL_MAX:
        return False
    buf.append(now)
    return True

if PUBLIC_DIR.exists():
    app.mount("/public", StaticFiles(directory=str(PUBLIC_DIR)), name="public")


class Action(str, Enum):
    start = "start"
    stop = "stop"
    dictate = "dictate"
    status = "status"
    set = "set"


class CommandIn(BaseModel):
    action: Action
    payload: Optional[Dict[str, Any]] = None


@app.get("/controller", response_class=HTMLResponse)
def controller() -> str:
    index = PUBLIC_DIR / "controller.html"
    return index.read_text(encoding="utf-8") if index.exists() else "<h1>Missing UI</h1>"


@app.get("/status")
def status_json():
    return bridge.status()


@app.get("/api/status")
def api_status_compat():
    # Compatibility with the initial UI that expects a string status and a dict state
    try:
        from agent import agent_main as _am  # lazy import to avoid cycles
        status_line = getattr(_am, "STATUS_LINE", "")
        state = getattr(_am, "RUNTIME_STATE", {})
        if not status_line:
            # Derive a simple line from bridge if main didn't set one yet
            bs = bridge.status()
            status_line = bs.get("engine_status") or (
                f"running={bs.get('running')} imported={bs.get('engine_imported')}"
            )
        return {"ok": True, "status": status_line, "state": state}
    except Exception:
        s = bridge.status()
        return {"ok": True, "status": s, "state": s}


@app.get("/api/perf")
def api_perf():
    try:
        from agent import agent_main as _am
        perf = getattr(_am, "RUNTIME_STATE", {}).get("perf", {})
        return {"ok": True, "perf": perf}
    except Exception:
        return {"ok": True, "perf": {}}


@app.post("/api/command")
async def api_command(cmd: CommandIn, request: Request):
    # Content-Type must be JSON for POST
    ctype = (request.headers.get("content-type") or "").lower()
    if "application/json" not in ctype:
        return JSONResponse({"ok": False, "error": "unsupported_media_type"}, status_code=415)
    # Optional token auth: if AGENT_TOKEN is set, require header X-Agent-Token
    if AGENT_TOKEN:
        provided = request.headers.get("x-agent-token", "").strip()
        if provided != AGENT_TOKEN:
            return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
    # Optional HMAC signing: if AGENT_SIGNING_KEY set, require timestamp + sig
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
        if not hmac.compare_digest(sig, digest):
            return JSONResponse({"ok": False, "error": "bad_signature"}, status_code=401)
    # Rate limit per client IP
    client_ip = request.client.host if request.client else "unknown"
    if not _rate_limit_ok(client_ip):
        return JSONResponse({"ok": False, "error": "rate_limited"}, status_code=429)

    action = cmd.action.value if isinstance(cmd.action, Action) else (str(cmd.action) or "").lower().strip()
    payload = cmd.payload or {}

    if action == "start":
        ok = bridge.start()
        return JSONResponse({"ok": ok, "running": bridge.is_running(), "status": bridge.status()})

    if action == "stop":
        ok = bridge.stop()
        return JSONResponse({"ok": ok, "running": bridge.is_running(), "status": bridge.status()})

    if action == "dictate":
        text = str(payload.get("text", "")).strip()
        if not text:
            return JSONResponse({"ok": False, "error": "Empty dictate text"}, status_code=400)
        if len(text) > MAX_TEXT_LEN:
            return JSONResponse({"ok": False, "error": "text_too_long"}, status_code=413)
        result = bridge.handle_text(text)
        result["running"] = bridge.is_running()
        return JSONResponse(result)

    if action == "status":
        return JSONResponse({"ok": True, "status": bridge.status()})

    if action == "set":
        # Apply runtime settings in agent_main if available
        try:
            from agent import agent_main as _am
            state = getattr(_am, "RUNTIME_STATE", {})
            changed = {}
            uv = payload.get("use_webrtcvad")
            if isinstance(uv, bool):
                state["use_webrtcvad"] = uv
                changed["use_webrtcvad"] = uv
            vb = payload.get("verbosity")
            if isinstance(vb, str) and vb.lower() in ("quiet","normal","verbose"):
                state["verbosity"] = vb.lower()
                changed["verbosity"] = state["verbosity"]
            return JSONResponse({"ok": True, "changed": changed, "state": state})
        except Exception as e:
            return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    return JSONResponse({"ok": False, "error": f"unknown action '{action}'"}, status_code=400)


def run():
    # Default to localhost-only; allow override with AGENT_HOST
    host = os.getenv("AGENT_HOST", "127.0.0.1")
    if host == "0.0.0.0" and not AGENT_TOKEN and not os.getenv("ALLOW_INSECURE"):
        print("[WARN] Controller bound to 0.0.0.0 without AGENT_TOKEN. Set AGENT_TOKEN or AGENT_HOST=127.0.0.1.")
    uvicorn.run(app, host=host, port=APP_PORT, log_level="info")


@app.middleware("http")
async def docs_guard(request: Request, call_next):
    # Gate /docs and /openapi.json if token is configured
    if request.url.path in ("/docs", "/openapi.json", "/redoc") and AGENT_TOKEN:
        token = request.headers.get("x-agent-token", "").strip()
        if token != AGENT_TOKEN:
            return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
    return await call_next(request)


@app.get("/api/logs")
def api_logs(lines: int = 200):
    try:
        n = max(1, min(int(lines), 2000))
    except Exception:
        n = 200
    try:
        if not LOG_FILE.exists():
            return JSONResponse({"ok": True, "lines": []})
        with LOG_FILE.open("r", encoding="utf-8", errors="ignore") as f:
            data = f.read().splitlines()
        tail = data[-n:]
        return JSONResponse({"ok": True, "lines": tail})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


def _auth_ok(request: Request) -> tuple[bool, JSONResponse | None]:
    # Optional token auth: if AGENT_TOKEN is set, require header X-Agent-Token
    if AGENT_TOKEN:
        provided = request.headers.get("x-agent-token", "").strip()
        if provided != AGENT_TOKEN:
            return False, JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
    # Optional HMAC signing
    if AGENT_SIGNING_KEY:
        ts = request.headers.get("x-agent-timestamp", "").strip()
        sig = request.headers.get("x-agent-sig", "").strip().lower()
        try:
            ts_i = int(ts)
        except Exception:
            return False, JSONResponse({"ok": False, "error": "missing_or_bad_timestamp"}, status_code=401)
        now = int(time.time())
        if abs(now - ts_i) > SIGNING_SKEW:
            return False, JSONResponse({"ok": False, "error": "timestamp_skew"}, status_code=401)
        # Note: caller ensures body read
    return True, None


@app.get("/api/macros")
def api_macros_get():
    try:
        src = MACROS_USER if MACROS_USER.exists() else MACROS_DEFAULT
        if not src.exists():
            return JSONResponse({"ok": True, "rules": [], "source": None})
        data = src.read_text(encoding="utf-8")
        return JSONResponse({"ok": True, "rules_raw": data, "source": str(src)})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.post("/api/macros")
async def api_macros_set(request: Request):
    # Auth
    ok, resp = _auth_ok(request)
    if not ok:
        return resp  # type: ignore[return-value]
    # Content type
    ctype = (request.headers.get("content-type") or "").lower()
    if "application/json" not in ctype:
        return JSONResponse({"ok": False, "error": "unsupported_media_type"}, status_code=415)
    # Body + HMAC
    body = await request.body()
    if AGENT_SIGNING_KEY:
        ts = request.headers.get("x-agent-timestamp", "").strip()
        digest = hmac.new(AGENT_SIGNING_KEY, str(ts).encode() + b"." + body, hashlib.sha256).hexdigest()
        provided = request.headers.get("x-agent-sig", "").strip().lower()
        if not hmac.compare_digest(provided, digest):
            return JSONResponse({"ok": False, "error": "bad_signature"}, status_code=401)
    # Parse and validate
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "bad_json"}, status_code=400)
    rules = payload.get("rules") if isinstance(payload, dict) else None
    if not isinstance(rules, list):
        return JSONResponse({"ok": False, "error": "rules_must_be_list"}, status_code=400)
    clean: list[dict] = []
    for idx, item in enumerate(rules):
        if not isinstance(item, dict):
            return JSONResponse({"ok": False, "error": f"rule_{idx}_not_object"}, status_code=400)
        m = str(item.get("match") or "").strip()
        r = str(item.get("rewrite") or "").strip()
        if not m or not r:
            return JSONResponse({"ok": False, "error": f"rule_{idx}_missing_fields"}, status_code=400)
        if len(m) > 200 or len(r) > 400:
            return JSONResponse({"ok": False, "error": f"rule_{idx}_too_long"}, status_code=400)
        clean.append({"match": m, "rewrite": r})
    try:
        MACROS_USER.parent.mkdir(parents=True, exist_ok=True)
        MACROS_USER.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"write_failed: {e}"}, status_code=500)
    # Reload in agent_main if available
    try:
        from agent import agent_main as _am
        count = _am.reload_macros_from_files()  # type: ignore[attr-defined]
    except Exception:
        count = None
    return JSONResponse({"ok": True, "saved": True, "count": count})


if __name__ == "__main__":
    run()
