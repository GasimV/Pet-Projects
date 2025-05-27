# NORMA – My Legal AI Search & Advisor Pet Project 🇦🇿

**NORMA** (*Normative Legal Acts Intelligent Search and Advisor System*) is a personal passion project I built to explore the intersection of artificial intelligence and legal informatics. It's a smart, AI-powered platform designed to help users quickly retrieve accurate legal information from Azerbaijani legislation using natural language queries.

---

## 💡 Why I Built This

I wanted to create a tool that makes complex legal information more accessible — not just to lawyers, but to students, business owners, and anyone in need of clear, authoritative legal guidance in Azerbaijan. The existing systems often rely on outdated keyword search and miss out on the power of semantic understanding. NORMA was my attempt to solve this using modern AI techniques.

---

## 🎯 What It Does

- Translates **natural language legal questions** into accurate, document-cited responses
- Uses **semantic search** to retrieve relevant articles, clauses, and sub-clauses
- Displays results with **direct URLs** to official legal documents
- Enforces daily user **query limits** to simulate real-world usage
- Includes **feedback mechanisms** and user authentication

---

## ⚙️ Technical Stack

This project combines full-stack web development with modern AI/NLP workflows:

### 💻 Backend
- **Django (Python)** – core backend and web framework
- **PostgreSQL** – stores user queries, profiles, and feedback
- **Django Auth System** – user management, rate limiting, profile updates

### 🤖 AI Engine
- **SentenceTransformer** (fine-tuned) – for embedding legal corpus
- **OpenAI GPT-4o** – for generating context-aware legal responses
- **Parquet + PyArrow** – to store dense vector embeddings and metadata
- **tiktoken** – for precise token count estimation and prompt control

### 🔍 Search Pipeline
1. Clean and parse user query
2. Perform **semantic similarity** matching on the legal corpus
3. Build a GPT prompt from the top-k most relevant legal passages
4. Query OpenAI's model with the constructed context
5. Return a structured response and log everything for later fine-tuning

---

## 🚀 Features

- Natural language interface for Azerbaijani legal system
- Smart prompt generation within a 30,000-token budget
- Semantic and keyword filtering combined
- AI responds **in Azerbaijani**, acting as a legal expert
- Feedback submission for continuous improvement
- Daily query limits (10/day/user) to control usage
- Easily expandable legal corpus

---

## 📈 Future Goals

- Partner with **local legal professionals** for validation
- Integrate document upload and **custom legal contract analysis**
- Build an **admin dashboard** for corpus updates and query analytics

---

## 🙌 Final Thoughts

NORMA is my way of exploring how modern machine learning can serve society beyond the hype. It’s not perfect, but I believe projects like this can pave the way for smarter, more accessible public services — starting with the law.

Feel free to reach out if you’re interested in collaborating or adapting this for another legal system or domain!

—
Built with ❤️ & 🇦🇿