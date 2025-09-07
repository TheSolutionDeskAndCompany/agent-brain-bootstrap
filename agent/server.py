import os
from pathlib import Path
from typing import Optional, Dict, Any

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Bridge that safely calls optional functions in decision_engine
from .controller_bridge import AgentBridge

APP_PORT = int(os.getenv("AGENT_PORT", "8765"))
PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"

app = FastAPI(title="AgentBrain Controller")
bridge = AgentBridge()

if PUBLIC_DIR.exists():
    app.mount("/public", StaticFiles(directory=str(PUBLIC_DIR)), name="public")


class CommandIn(BaseModel):
    action: str
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


@app.post("/api/command")
async def api_command(cmd: CommandIn):
    action = (cmd.action or "").lower().strip()
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
        result = bridge.handle_text(text)
        result["running"] = bridge.is_running()
        return JSONResponse(result)

    if action == "status":
        return JSONResponse({"ok": True, "status": bridge.status()})

    return JSONResponse({"ok": False, "error": f"unknown action '{action}'"}, status_code=400)


def run():
    # If you prefer, change to host="127.0.0.1" to limit to local-only
    uvicorn.run(app, host="0.0.0.0", port=APP_PORT, log_level="info")


if __name__ == "__main__":
    run()
