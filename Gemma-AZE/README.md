# Gemma Azerbaijani Language Experiments

This project explores the capabilities of **Google's Gemma foundation models (FMs)** in understanding and generating Azerbaijani language through instruction tuning and prompt engineering. The goal is to assess and enhance Gemma's potential for various valuable applications in Azerbaijani, such as conversational AI, customer support automation, voice assistants, and beyond.

Gemma models are particularly significant due to their **lightweight architecture**, **multi-modal abilities**, and **deployability on consumer-grade hardware**. Unlike larger LLMs that require high-end GPUs or cloud infrastructure, Gemma models can run efficiently on:

* Single GPU servers
* CPUs (as demonstrated in this project)
* Consumer devices like laptops, PCs, and even smartphones (with further optimization)

## Project Focus

* Evaluating different versions of Gemma FMs for Azerbaijani language tasks.
* Designing application scenarios through **instruction tuning** and **prompt engineering**.
* Testing model performance in real-world interaction loops (e.g., simulating a bank call center operator).
* Exploring Gemma’s viability for **edge deployment** on low-resource devices.

The notebook demonstrates a simple interactive dialogue loop in Azerbaijani, using context-aware text generation, while securely handling Hugging Face tokens for model access.

## Why Gemma?

* **Lightweight & Efficient**: Small enough to run on consumer hardware.
* **Multi-modal Potential**: Designed to work beyond text, adaptable for broader AI applications.
* **Open-Source Flexibility**: Easily integrable into custom pipelines for research and product development.
* **Scalable**: Can scale from local CPU inference to multi-modal cloud services depending on application need.