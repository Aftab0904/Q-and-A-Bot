# TalentScout – Document Q&A Assistant

An AI-powered Document Question Answering system built using Retrieval-Augmented Generation (RAG).

This application allows users to upload a `.txt` document, ask questions about it, and receive answers strictly based on the document content — ensuring no hallucinations from the LLM.

---

##  Project Status

<p align="center">
  <img src="https://img.shields.io/badge/Status-Completed-brightgreen?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Type-Assignment%20Project-blue?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Focus-RAG%20Systems-orange?style=for-the-badge" />
</p>

---

## Problem Statement

Traditional document analysis is time-consuming and inefficient, especially when dealing with large unstructured text.

This system solves the problem by:
- Allowing users to upload documents
- Automatically processing and indexing the content
- Answering questions using only the document context

---

## Tech Stack

- **Backend:** FastAPI  
- **Frontend:** HTML, CSS, JavaScript (Single Page UI)  
- **LLM:** OpenAI GPT / Groq (LLaMA)  
- **Embeddings:** OpenAI `text-embedding-3-small`  
- **Deployment:** Render (Backend), Vercel (Frontend)  

---

## Features

| Feature | Description |
|--------|------------|
|  File Upload | Upload `.txt` documents |
| Chunking | Splits document into smaller chunks |
| Semantic Search | Uses embeddings for similarity search |
|  AI Q&A | Answers questions using document context only |
|  No Hallucination | Strict prompt ensures grounded answers |
|  Source Tracking | Shows chunk indices used for answers |
|  Fast UI | Single-page HTML interface |
|  Model Flexibility | Supports OpenAI / Groq LLMs |

---

##  Architecture Overview

```mermaid
flowchart TD

    A[User Uploads Document] --> B[Chunking Engine]
    B --> C["Embedding Model (OpenAI)"]
    C --> D[In-Memory Storage]

    E[User Question] --> F[Query Embedding]
    F --> G[Similarity Search]
    G --> H[Top Chunks Retrieved]

    H --> I["LLM (OpenAI / Groq)"]
    I --> J[Answer Generated]

    J --> K[Frontend Display + Sources]
```

## LLM & Embedding Details

### LLM Used
- **OpenAI (GPT-3.5 Turbo)**
- **Groq (LLaMA 3)**

**Why these models?**
- Fast response time suitable for real-time applications  
- High-quality and reliable answers  
- Easy API integration  
- Groq provides a free and fast inference option  

---

### Embedding Model
- **GoogleGemini**

**Why this embedding model?**
- Lightweight and efficient (important for deployment on free-tier services)  
- Good semantic understanding for document retrieval  
- Avoids heavy local models like sentence-transformers, reducing memory usage  

---

## API Key Setup

To securely use LLM and embedding services, API keys are stored using environment variables.

### Step 1: Create a `.env` file in the backend directory

---

### Step 2: Load environment variables in code

```python
from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

```
