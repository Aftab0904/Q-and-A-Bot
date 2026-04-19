import os
import uuid
import numpy as np
import google.generativeai as genai
import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv

load_dotenv()

# -------- CONFIG --------
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Persistent ChromaDB (saves to a local folder named 'chroma_db')
client = chromadb.PersistentClient(path="./chroma_db")

# Create or get a collection for documents
collection = client.get_or_create_collection(
    name="document_qa_collection",
    metadata={"hnsw:space": "cosine"}
)

# -------- CHUNK --------
def chunk_text(text, size=500, overlap=50):
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i+size])
        i += size - overlap
    return chunks

# -------- GEMINI EMBEDDING --------
def embed(texts):
    res = genai.embed_content(
        model="models/gemini-embedding-2-preview",
        content=texts
    )
    return res["embedding"]

# -------- STORE --------
def store_document(doc_id, filename, chunks):
    embeddings = embed(chunks)
    
    # Generate unique IDs for each chunk
    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    
    # Add metadata to each chunk
    metadatas = [{"filename": filename, "doc_id": doc_id, "chunk_index": i} for i in range(len(chunks))]
    
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas
    )

# -------- RETRIEVE --------
def retrieve(doc_id, question, top_k=3):
    q_embed = embed([question])[0]
    
    results = collection.query(
        query_embeddings=[q_embed],
        n_results=top_k,
        where={"doc_id": doc_id}
    )
    
    if not results["documents"]:
        return None, []
        
    return results["documents"][0], results["metadatas"][0]
