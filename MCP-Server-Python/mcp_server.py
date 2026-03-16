"""
MCP Server with demo tools.

Exposes a calculator, a unit converter, and a text analysis tool
via the Model Context Protocol.

Run:
    python mcp_server.py          # stdio transport (used by agent.py)
    python mcp_server.py --sse    # SSE transport on http://localhost:8000/sse
"""

import math
import sys

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("demo-tools")


# ── Tool 1: Calculator ──────────────────────────────────────────────────────

@mcp.tool()
def calculate(expression: str) -> str:
    """
    Evaluate a math expression and return the result.

    Supports basic arithmetic (+, -, *, /, **), parentheses,
    and common math functions (sqrt, sin, cos, log, pi, e).

    Examples: "2 + 3 * 4", "sqrt(144)", "log(100)", "pi * 3**2"
    """
    allowed_names = {
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log10,
        "ln": math.log,
        "abs": abs,
        "round": round,
        "pi": math.pi,
        "e": math.e,
    }
    try:
        result = eval(expression, {"__builtins__": {}}, allowed_names)  # noqa: S307
        return str(result)
    except Exception as exc:
        return f"Error: {exc}"


# ── Tool 2: Unit converter ──────────────────────────────────────────────────

CONVERSIONS: dict[str, dict[str, float]] = {
    "km_to_miles": {"factor": 0.621371},
    "miles_to_km": {"factor": 1.60934},
    "kg_to_lbs": {"factor": 2.20462},
    "lbs_to_kg": {"factor": 0.453592},
    "celsius_to_fahrenheit": {"factor": 1.8, "offset": 32},
    "fahrenheit_to_celsius": {"factor": 1 / 1.8, "offset": -32 / 1.8},
}


@mcp.tool()
def convert_units(value: float, conversion: str) -> str:
    """
    Convert a numeric value between common units.

    Available conversions:
      km_to_miles, miles_to_km,
      kg_to_lbs, lbs_to_kg,
      celsius_to_fahrenheit, fahrenheit_to_celsius

    Examples: convert_units(100, "km_to_miles") → "62.1371"
    """
    conv = CONVERSIONS.get(conversion)
    if conv is None:
        available = ", ".join(CONVERSIONS)
        return f"Unknown conversion '{conversion}'. Available: {available}"
    result = value * conv["factor"] + conv.get("offset", 0)
    return f"{round(result, 4)}"


# ── Tool 3: Text analysis ───────────────────────────────────────────────────

@mcp.tool()
def analyze_text(text: str) -> str:
    """
    Return basic statistics about a piece of text:
    character count, word count, sentence count, and average word length.
    """
    chars = len(text)
    words = text.split()
    word_count = len(words)
    sentence_count = sum(text.count(p) for p in ".!?") or 1
    avg_word_len = round(sum(len(w) for w in words) / max(word_count, 1), 2)
    return (
        f"Characters: {chars}, Words: {word_count}, "
        f"Sentences: {sentence_count}, Avg word length: {avg_word_len}"
    )


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if "--sse" in sys.argv:
        mcp.run(transport="sse")
    else:
        mcp.run()
