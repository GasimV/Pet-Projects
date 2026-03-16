"""
AI Agent that connects to the MCP server and uses Gemma for tool calling.

The agent:
  1. Starts the MCP server as a subprocess.
  2. Discovers available tools.
  3. Converts them to the format Gemma expects.
  4. Runs an interactive loop: user prompt → LLM → tool calls → response.

Usage:
    python agent.py
    python agent.py --model google/gemma-3-1b-it   # use a different gated model
    python agent.py --model Qwen/Qwen2.5-1.5B-Instruct # use an ungated model
"""

import argparse
import asyncio
import json
import re
import sys

import torch
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from transformers import AutoModelForCausalLM, AutoTokenizer

DEFAULT_MODEL = "google/gemma-3-4b-it"


# ── Model loading ────────────────────────────────────────────────────────────

def load_model(model_id: str):
    """Load model and tokenizer with GPU if available, else CPU."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    print(f"Loading {model_id} on {device} ({dtype}) ...")

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        dtype=dtype,
        device_map="auto" if device == "cuda" else None,
    )
    if device == "cpu":
        model = model.to(device)

    print("Model ready.\n")
    return model, tokenizer, device


# ── MCP → Gemma tool schema conversion ───────────────────────────────────────

def mcp_tools_to_gemma(mcp_tools: list) -> list[dict]:
    """Convert MCP tool definitions to the dict format Gemma expects."""
    gemma_tools = []
    for tool in mcp_tools:
        properties = {}
        required = []
        if tool.inputSchema and "properties" in tool.inputSchema:
            for name, prop in tool.inputSchema["properties"].items():
                properties[name] = {
                    "type": prop.get("type", "string"),
                    "description": prop.get("description", ""),
                }
            required = tool.inputSchema.get("required", list(properties.keys()))

        gemma_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        })
    return gemma_tools


# ── LLM inference ────────────────────────────────────────────────────────────

def generate_response(
    model, tokenizer, device, messages: list, tools: list[dict]
) -> str:
    """Run the model on a chat with tool definitions and return raw text."""
    text = tokenizer.apply_chat_template(
        messages,
        tools=tools,
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=512,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
        )
    # Decode only the new tokens
    new_tokens = output_ids[0][inputs["input_ids"].shape[-1]:]
    return tokenizer.decode(new_tokens, skip_special_tokens=False)


# ── Parsing tool calls from model output ─────────────────────────────────────

def parse_tool_calls(text: str) -> list[dict]:
    """
    Extract tool calls from the model output.

    Supports multiple formats:
      - Qwen-style <tool_call>...</tool_call> tags
      - Gemma-style ```tool_call ... ``` code blocks
      - ```python/json ... ``` code blocks
      - Bare JSON objects with "name" key (handles nested braces)
    """
    calls: list[dict] = []

    # Pattern 1: <tool_call>...</tool_call> tags (Qwen format)
    for block in re.findall(r"<tool_call>\s*(.*?)\s*</tool_call>", text, re.DOTALL):
        try:
            data = json.loads(block.strip())
            if isinstance(data, list):
                calls.extend(data)
            elif isinstance(data, dict):
                calls.append(data)
        except json.JSONDecodeError:
            pass

    # Pattern 2: ```tool_call ... ``` blocks (Gemma format)
    if not calls:
        for block in re.findall(r"```tool_call\s*(.*?)```", text, re.DOTALL):
            try:
                data = json.loads(block.strip())
                if isinstance(data, list):
                    calls.extend(data)
                else:
                    calls.append(data)
            except json.JSONDecodeError:
                pass

    # Pattern 3: ```python/json ... ``` blocks
    if not calls:
        for block in re.findall(r"```(?:python|json)?\s*(.*?)```", text, re.DOTALL):
            try:
                data = json.loads(block.strip())
                if isinstance(data, dict) and "name" in data:
                    calls.append(data)
            except json.JSONDecodeError:
                pass

    # Pattern 4: bare JSON objects with "name" key (greedy brace matching)
    if not calls:
        for m in re.finditer(r'\{', text):
            start = m.start()
            depth = 0
            for i in range(start, len(text)):
                if text[i] == '{':
                    depth += 1
                elif text[i] == '}':
                    depth -= 1
                if depth == 0:
                    candidate = text[start:i + 1]
                    try:
                        data = json.loads(candidate)
                        if isinstance(data, dict) and "name" in data:
                            calls.append(data)
                    except json.JSONDecodeError:
                        pass
                    break

    return calls


# ── Main agent loop ──────────────────────────────────────────────────────────

async def agent_loop(model_id: str):
    """Start MCP server, discover tools, and run the interactive agent."""
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["mcp_server.py"],
    )

    print("Connecting to MCP server ...")
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # Discover tools
            tools_result = await session.list_tools()
            mcp_tools = tools_result.tools
            gemma_tools = mcp_tools_to_gemma(mcp_tools)

            print(f"Connected. Available tools: "
                  f"{[t['function']['name'] for t in gemma_tools]}\n")

            # Load model
            model, tokenizer, device = load_model(model_id)

            print("=" * 60)
            print("  MCP + Gemma Agent  (type 'quit' to exit)")
            print("=" * 60)

            while True:
                try:
                    user_input = input("\nYou: ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if not user_input or user_input.lower() in ("quit", "exit"):
                    break

                messages = [
                    {
                        "role": "user",
                        "content": user_input,
                    },
                ]

                # Step 1: ask the model
                raw = generate_response(model, tokenizer, device, messages, gemma_tools)

                # Step 2: check for tool calls
                tool_calls = parse_tool_calls(raw)

                if tool_calls:
                    print(f"\n[Agent calling {len(tool_calls)} tool(s) ...]")
                    tool_results = []
                    for tc in tool_calls:
                        name = tc.get("name", "")
                        args = tc.get("arguments", tc.get("parameters", {}))
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except json.JSONDecodeError:
                                args = {}
                        print(f"  → {name}({args})")
                        try:
                            result = await session.call_tool(name, args)
                            content = result.content[0].text if result.content else ""
                        except Exception as exc:
                            content = f"Error: {exc}"
                        tool_results.append({"tool": name, "result": content})
                        print(f"    ← {content}")

                    # Step 3: feed results back to the model for a final answer
                    tool_summary = "\n".join(
                        f"{r['tool']} returned: {r['result']}" for r in tool_results
                    )
                    messages.append({"role": "assistant", "content": raw})
                    messages.append({
                        "role": "user",
                        "content": (
                            f"Here are the tool results:\n{tool_summary}\n\n"
                            "Please give a concise final answer."
                        ),
                    })
                    final = generate_response(
                        model, tokenizer, device, messages, gemma_tools
                    )
                    # Strip any remaining special tokens for display
                    final = re.sub(r"<[^>]+>", "", final).strip()
                    print(f"\nAssistant: {final}")
                else:
                    # No tool call — direct answer
                    display = re.sub(r"<[^>]+>", "", raw).strip()
                    print(f"\nAssistant: {display}")

    print("\nGoodbye!")


# ── CLI entry point ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MCP + Gemma Agent")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"HuggingFace model ID (default: {DEFAULT_MODEL})",
    )
    args = parser.parse_args()
    asyncio.run(agent_loop(args.model))


if __name__ == "__main__":
    main()
