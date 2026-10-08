import streamlit as st
import os
import pypdf
from google import genai
import time
from google.genai import types

# 1. Authenticate
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except (KeyError, FileNotFoundError):
    API_KEY = os.environ.get("GEMINI_API_KEY")

@st.cache_resource
def get_client():
    return genai.Client(api_key=API_KEY)

client = get_client()

st.title("📚 AI Textbook Tutor (Gemini)")

# 2. Initialize Session State & Chat Object
if "chat" not in st.session_state:
    st.session_state.messages = []
    st.session_state.textbook_text = None
    
    st.session_state.chat = client.chats.create(
        model="gemini-3.8-flash",
        config=types.GenerateContentConfig(
            system_instruction=(
                "You are an AI educator. Answer student questions using ONLY the provided textbook text. "
                "If math is required, use your code execution tool to calculate the exact answer. "
                "Structure every response with: 1) A clear conceptual explanation, "
                "2) The step-by-step mathematical solution, and 3) Two follow-up questions."
            ),
            tools=[{"code_execution": {}}]
        )
    )

# 3. Sidebar: File Upload and Text Extraction
uploaded_file = st.sidebar.file_uploader("Upload Textbook (PDF)", type=["pdf"])
if uploaded_file and not st.session_state.textbook_text:
    with st.spinner("Extracting textbook text..."):
        # Read the PDF text locally instead of uploading the raw file to Google
        pdf_reader = pypdf.PdfReader(uploaded_file)
        extracted_text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                extracted_text += page_text + "\n"
        
        st.session_state.textbook_text = extracted_text
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
            
            # If this is the first prompt, combine the textbook text with the user's question
            if st.session_state.textbook_text and "file_sent" not in st.session_state:
                full_prompt = f"TEXTBOOK REFERENCE MATERIAL:\n{st.session_state.textbook_text}\n\nSTUDENT QUESTION:\n{prompt}"
                st.session_state.file_sent = True
            else:
                full_prompt = prompt
            
            # Send message to Gemini Chat Session
            # Create an empty placeholder to update our status messages
            status_container = st.empty()
            max_retries = 5
            
            for attempt in range(max_retries):
                try:
                    # Attempt to send the message
                    response = st.session_state.chat.send_message(full_prompt)
                    
                    # If successful, clear the warning, print the text, and save to memory
                    status_container.empty()
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                    break  # Exit the retry loop
                    
                except Exception as e:
                    if "503" in str(e) or "UNAVAILABLE" in str(e):
                        if attempt < max_retries - 1:
                            # Update the UI and wait 10 seconds before looping again
                            status_container.warning(f"⏳ Servers are busy. Auto-retrying in 10 seconds... (Attempt {attempt + 1} of {max_retries})")
                            time.sleep(10)
                        else:
                            status_container.error("Google's servers are still at maximum capacity. Please try again later.")
                    else:
                        status_container.error(f"An API error occurred: {e}")
                        break  # Stop retrying if it is a different kind of error
