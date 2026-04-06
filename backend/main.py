from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# In-memory store
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


# -------- EMBEDDING --------
def embed(texts):
    res = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )
    return [r.embedding for r in res.data]


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
    import numpy as np

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
        res = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
    except:
        raise HTTPException(status_code=503, detail="LLM failed")

    return {
        "answer": res.choices[0].message.content,
        "sources": sources
    }


# -------- HEALTH --------
@app.get("/health")
def health():
    return {"status": "ok"}