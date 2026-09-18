"""FastAPI backend — in-process MCP, no subprocess needed."""
import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from app.mcp_client import (get_tools_schema_cached, list_resources,
                            list_prompts, call_tool, list_tools_schema)
from app.agent import run_agent

app = FastAPI(title="MCP AI System", version="1.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tools")
async def tools():
    return await get_tools_schema_cached()


@app.get("/resources")
async def resources():
    return await list_resources()


@app.get("/prompts")
async def prompts():
    return await list_prompts()


@app.post("/chat")
async def chat(req: ChatRequest):
    """SSE stream of tool-call events + final answer."""
    tools_schema = await list_tools_schema()

    async def gen():
        try:
            async for event in run_agent(req.message, tools_schema, call_tool):
                yield "data: " + json.dumps(event, default=str) + "\n\n"
        except Exception as e:
            yield ("data: " + json.dumps({"type": "answer",
                                          "text": "Error: " + str(e)}) + "\n\n")
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache"})


@app.get("/", response_class=HTMLResponse)
def index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())