"""
A thin, defensive bridge from the web controller to your existing decision engine.

It will call these optional functions in agent/decision_engine.py if present:
- start() -> None
- stop() -> None
- is_running() -> bool
- handle_text(command: str) -> dict | str | None
- status() -> dict | str

If a function is missing, the bridge safely no-ops or returns sensible defaults.
"""

from __future__ import annotations
from typing import Any, Optional

try:
    # Your existing engine
    from . import decision_engine as de  # type: ignore
except Exception as e:  # keep controller usable even if import fails
    de = None  # type: ignore
    _import_error = e
else:
    _import_error = None


class AgentBridge:
    def __init__(self) -> None:
        self._last_error: Optional[str] = None

    # --- lifecycle ---------------------------------------------
    def start(self) -> bool:
        try:
            if de and hasattr(de, "start"):
                de.start()  # type: ignore[attr-defined]
                return True
            # Fallback: try a common alt name
            if de and hasattr(de, "run"):
                de.run()  # type: ignore[attr-defined]
                return True
            self._last_error = "No start() or run() found in decision_engine.py"
            return False
        except Exception as e:
            self._last_error = f"start() error: {e}"
            return False

    def stop(self) -> bool:
        try:
            if de and hasattr(de, "stop"):
                de.stop()  # type: ignore[attr-defined]
                return True
            self._last_error = "No stop() found in decision_engine.py"
            return False
        except Exception as e:
            self._last_error = f"stop() error: {e}"
            return False

    # --- queries -----------------------------------------------
    def is_running(self) -> bool:
        try:
            if de and hasattr(de, "is_running"):
                return bool(de.is_running())  # type: ignore[attr-defined]
        except Exception:
            pass
        # Default to False if not provided
        return False

    def status(self) -> dict[str, Any]:
        base = {
            "engine_imported": de is not None,
            "engine_import_error": str(_import_error) if _import_error else None,
            "running": self.is_running(),
            "last_error": self._last_error,
        }
        try:
            if de and hasattr(de, "status"):
                s = de.status()  # type: ignore[attr-defined]
                if isinstance(s, dict):
                    base.update(s)
                else:
                    base["engine_status"] = str(s)
        except Exception as e:
            base["status_error"] = str(e)
        return base

    # --- commands ----------------------------------------------
    def handle_text(self, text: str) -> dict[str, Any]:
        try:
            if de and hasattr(de, "handle_text"):
                out = de.handle_text(text)  # type: ignore[attr-defined]
                return {"ok": True, "result": out}
            # Try a generic "handle" function
            if de and hasattr(de, "handle"):
                out = de.handle(text)  # type: ignore[attr-defined]
                return {"ok": True, "result": out}
            # Fallback: use respond(user_text, ...) if present
            if de and hasattr(de, "respond"):
                out = de.respond(text)  # type: ignore[attr-defined]
                return {"ok": True, "result": out}
            return {"ok": False, "error": "No handle_text(text), handle(text), or respond(text) found"}
        except Exception as e:
            self._last_error = f"handle_text() error: {e}"
            return {"ok": False, "error": str(e)}

