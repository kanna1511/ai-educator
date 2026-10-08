import streamlit as st
from openai import OpenAI

# Initialize client
client = OpenAI()

st.title("📚 AI Textbook Tutor")

if "previous_response_id" not in st.session_state:
    st.session_state.previous_response_id = None
    st.session_state.messages = []
    st.session_state.vector_store_id = None

# Sidebar: File Upload & Vector Store Logic
uploaded_file = st.sidebar.file_uploader("Upload Textbook (PDF)", type=["pdf"])
if uploaded_file and not st.session_state.vector_store_id:
    with st.spinner("Processing textbook..."):
        openai_file = client.files.create(file=uploaded_file, purpose="assistants")
        
        vector_store = client.vector_stores.create(name="Textbook Store")
        client.vector_stores.files.create(
            vector_store_id=vector_store.id, 
            file_id=openai_file.id
        )
        st.session_state.vector_store_id = vector_store.id
        st.sidebar.success("Textbook learned! Ask me anything.")

# Render Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle User Input & Responses API Call
if prompt := st.chat_input("Ask a question or provide a problem..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching text and calculating..."):
            kwargs = {
                "model": "gpt-4o",
                "input": prompt,
                "instructions": (
                    "You are an AI educator. Answer student questions using ONLY the provided textbook files. "
                    "If math is required, use the Code Interpreter tool to calculate the exact answer. "
                    "Structure every response with: 1) A clear conceptual explanation, "
                    "2) The step-by-step mathematical solution, and 3) Two follow-up questions."
                ),
                "tools": [{"type": "code_interpreter", "container": {"type": "auto"}}]
            }

            if st.session_state.vector_store_id:
                kwargs["tools"].append({
                    "type": "file_search", 
                    "file_search": {"vector_store_ids": [st.session_state.vector_store_id]}
                })

            if st.session_state.previous_response_id:
                kwargs["previous_response_id"] = st.session_state.previous_response_id
            
            response = client.responses.create(**kwargs)
            output_text = response.output[0].content[0].text
            st.markdown(output_text)
            
            st.session_state.previous_response_id = response.id
            st.session_state.messages.append({"role": "assistant", "content": output_text})
