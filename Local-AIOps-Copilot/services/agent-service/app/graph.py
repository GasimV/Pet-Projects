"""LangGraph agent — routes user requests through tools, RAG, and LLM."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated, Any, TypedDict

_PROJECT_ROOT = str(Path(__file__).resolve().parents[3])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from shared.config import get_settings
from shared.llm_backend import LLMClient, LLMMessage, create_llm_client
from shared.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class AgentState(TypedDict):
    messages: Annotated[list[dict], add_messages]
    session_id: str
    use_tools: bool
    use_rag: bool
    rag_context: str
    tool_results: list[dict]
    final_response: str


class AgentGraph:
    """LangGraph-based agent with pluggable LLM backend."""

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        rag_client: Any = None,
        tool_registry: dict[str, Any] | None = None,
    ):
        self.llm = llm_client or create_llm_client()
        self.rag_client = rag_client
        self.tool_registry = tool_registry or {}
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(AgentState)

        graph.add_node("route", self._route_node)
        graph.add_node("retrieve", self._retrieve_node)
        graph.add_node("call_tools", self._tool_node)
        graph.add_node("generate", self._generate_node)

        graph.set_entry_point("route")

        graph.add_conditional_edges(
            "route",
            self._should_retrieve_or_generate,
            {
                "retrieve": "retrieve",
                "call_tools": "call_tools",
                "generate": "generate",
            },
        )
        graph.add_edge("retrieve", "generate")
        graph.add_edge("call_tools", "generate")
        graph.add_edge("generate", END)

        return graph.compile()

    async def _route_node(self, state: AgentState) -> AgentState:
        logger.debug("routing", session_id=state.get("session_id"))
        return state

    def _should_retrieve_or_generate(self, state: AgentState) -> str:
        if state.get("use_rag") and self.rag_client:
            return "retrieve"
        if state.get("use_tools") and self.tool_registry:
            return "call_tools"
        return "generate"

    async def _retrieve_node(self, state: AgentState) -> dict:
        messages = state.get("messages", [])
        last_msg = messages[-1] if messages else {}
        query = last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg)

        context = ""
        if self.rag_client:
            try:
                chunks = await self.rag_client.retrieve(query, top_k=3)
                context = "\n\n".join(
                    f"[Source: {c.get('document_id', 'unknown')}]\n{c.get('content', '')}"
                    for c in chunks
                )
            except Exception as e:
                logger.error("rag_retrieve_error", error=str(e))
                context = ""

        return {"rag_context": context}

    async def _tool_node(self, state: AgentState) -> dict:
        messages = state.get("messages", [])
        last_msg = messages[-1] if messages else {}
        user_text = last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg)

        # Ask the LLM if it wants to use any tools
        tool_definitions = [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": getattr(tool, "description", f"Tool: {name}"),
                    "parameters": getattr(tool, "parameters", {"type": "object", "properties": {}}),
                },
            }
            for name, tool in self.tool_registry.items()
        ]

        llm_messages = [LLMMessage(role=m.get("role", "user"), content=m.get("content", "")) for m in messages]
        response = await self.llm.chat(llm_messages, tools=tool_definitions)

        tool_results = []
        if response.tool_calls:
            for tc in response.tool_calls:
                func_name = tc.get("function", {}).get("name", "")
                func_args = tc.get("function", {}).get("arguments", "{}")
                tool = self.tool_registry.get(func_name)
                if tool:
                    try:
                        import json
                        args = json.loads(func_args) if isinstance(func_args, str) else func_args
                        result = await tool.execute(**args) if hasattr(tool, "execute") else str(tool)
                        tool_results.append({
                            "tool_name": func_name,
                            "arguments": func_args,
                            "result": str(result),
                        })
                    except Exception as e:
                        tool_results.append({
                            "tool_name": func_name,
                            "arguments": func_args,
                            "result": f"Error: {e}",
                        })

        return {"tool_results": tool_results}

    async def _generate_node(self, state: AgentState) -> dict:
        messages = state.get("messages", [])
        rag_context = state.get("rag_context", "")
        tool_results = state.get("tool_results", [])

        system_prompt = (
            "You are Local-AIOps-Copilot, an AI assistant for infrastructure operations, "
            "MLOps, and release management. You help with monitoring, debugging, deployments, "
            "and operational decisions. Be concise and actionable."
        )

        if rag_context:
            system_prompt += f"\n\nRelevant context from documents:\n{rag_context}"

        if tool_results:
            tool_info = "\n".join(
                f"Tool '{tr['tool_name']}' returned: {tr['result']}" for tr in tool_results
            )
            system_prompt += f"\n\nTool results:\n{tool_info}"

        llm_messages = [LLMMessage(role="system", content=system_prompt)]
        for m in messages:
            role = m.get("role", "user") if isinstance(m, dict) else "user"
            content = m.get("content", "") if isinstance(m, dict) else str(m)
            llm_messages.append(LLMMessage(role=role, content=content))

        response = await self.llm.chat(llm_messages)
        return {"final_response": response.content}

    async def run(
        self,
        session_id: str,
        message: str,
        history: list[dict] | None = None,
        use_tools: bool = True,
        use_rag: bool = True,
    ) -> dict:
        messages = list(history or [])
        messages.append({"role": "user", "content": message})

        initial_state: AgentState = {
            "messages": messages,
            "session_id": session_id,
            "use_tools": use_tools,
            "use_rag": use_rag,
            "rag_context": "",
            "tool_results": [],
            "final_response": "",
        }

        result = await self.graph.ainvoke(initial_state)
        return {
            "content": result.get("final_response", ""),
            "tool_calls": result.get("tool_results", []),
            "sources": [],
        }

    async def run_stream(
        self,
        session_id: str,
        message: str,
        history: list[dict] | None = None,
        use_tools: bool = True,
        use_rag: bool = True,
    ):
        """Stream the final generation step."""
        messages = list(history or [])
        messages.append({"role": "user", "content": message})

        system_prompt = (
            "You are Local-AIOps-Copilot, an AI assistant for infrastructure operations, "
            "MLOps, and release management."
        )

        llm_messages = [LLMMessage(role="system", content=system_prompt)]
        for m in messages:
            role = m.get("role", "user") if isinstance(m, dict) else "user"
            content = m.get("content", "") if isinstance(m, dict) else str(m)
            llm_messages.append(LLMMessage(role=role, content=content))

        async for token in self.llm.stream(llm_messages):
            yield token
