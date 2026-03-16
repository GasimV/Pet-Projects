# MCP Server + AI Agent (Python)

A minimal Python project demonstrating the **Model Context Protocol (MCP)** with local LLM tool calling using **Gemma**.

The MCP server exposes three demo tools. The agent connects to the server, discovers the tools at runtime, and uses LLM to decide when and how to call them.

## Architecture

```
┌──────────────┐    stdio/SSE    ┌──────────────┐
│  agent.py    │◄──────────────► │ mcp_server.py│
│  (LLM)       │                 │  (FastMCP)   │
└──────────────┘                 └──────────────┘
        │                             │
   User prompt                  3 demo tools:
   ↕ Tool calls                  • calculate
   ↕ Final answer                • convert_units
                                 • analyze_text
```

## Tools

| Tool | Description | Example |
|------|-------------|---------|
| `calculate` | Evaluate math expressions (`+`, `-`, `*`, `/`, `sqrt`, `sin`, `pi`, …) | `calculate("pi * 3**2")` → `28.2743…` |
| `convert_units` | Convert between common units (km↔miles, kg↔lbs, °C↔°F) | `convert_units(100, "km_to_miles")` → `62.1371` |
| `analyze_text` | Character, word & sentence counts plus average word length | `analyze_text("Hello world!")` → stats |

## Setup

```bash
# Clone (or navigate to the project folder)
git clone https://github.com/GasimV/Pet-Projects.git
cd Pet-Projects/MCP-Server-Python

# Create & activate virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

> **GPU support:** If you have an NVIDIA GPU, install the CUDA-enabled PyTorch
> *before* the other requirements:
> ```bash
> pip install torch --index-url https://download.pytorch.org/whl/cu130
> pip install -r requirements.txt
> ```
> The agent auto-detects GPU availability and falls back to CPU.

## Usage

### Run the interactive agent

```bash
python agent.py
```

On first run the LLM model (~8 GB for 4B Gemma) will be downloaded and cached by HuggingFace.

Use a smaller model if memory is tight:

```bash
python agent.py --model google/gemma-3-1b-it
```

### Example session

```
You: What is the square root of 1764?
[Agent calling 1 tool(s) ...]
  → calculate({"expression": "sqrt(1764)"})
    ← 42.0
Assistant: The square root of 1764 is 42.

You: Convert 30 degrees Celsius to Fahrenheit
[Agent calling 1 tool(s) ...]
  → convert_units({"value": 30, "conversion": "celsius_to_fahrenheit"})
    ← 86.0
Assistant: 30 °C is equal to 86 °F.

You: Analyze this text: MCP makes tool calling easy and fun
[Agent calling 1 tool(s) ...]
  → analyze_text({"text": "MCP makes tool calling easy and fun"})
    ← Characters: 35, Words: 7, Sentences: 1, Avg word length: 4.14
Assistant: The text has 35 characters, 7 words, 1 sentence, with an average word length of 4.14.
```

### Run the MCP server standalone (SSE mode)

```bash
python mcp_server.py --sse
# Server listening on http://localhost:8000/sse
```

This lets you connect any MCP-compatible client (Claude Desktop, other agents, etc.).

## Project Structure

```
MCP-Server-Python/
├── mcp_server.py       # MCP server with 3 demo tools
├── agent.py            # Interactive AI agent (Gemma + MCP client)
├── requirements.txt
├── .gitignore
└── README.md
```

## Requirements

- Python 3.10+
- ~8 GB RAM/VRAM for Gemma 3 4B (or ~3 GB for 1B variant)
- Optional: NVIDIA GPU with CUDA for faster inference

## License

MIT
