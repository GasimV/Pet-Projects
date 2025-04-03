import os
from dotenv import load_dotenv
import streamlit as st
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

# Load API key
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

# Set up LangChain Chat model
llm = ChatOpenAI(temperature=0.7, openai_api_key=openai_api_key)

# Streamlit UI
st.set_page_config(page_title="LangChain Chat")
st.title("🤖 Chat with LangChain")

# Keep chat history in session
if "messages" not in st.session_state:
    st.session_state.messages = [
        SystemMessage(content="You are a helpful assistant.")
    ]

# User input
user_input = st.text_input("Your message:", key="user_input")

if st.button("Send") and user_input:
    st.session_state.messages.append(HumanMessage(content=user_input))

    # Get response
    response = llm.invoke(st.session_state.messages)
    st.session_state.messages.append(response)

# Display chat
for msg in st.session_state.messages:
    if isinstance(msg, HumanMessage):
        st.markdown(f"**You:** {msg.content}")
    elif isinstance(msg, SystemMessage):
        st.markdown(f"**System:** {msg.content}")
    else:
        st.markdown(f"**AI:** {msg.content}")
