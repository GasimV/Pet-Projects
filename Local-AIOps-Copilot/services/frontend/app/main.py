"""Streamlit Chat UI for Local-AIOps-Copilot."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
_PROJECT_ROOT = str(Path(__file__).resolve().parents[3])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import httpx
import streamlit as st

API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8080")


def init_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        import uuid

        st.session_state.session_id = str(uuid.uuid4())


def render_sidebar():
    with st.sidebar:
        st.title("Local-AIOps-Copilot")
        st.divider()

        st.subheader("Settings")
        st.session_state.use_tools = st.toggle("Enable Tool Calling", value=True)
        st.session_state.use_rag = st.toggle("Enable RAG Retrieval", value=True)
        st.session_state.stream_mode = st.toggle("Stream Responses", value=True)

        st.divider()
        st.subheader("Backend Info")
        try:
            resp = httpx.get(f"{API_GATEWAY_URL}/api/v1/backend/info", timeout=5)
            if resp.status_code == 200:
                info = resp.json()
                st.info(
                    f"**Backend:** {info['backend']}\n\n"
                    f"**Environment:** {info['environment']}\n\n"
                    f"**GPU Mode:** {info['is_gpu_mode']}"
                )
            else:
                st.warning("Could not fetch backend info")
        except Exception:
            st.error("API Gateway not reachable")

        st.divider()
        if st.button("Clear Chat"):
            st.session_state.messages = []
            import uuid

            st.session_state.session_id = str(uuid.uuid4())
            st.rerun()

        st.divider()
        st.subheader("Health")
        try:
            resp = httpx.get(f"{API_GATEWAY_URL}/health", timeout=5)
            if resp.status_code == 200:
                health = resp.json()
                status_color = "green" if health["status"] == "healthy" else "orange"
                st.markdown(f":{status_color}[{health['status'].upper()}]")
                st.caption(f"Agent: {'Connected' if health['agent_service'] else 'Disconnected'}")
            else:
                st.error("Health check failed")
        except Exception:
            st.error("Cannot reach API Gateway")


def send_message_sync(message: str) -> dict:
    """Send a non-streaming chat request."""
    try:
        resp = httpx.post(
            f"{API_GATEWAY_URL}/api/v1/chat",
            json={
                "message": message,
                "session_id": st.session_state.session_id,
                "use_tools": st.session_state.get("use_tools", True),
                "use_rag": st.session_state.get("use_rag", True),
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"content": f"Error: {e}", "sources": [], "tool_calls": []}


def send_message_stream(message: str):
    """Send a streaming chat request via SSE."""
    try:
        with httpx.stream(
            "POST",
            f"{API_GATEWAY_URL}/api/v1/chat/stream",
            json={
                "message": message,
                "session_id": st.session_state.session_id,
                "use_tools": st.session_state.get("use_tools", True),
                "use_rag": st.session_state.get("use_rag", True),
            },
            timeout=120,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    data_str = line[6:]
                    try:
                        data = json.loads(data_str)
                        if "token" in data:
                            yield data["token"]
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        yield f"Error: {e}"


def main():
    st.set_page_config(
        page_title="Local-AIOps-Copilot",
        page_icon="🤖",
        layout="wide",
    )

    init_session_state()
    render_sidebar()

    st.header("Chat")

    # Render chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander("Sources"):
                    for src in msg["sources"]:
                        st.caption(src)
            if msg.get("tool_calls"):
                with st.expander("Tool Calls"):
                    for tc in msg["tool_calls"]:
                        st.json(tc)

    # Chat input
    if prompt := st.chat_input("Ask me anything about your infrastructure..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            if st.session_state.get("stream_mode", True):
                response_placeholder = st.empty()
                full_response = ""
                for token in send_message_stream(prompt):
                    full_response += token
                    response_placeholder.markdown(full_response + "▌")
                response_placeholder.markdown(full_response)
                st.session_state.messages.append(
                    {"role": "assistant", "content": full_response}
                )
            else:
                with st.spinner("Thinking..."):
                    result = send_message_sync(prompt)
                st.markdown(result["content"])
                msg_data: dict = {"role": "assistant", "content": result["content"]}
                if result.get("sources"):
                    msg_data["sources"] = result["sources"]
                    with st.expander("Sources"):
                        for src in result["sources"]:
                            st.caption(src)
                if result.get("tool_calls"):
                    msg_data["tool_calls"] = result["tool_calls"]
                    with st.expander("Tool Calls"):
                        for tc in result["tool_calls"]:
                            st.json(tc)
                st.session_state.messages.append(msg_data)


if __name__ == "__main__":
    main()
