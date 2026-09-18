"""Agent loop: Gemini tool-calling + in-process MCP tool execution."""
import asyncio
import json
from typing import AsyncGenerator, Dict, List, Any, Callable, Awaitable

from app.llm import chat_with_tools, chat_text


SYSTEM_PROMPT = (
    "You are a helpful e-commerce analyst assistant. You have access to tools "
    "that query the shop database and search product documentation.\n\n"
    "Rules:\n"
    "- Use tools to answer questions that require data.\n"
    "- Combine results from multiple tools when helpful.\n"
    "- For documentation/policy questions, use search_docs.\n"
    "- Always explain your reasoning briefly in the final answer.\n"
    "- If a tool returns an error, say so honestly.\n"
    "- After gathering all necessary data, provide a clear, concise answer."
)


async def run_agent(query: str,
                    tools_schema: List[Dict],
                    call_tool: Callable[[str, Dict], Awaitable[Any]],
                    max_turns: int = 6) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Yields events:
      {"type": "tool_call",   "tool": ..., "args": ...}
      {"type": "tool_result", "tool": ..., "result": ...}
      {"type": "answer",      "text": ...}
    """
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query},
    ]

    for turn in range(max_turns):
        try:
            msg = await asyncio.to_thread(chat_with_tools, messages, tools_schema)
        except Exception as e:
            yield {"type": "answer", "text": f"Error calling LLM: {str(e)}"}
            return

        # Case 1: LLM returned tool calls
        if msg.tool_calls:
            # Append assistant message with tool calls
            assistant_msg = {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
            }
            messages.append(assistant_msg)

            # Execute each tool
            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}

                yield {"type": "tool_call", "tool": name, "args": args}

                try:
                    result = await call_tool(name, args)
                    tool_content = json.dumps(result, default=str)
                except Exception as e:
                    result = {"error": str(e)}
                    tool_content = json.dumps(result)

                # Append tool result
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": name,  # Add name for Gemini matching
                    "content": tool_content,
                })
                yield {"type": "tool_result", "tool": name, "result": result}
            continue

        # Case 2: LLM returned final answer
        if msg.content and msg.content.strip():
            yield {"type": "answer", "text": msg.content}
            return
        
        # Case 3: Empty response — force a summary
        messages.append({
            "role": "user",
            "content": "Please provide your final answer based on the tool results above."
        })
        continue

    # Safety: if we exhausted turns, force a final answer
    try:
        fallback = await asyncio.to_thread(
            chat_text,
            messages + [{
                "role": "user",
                "content": "Summarize your findings and provide a final answer now."
            }]
        )
        yield {"type": "answer", "text": fallback or "I gathered the data but couldn't generate a summary."}
    except Exception as e:
        yield {"type": "answer", "text": f"Error generating final answer: {str(e)}"}