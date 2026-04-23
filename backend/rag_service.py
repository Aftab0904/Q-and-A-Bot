import os
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

# -------- CONFIG --------
# Local Embedding Model using LangChain's HuggingFaceEmbeddings wrapper
print("Loading local embedding model (BAAI/bge-small-en-v1.5) via LangChain...")
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")

# Persistent ChromaDB via LangChain wrapper
persist_directory = "./chroma_db"
vectorstore = Chroma(
    collection_name="document_qa_collection",
    embedding_function=embeddings,
    persist_directory=persist_directory
)

# -------- CHUNK --------
def chunk_text(text, size=500, overlap=50):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        length_function=len,
    )
    return text_splitter.split_text(text)

# -------- STORE --------
def store_document(doc_id, filename, chunks):
    # Add metadata to chunks
    metadatas = [{"filename": filename, "doc_id": doc_id, "chunk_index": i} for i in range(len(chunks))]
    # LangChain's Chroma handles ID generation or we can provide them
    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    
    vectorstore.add_texts(
        texts=chunks,
        metadatas=metadatas,
        ids=ids
    )

# -------- RETRIEVE --------
def retrieve(doc_id, question, top_k=3):
    # LangChain's retriever with filter for doc_id
    results = vectorstore.similarity_search(
        question, 
        k=top_k, 
        filter={"doc_id": doc_id}
    )
    
    if not results:
        return None, []
        
    documents = [doc.page_content for doc in results]
    metadatas = [doc.metadata for doc in results]
    
    return documents, metadatas
