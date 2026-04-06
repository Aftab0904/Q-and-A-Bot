from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uuid
import os
from dotenv import load_dotenv

from rag import chunk_text, embed_chunks, store_document, retrieve
from models import AskRequest

load_dotenv()

app = FastAPI()

# CORS fix
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
GROQ_KEY = os.getenv("GROQ_API_KEY")


# ---------- STRICT PROMPT ----------
SYSTEM_PROMPT = """
You are a document QA assistant.

You MUST answer ONLY from the provided context.

RULES:
- If answer is NOT in context → say:
  "The answer is not present in the document."
- Do NOT use outside knowledge
- Be concise
"""


# ---------- UPLOAD ----------
@app.post("/upload")
async def upload(file: UploadFile):

    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=415, detail="Only .txt allowed")

    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    text = content.decode("utf-8")

    chunks = chunk_text(text)
    embeddings = embed_chunks(chunks)

    doc_id = str(uuid.uuid4())
    store_document(doc_id, chunks, embeddings)

    return {
        "document_id": doc_id,
        "filename": file.filename,
        "total_chunks": len(chunks)
    }


# ---------- LLM FUNCTIONS ----------
def ask_openai(prompt):
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_KEY)

    res = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    )

    return res.choices[0].message.content


def ask_groq(prompt):
    from openai import OpenAI

    client = OpenAI(
        api_key=GROQ_KEY,
        base_url="https://api.groq.com/openai/v1"
    )

    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    )

    return res.choices[0].message.content


def ask_llama_local(prompt):
    return "Free model. Context was provided."


# ---------- ASK ----------
@app.post("/ask")
def ask(req: AskRequest):

    if not req.question:
        raise HTTPException(status_code=400, detail="Empty question")

    result = retrieve(req.document_id, req.question)

    if not result:
        raise HTTPException(status_code=404, detail="Document not found")

    context, indices = result

    final_prompt = f"""
Context:
{context}

Question:
{req.question}
"""

    if req.model == "openai":
        answer = ask_openai(final_prompt)

    elif req.model == "groq":
        answer = ask_groq(final_prompt)

    else:
        answer = ask_llama_local(final_prompt)

    return {
        "answer": answer,
        "sources": indices
    }


# ---------- HEALTH ----------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "llm": "dynamic",
        "embedding": "MiniLM"
    }