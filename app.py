import streamlit as st
from google import genai
import os

st.set_page_config(page_title="Gemini PDF Chat", layout="centered")
st.title("📄 Chat with your Loan Docs")

# 1. Initialize Client ONLY ONCE and store it in session_state
if "client" not in st.session_state:
    api_key = st.secrets.get("API_KEY") or os.getenv("API_KEY")
    if not api_key:
        st.error("API Key missing!")
        st.stop()
    # Store the client so it doesn't get "closed" or recreated
    st.session_state.client = genai.Client(api_key=api_key)

if "chat_session" not in st.session_state:
    st.session_state.chat_session = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Sidebar: File Upload ---
with st.sidebar:
    st.header("Upload")
    uploaded_file_det = st.file_uploader("Upload a PDF", type="pdf")
    
    if uploaded_file_det and st.button("Process Document"):
        with st.spinner("Uploading to Gemini..."):
            # Use the persistent client
            with open("temp.pdf", "wb") as f:
                f.write(uploaded_file_det.getbuffer())
            
            gemini_file = st.session_state.client.files.upload(file="temp.pdf")
            
            # Start the session using the persistent client
            st.session_state.chat_session = st.session_state.client.chats.create(
                model="gemini-2.5-flash",
                history=[{
                    "role": "user",
                    "parts": [{"file_data": {"file_uri": gemini_file.uri, "mime_type": gemini_file.mime_type}}]
                }]
            )
            # Clear old messages if a new document is uploaded
            st.session_state.messages = []
            st.success("Document processed!")

# --- Chat Interface ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask something about the PDF..."):
    if st.session_state.chat_session is None:
        st.warning("Please process a document first.")
    else:
        # Display user message
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        try:
            # Crucial: Use the session stored in session_state
            response = st.session_state.chat_session.send_message(prompt)
            
            with st.chat_message("assistant"):
                st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"Error: {e}")
