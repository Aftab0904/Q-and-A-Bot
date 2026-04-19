from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import os
import io
from dotenv import load_dotenv
from openai import OpenAI
import numpy as np
from pypdf import PdfReader
import chromadb
from evaluator import evaluate_response
from sentence_transformers import SentenceTransformer

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

# -------- LLM CLIENT --------
groq_client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

# -------- EMBEDDING MODEL (LOCAL) --------
print("Loading local embedding model (BAAI/bge-small-en-v1.5)...")
embed_model = SentenceTransformer('BAAI/bge-small-en-v1.5')

# -------- CHROMADB --------
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(
    name="document_qa_collection",
    metadata={"hnsw:space": "cosine"}
)

# -------- MODEL --------
class AskRequest(BaseModel):
    document_id: str
    question: str


# -------- CHUNK --------
def chunk_text(text, size=800, overlap=100):
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i+size])
        i += size - overlap
    return chunks


# -------- LOCAL EMBEDDING --------
def embed(texts):
    try:
        # Use local sentence-transformers
        if isinstance(texts, str):
            texts = [texts]
        
        embeddings = embed_model.encode(texts)
        return embeddings.tolist()
    except Exception as e:
        print(f"CRITICAL: Embedding failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=503, detail=f"Local embedding failed: {str(e)}")


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
    
    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    metadatas = [{"doc_id": doc_id, "chunk_index": i} for i in range(len(chunks))]
    
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas
    )

    return {
        "document_id": doc_id,
        "filename": file.filename,
        "total_chunks": len(chunks)
    }


# -------- ASK --------
@app.post("/ask")
def ask(req: AskRequest):
    if not req.question:
        raise HTTPException(status_code=400, detail="Question is empty")

    # 1. Embed user question
    q_embed = embed([req.question])[0]
    
    # 2. Retrieve top chunks from ChromaDB
    results = collection.query(
        query_embeddings=[q_embed],
        n_results=3,
        where={"doc_id": req.document_id}
    )
    
    if not results["documents"]:
        raise HTTPException(status_code=404, detail="Document not found or no context retrieved")
        
    context = "\n\n".join(results["documents"][0])
    sources = results["ids"][0]

    # 3. Generate Answer
    prompt = f"""
    Answer the following question using ONLY the provided context. 
    If the answer is not in the context, state that explicitly.
    
    [CONTEXT]
    {context}
    
    [QUESTION]
    {req.question}
    """

    try:
        res = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )
        answer = res.choices[0].message.content
        
        # 4. EVALUATE (Judge LLM)
        evaluation = evaluate_response(req.question, context, answer)
        
        return {
            "answer": answer,
            "sources": sources,
            "evaluation": evaluation
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI Engine failed: {str(e)}")


# -------- HEALTH --------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"message": "API running 🚀"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
