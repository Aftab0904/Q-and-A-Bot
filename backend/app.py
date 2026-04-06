import streamlit as st
import numpy as np
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import os

load_dotenv()

# -------- CONFIG --------
st.set_page_config(page_title="Document Q&A", layout="centered")

st.title("Document Q&A Assistant")

# -------- MODEL SELECTION --------
model_choice = st.selectbox(
    "Choose Model",
    ["OpenAI", "Groq"]
)

# -------- LOAD EMBEDDING MODEL --------
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

# -------- SESSION STATE --------
if "doc" not in st.session_state:
    st.session_state.doc = None
    st.session_state.embeddings = None
    st.session_state.chunks = None


# -------- CHUNK FUNCTION --------
def chunk_text(text, size=300, overlap=50):
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i+size])
        i += size - overlap
    return chunks


# -------- UPLOAD --------
uploaded_file = st.file_uploader("Upload .txt file", type=["txt"])

if uploaded_file:
    text = uploaded_file.read().decode("utf-8")

    chunks = chunk_text(text)
    embeddings = embed_model.encode(chunks)

    st.session_state.chunks = chunks
    st.session_state.embeddings = embeddings

    st.success(f"Uploaded! Total chunks: {len(chunks)}")


# -------- QUESTION --------
question = st.text_input("Ask a question")

# -------- RETRIEVAL --------
def retrieve(question, top_k=3):
    query_embedding = embed_model.encode([question])[0]
    sims = np.dot(st.session_state.embeddings, query_embedding)

    top_idx = np.argsort(sims)[-top_k:][::-1]
    context = [st.session_state.chunks[i] for i in top_idx]

    return context, top_idx


# -------- LLM CALLS --------
def ask_openai(prompt):
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    res = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Answer ONLY from context."},
            {"role": "user", "content": prompt}
        ]
    )
    return res.choices[0].message.content


def ask_groq(prompt):
    from openai import OpenAI

    client = OpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1"
    )

    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Answer ONLY from context."},
            {"role": "user", "content": prompt}
        ]
    )
    return res.choices[0].message.content


def ask_free(prompt):
    return "Free model (no LLM): " + prompt[:100]


# -------- ANSWER --------
if st.button("Ask"):

    if st.session_state.chunks is None:
        st.error("Upload document first")
    elif not question:
        st.error("Enter a question")
    else:
        context, sources = retrieve(question)

        final_prompt = f"""
        Context:
        {context}

        Question:
        {question}

        If answer not in context, say:
        "Answer not found in document"
        """

        if model_choice == "OpenAI":
            answer = ask_openai(final_prompt)
        elif model_choice == "Groq":
            answer = ask_groq(final_prompt)
        else:
            answer = ask_free(final_prompt)

        st.subheader("Answer")
        st.write(answer)

        st.subheader("Sources")
        st.write(sources)