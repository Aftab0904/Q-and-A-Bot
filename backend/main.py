from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import os
import io
from dotenv import load_dotenv
from openai import OpenAI
import numpy as np
import google.generativeai as genai
from pypdf import PdfReader

load_dotenv()

# -------- APP --------
app = FastAPI()

# -------- CORS --------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------- API KEYS --------
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

groq_client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

# -------- STORE (In-Memory) --------
DOCUMENTS = {}

# -------- MODEL --------
class AskRequest(BaseModel):
    document_id: str
    question: str


# -------- CHUNK --------
def chunk_text(text, size=500, overlap=50):
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i+size])
        i += size - overlap
    return chunks


# -------- GEMINI EMBEDDING (Batch) --------
def embed(texts):
    try:
        res = genai.embed_content(
            model="models/gemini-embedding-2-preview",
            content=texts
        )
        return res["embedding"]
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Embedding failed: {str(e)}")


# -------- UPLOAD --------
@app.post("/upload")
async def upload(file: UploadFile):

    if file.filename.endswith(".txt"):
        content = await file.read()
        text = content.decode("utf-8")
    elif file.filename.endswith(".pdf"):
        content = await file.read()
        pdf_reader = PdfReader(io.BytesIO(content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
    else:
        raise HTTPException(status_code=415, detail="Only .txt and .pdf files allowed")

    if not text.strip():
        raise HTTPException(status_code=400, detail="File is empty or no text found")

    chunks = chunk_text(text)
    embeddings = embed(chunks)

    doc_id = str(uuid.uuid4())

    DOCUMENTS[doc_id] = {
        "chunks": chunks,
        "embeddings": embeddings
    }

    return {
        "document_id": doc_id,
        "filename": file.filename,
        "total_chunks": len(chunks)
    }


# -------- RETRIEVE --------
def retrieve(doc_id, question):
    data = DOCUMENTS.get(doc_id)

    if not data:
        return None

    q_embed = embed([question])[0]

    sims = np.dot(data["embeddings"], q_embed)
    idx = np.argsort(sims)[-3:][::-1]

    return [data["chunks"][i] for i in idx], idx.tolist()


# -------- ASK --------
@app.post("/ask")
def ask(req: AskRequest):

    if not req.question:
        raise HTTPException(status_code=400, detail="Question is empty")

    result = retrieve(req.document_id, req.question)

    if not result:
        raise HTTPException(status_code=404, detail="Document not found")

    context, sources = result

    prompt = f"""
Answer ONLY using this context:
{context}

If answer is not present, say:
"Answer not found in document"

Question:
{req.question}
"""

    try:
        res = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"LLM failed: {str(e)}")

    return {
        "answer": res.choices[0].message.content,
        "sources": sources
    }


# -------- HEALTH --------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"message": "API running 🚀"}