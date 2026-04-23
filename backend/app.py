import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# -------- CONFIG --------
st.set_page_config(page_title="Document Q&A (LangChain)", layout="centered")

st.title("Document Q&A Assistant")
st.info("Now powered by LangChain")

API_BASE = "http://localhost:8000"

# -------- SESSION STATE --------
if "doc_id" not in st.session_state:
    st.session_state.doc_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# -------- UPLOAD --------
uploaded_file = st.file_uploader("Upload .pdf or .txt file", type=["pdf", "txt"])

if uploaded_file and st.session_state.doc_id is None:
    with st.spinner("Uploading and indexing with LangChain..."):
        files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
        try:
            res = requests.post(f"{API_BASE}/upload", files=files)
            if res.status_code == 200:
                data = res.json()
                st.session_state.doc_id = data["document_id"]
                st.success(f"Uploaded! Total chunks: {data['total_chunks']}")
            else:
                st.error(f"Upload failed: {res.text}")
        except Exception as e:
            st.error(f"Could not connect to backend: {e}")

# -------- QUESTION --------
question = st.text_input("Ask a question")

# -------- ANSWER --------
if st.button("Ask"):
    if st.session_state.doc_id is None:
        st.error("Please upload a document first")
    elif not question:
        st.error("Enter a question")
    else:
        with st.spinner("Thinking..."):
            try:
                res = requests.post(
                    f"{API_BASE}/ask",
                    json={"document_id": st.session_state.doc_id, "question": question}
                )
                if res.status_code == 200:
                    data = res.json()
                    st.subheader("Answer")
                    st.write(data["answer"])
                    
                    if "evaluation" in data:
                        with st.expander("AI Evaluation"):
                            st.json(data["evaluation"])
                    
                    st.subheader("Source Chunks")
                    st.write(data["sources"])
                else:
                    st.error(f"Error: {res.json().get('detail', 'Unknown error')}")
            except Exception as e:
                st.error(f"Request failed: {e}")

if st.button("Clear Session"):
    st.session_state.doc_id = None
    st.session_state.messages = []
    st.rerun()
