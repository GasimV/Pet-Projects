# Azerbaijani Labor Law QA Bot 🤖⚖️

This project is an **AI-powered Question-Answering (QA) system** built on top of **Google Generative AI** and **FAISS**, designed to answer questions based on the **Labor Code of Azerbaijan**.  
It also includes a **Telegram Bot** integration for easy interaction.

---

## 🚀 Features
- 📑 **Retrieval-Augmented Generation (RAG):** Uses FAISS for efficient legal text retrieval.  
- ⚖️ **Domain-Specific:** Answers are grounded in the Azerbaijani Labor Code.  
- 🤖 **Telegram Bot:** Ask questions directly via Telegram.  
- 🔒 **Secure Config:** `.env` file used for API keys & tokens.  

---

## ⚙️ Setup

1. Create a `.env` file in the project root:

   ```env
   GOOGLE_API_KEY=your_google_api_key
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   ```

2. Generate embeddings:

   ```bash
   jupyter notebook embedding_generator.ipynb
   ```

   This creates:

   * `law_embeddings.faiss`
   * `chunks_for_retrieval.pkl`

3. Run the QA system locally:

   ```bash
   python qa_system.py
   ```

4. Start the Telegram bot:

   ```bash
   python telegram_bot.py
   ```

---

## 📂 Project Structure

```
Task/
│── embedding_generator.ipynb     # Creates embeddings for legal texts
│── qa_system.py                  # Core RAG-based QA system
│── telegram_bot.py               # Telegram bot interface
│── labor_law_chunks.json         # Preprocessed chunks of Labor Code
│── law_embeddings.faiss          # FAISS index
│── chunks_for_retrieval.pkl      # Serialized chunks for retrieval
│── requirements.txt              # Dependencies
│── .env                          # API keys (not included in GitHub)
│── Seçilmiş Əsas Məsələlər.txt   # Sample Azerbaijani labor law notes
```

---

## 📌 Example Usage

**Telegram:**

* "Minimum məzuniyyət müddəti neçə gündür?"
* "Sınaq müddəti nə qədər ola bilər?"
* "Əmək müqaviləsinə hansı halda xitam verilə bilər?"

---

## 🛡️ Disclaimer

This tool is for **educational and informational purposes only**.
It does **not replace professional legal advice**.

---

## 📜 License

MIT License

