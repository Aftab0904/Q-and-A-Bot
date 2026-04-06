from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import os
from dotenv import load_dotenv
from openai import OpenAI
import numpy as np
import google.generativeai as genai

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

# -------- STORE --------
DOCUMENTS = {}

# -------- MODEL --------
class AskRequest(BaseModel):
    document_id: str
    question: str


# -------- CHUNK --------
def chunk_text(text, size=300, overlap=50):
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i+size])
        i += size - overlap
    return chunks


# -------- GEMINI EMBEDDING --------
def embed(texts):
    try:
        embeddings = []

        for text in texts:
            res = genai.embed_content(
                model="gemini-embedding-004",
                content=text
            )
            embeddings.append(res["embedding"])

        return embeddings

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Embedding failed: {str(e)}")


# -------- UPLOAD --------
@app.post("/upload")
async def upload(file: UploadFile):

    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=415, detail="Only .txt files allowed")

    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="File is empty")

    text = content.decode("utf-8")

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