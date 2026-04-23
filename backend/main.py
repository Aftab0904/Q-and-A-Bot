from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import os
import io
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pypdf import PdfReader
from evaluator import evaluate_response
import rag_service
from models import AskRequest

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

# -------- LLM CLIENT (LangChain) --------
# We use ChatOpenAI which is compatible with Groq if we set base_url
llm = ChatOpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
    model="llama-3.3-70b-versatile"
)

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

    # Use LangChain-powered RAG service
    chunks = rag_service.chunk_text(text)
    doc_id = str(uuid.uuid4())
    rag_service.store_document(doc_id, file.filename, chunks)

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

    # 1. Retrieve top chunks using LangChain logic in rag_service
    docs, metadatas = rag_service.retrieve(req.document_id, req.question)
    
    if not docs:
        raise HTTPException(status_code=404, detail="Document not found or no context retrieved")
        
    context = "\n\n".join(docs)
    sources = [m.get("chunk_index") for m in metadatas]

    # 2. Generate Answer using LangChain ChatOpenAI
    prompt = f"""
    Answer the following question using ONLY the provided context. 
    If the answer is not in the context, state that explicitly.
    
    [CONTEXT]
    {context}
    
    [QUESTION]
    {req.question}
    """

    try:
        # Using LangChain invoke method
        res = llm.invoke(prompt)
        answer = res.content
        
        # 3. EVALUATE (Judge LLM)
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
    return {"message": "API running with LangChain"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
