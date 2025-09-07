from fastapi import FastAPI
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/agent")
async def agent(req: AgentRequest):
    return {"output": run_agent(req.input.strip())}


@app.get("/healthz")
async def healthz():
    return {"ok": True}


# Static hosting for mobile UI and RDP profiles
if os.path.isdir("public"):
    app.mount("/public", StaticFiles(directory="public"), name="public")
if os.path.isdir("public/rdp"):
    app.mount("/rdp", StaticFiles(directory="public/rdp"), name="rdp")


if __name__ == "__main__":
    uvicorn.run("mobile_server:app", host="0.0.0.0", port=8000, reload=True)

