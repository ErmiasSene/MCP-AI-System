"""In-process MCP client.

Instead of spawning a subprocess, we import the FastMCP instance directly
and call its internal tool registry. This eliminates every stdio/anyio issue
while preserving the exact MCP concepts (tools/resources/prompts/schemas).
"""
import json
from typing import Any, Dict, List

from app.mcp_server import mcp  # our FastMCP instance


# ---------- helpers ----------

def _schema_for_tool(tool) -> Dict:
    """Convert an MCP Tool into OpenAI function-calling schema."""
    # mcp 1.x uses `inputSchema`, not `parameters`
    params = getattr(tool, "inputSchema", None) or getattr(tool, "parameters", {})
    if not isinstance(params, dict):
        params = params.model_dump() if hasattr(params, "model_dump") else {}
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": params,
        },
    }


# ---------- public API ----------

_tools_cache: List[Dict] | None = None


async def get_tools_schema_cached() -> List[Dict]:
    global _tools_cache
    if _tools_cache is None:
        result = await mcp.list_tools()  # returns ListToolsResult
        tools = getattr(result, "tools", result)  # unwrap if wrapped
        _tools_cache = [_schema_for_tool(t) for t in tools]
    return _tools_cache


async def list_tools_schema() -> List[Dict]:
    return await get_tools_schema_cached()


async def call_tool(name: str, args: Dict[str, Any]) -> Any:
    """Call an MCP tool in-process. Returns parsed JSON or string."""
    result = await mcp.call_tool(name, arguments=args)
    # call_tool returns a CallToolResult with `content` list
    content_list = getattr(result, "content", result)
    texts = [c.text for c in content_list if hasattr(c, "text")]
    joined = "\n".join(texts)
    try:
        return json.loads(joined)
    except Exception:
        return joined


async def list_resources() -> List[Dict]:
    result = await mcp.list_resources()
    resources = getattr(result, "resources", result)
    return [{"uri": str(r.uri), "name": r.name, "description": r.description}
            for r in resources]


async def list_prompts() -> List[Dict]:
    result = await mcp.list_prompts()
    prompts = getattr(result, "prompts", result)
    return [{"name": p.name, "description": p.description} for p in prompts]