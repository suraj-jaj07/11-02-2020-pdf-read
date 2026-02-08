import streamlit as st
import os
from pypdf import PdfReader
from google import genai

# -----------------------------
# Config
# -----------------------------
GOOGLE_API_KEY = os.getenv("API_KEY")
MODEL_ID = "gemini-2.5-flash"
client = genai.Client(api_key=GOOGLE_API_KEY)

st.set_page_config(page_title="Chat with PDF (Gemini)", layout="wide")
st.title("📄💬 Chat with your PDF (Gemini)")

# -----------------------------
# Session State
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "pdf_chunks" not in st.session_state:
    st.session_state.pdf_chunks = []

# -----------------------------
# PDF Processing
# -----------------------------
def load_pdf_chunks(pdf_file, chunk_size=1200, overlap=200):
    reader = PdfReader(pdf_file)
    chunks = []

    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        if not text:
            continue

        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]
            chunks.append({
                "page": page_num,
                "text": chunk_text
            })
            start = end - overlap

    return chunks

def build_context(chunks, max_chunks=5):
    context = ""
    for c in chunks[:max_chunks]:
        context += f"\n[Page {c['page']}]\n{c['text']}\n"
    return context

# -----------------------------
# Gemini Streaming
# -----------------------------
def stream_answer(question, context):
    prompt = f"""
You are answering questions from a PDF.

Rules:
- Use ONLY the provided context
- Cite page numbers like (Page X)
- If unsure, say you don't know

Context:
{context}

Question:
{question}
"""

    stream = client.models.generate_content_stream(
        model=MODEL_ID,
        contents=prompt
    )

    full_response = ""
    for chunk in stream:
        if chunk.text:
            full_response += chunk.text
            yield chunk.text

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.header("📂 Upload PDF")
    pdf_file = st.file_uploader("Upload PDF", type=["pdf"])

    if pdf_file and not st.session_state.pdf_chunks:
        with st.spinner("Processing PDF..."):
            st.session_state.pdf_chunks = load_pdf_chunks(pdf_file)
        st.success(f"Loaded {len(st.session_state.pdf_chunks)} chunks")

# -----------------------------
# Chat UI
# -----------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if question := st.chat_input("Ask something about the PDF"):
    # User message
    st.session_state.messages.append({
        "role": "user",
        "content": question
    })

    with st.chat_message("user"):
        st.markdown(question)

    # Build context (simple relevance heuristic: first N chunks)
    context = build_context(st.session_state.pdf_chunks)

    # Assistant response (streaming)
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        streamed_text = ""

        for token in stream_answer(question, context):
            streamed_text += token
            response_placeholder.markdown(streamed_text)

    st.session_state.messages.append({
        "role": "assistant",
        "content": streamed_text
    })
