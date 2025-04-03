---

# 🤖 LangChain Chat with an LLM

This is a simple hands-on LangChain project to understand how to use LangChain with OpenAI models and Streamlit. It creates a lightweight chat interface where you can talk to an AI assistant.

---

## 🔧 Features

- ✅ Chat with an OpenAI model using LangChain
- ✅ Built-in chat memory (session-based)
- ✅ Streamlit-powered web UI
- ✅ Modular and beginner-friendly

---

## 🧠 Tech Stack

- [LangChain](https://docs.langchain.com/) – Framework for building LLM apps
- [OpenAI](https://platform.openai.com/) – Language model provider
- [Streamlit](https://streamlit.io/) – Web UI
- [Python dotenv](https://pypi.org/project/python-dotenv/) – For API key management

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/GasimV/Pet_Projects/LangChain Chat with an LLM.git
cd "LangChain Chat with an LLM"
```

### 2. Install Dependencies

It's best to use a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
```

Install:

```bash
pip install streamlit langchain langchain-openai python-dotenv
```

### 3. Set Up Your API Key

Create a `.env` file in the root of the project:

```
OPENAI_API_KEY=your_openai_api_key_here
```

You can get your key from https://platform.openai.com/account/api-keys

---

## 💬 Run the App

```bash
streamlit run langchain_chat_app.py
```

Visit http://localhost:8501 in your browser.

---

## 📁 Project Structure

```
.
├── langchain_chat_app.py   # Main chat app
├── .env                    # Your API key (not committed)
├── README.md

```

---

## 🧩 Next Steps

- Add **memory** using `ConversationBufferMemory`
- Add **tools/agents** like calculator or web search
- Swap in **local models** (like DeepSeek, Ollama, Llama.cpp)
- Integrate **LangSmith** for tracing/debugging

---

## 📜 License

MIT — free for personal and commercial use.

---