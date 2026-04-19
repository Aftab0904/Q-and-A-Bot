import os
import uuid
import numpy as np
import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

# -------- CONFIG --------
# Local Embedding Model (No API needed)
print("Loading local embedding model (BAAI/bge-small-en-v1.5)...")
embed_model = SentenceTransformer('BAAI/bge-small-en-v1.5')

# Persistent ChromaDB
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

# -------- LOCAL EMBEDDING --------
def embed(texts):
    if isinstance(texts, str):
        texts = [texts]
    embeddings = embed_model.encode(texts)
    return embeddings.tolist()

# -------- STORE --------
def store_document(doc_id, filename, chunks):
    embeddings = embed(chunks)
    
    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
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
