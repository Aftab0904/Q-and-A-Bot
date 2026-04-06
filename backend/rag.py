from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer("all-MiniLM-L6-v2")

DOCUMENT_STORE = {}

# Split text into chunks
def chunk_text(text, size=300, overlap=50):
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i+size])
        i += size - overlap
    return chunks


# Convert chunks to embeddings
def embed_chunks(chunks):
    return model.encode(chunks)


# Store document
def store_document(doc_id, chunks, embeddings):
    DOCUMENT_STORE[doc_id] = {
        "chunks": chunks,
        "embeddings": embeddings
    }


# Retrieve relevant chunks
def retrieve(doc_id, question, top_k=3):
    data = DOCUMENT_STORE.get(doc_id)

    if not data:
        return None

    query_embedding = model.encode([question])[0]

    similarities = np.dot(data["embeddings"], query_embedding)
    top_indices = np.argsort(similarities)[-top_k:][::-1]

    results = [data["chunks"][i] for i in top_indices]

    return results, top_indices.tolist()