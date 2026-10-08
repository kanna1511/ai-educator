import streamlit as st
import tempfile
import os
from google import genai
from google.genai import types

# 1. Authenticate using Streamlit Secrets (or local environment variables)
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except (KeyError, FileNotFoundError):
    API_KEY = os.environ.get("GEMINI_API_KEY")

client = genai.Client(api_key=API_KEY)

st.title("📚 AI Textbook Tutor (Gemini)")

# 2. Initialize Session State & Chat Object
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.gemini_file = None
    
    # Create the stateful chat session with the Code Interpreter enabled
    st.session_state.chat = client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=(
                "You are an AI educator. Answer student questions using ONLY the provided textbook files. "
                "If math is required, use your code execution tool to calculate the exact answer. "
                "Structure every response with: 1) A clear conceptual explanation, "
                "2) The step-by-step mathematical solution, and 3) Two follow-up questions."
            ),
            tools=[{"code_execution": {}}]
        )
    )

# 3. Sidebar: File Upload directly to Gemini
uploaded_file = st.sidebar.file_uploader("Upload Textbook (PDF)", type=["pdf"])
if uploaded_file and not st.session_state.gemini_file:
    with st.spinner("Uploading and analyzing textbook..."):
        # Save Streamlit's in-memory file to a temp file for Gemini to read
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name
        
        # Upload the whole file directly to Gemini's memory
        st.session_state.gemini_file = client.files.upload(file=tmp_path)
        st.sidebar.success("Textbook learned! Ask me anything.")

# 4. Render Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 5. Handle User Input
if prompt := st.chat_input("Ask a question or provide a problem..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking and calculating..."):
            
            # If this is the first prompt after uploading the file, send the file alongside the text
            prompt_contents = [prompt]
            if st.session_state.gemini_file and "file_sent" not in st.session_state:
                prompt_contents.insert(0, st.session_state.gemini_file)
                st.session_state.file_sent = True
            
            # Send message to Gemini Chat Session
            response = st.session_state.chat.send_message(prompt_contents)
            
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
