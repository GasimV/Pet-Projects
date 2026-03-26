from __future__ import annotations

import json

try:
    from langchain_ollama import ChatOllama
except Exception:  # pragma: no cover
    ChatOllama = None


class ToolPlanner:
    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url
        self._model = model

    async def plan(self, prompt: str) -> dict | None:
        lowered = prompt.lower()
        if "status" in lowered:
            return {"name": "get_system_status", "arguments_json": "{}"}
        if "capabilities" in lowered:
            return {"name": "list_capabilities", "arguments_json": "{}"}
        if "domain" in lowered or "mode" in lowered:
            return {"name": "get_domain_mode", "arguments_json": "{}"}
        if "manual" in lowered or "search" in lowered:
            return {"name": "search_manuals", "arguments_json": json.dumps({"query": prompt})}

        if ChatOllama is None:
            return None

        llm = ChatOllama(model=self._model, base_url=self._base_url)
        result = await llm.ainvoke(
            [
                (
                    "system",
                    "Decide whether exactly one tool is needed. Reply with JSON only: "
                    '{"name": "...", "arguments_json": "..."} or null.',
                ),
                ("human", prompt),
            ]
        )
        content = getattr(result, "content", "") or ""
        try:
            if content.strip().lower() == "null":
                return None
            return json.loads(content)
        except Exception:
            return None

