import streamlit as st
from groq import Groq
import os
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set page config
st.set_page_config(page_title="Eye Care AI Assistant", page_icon="👁️", layout="centered")

# Custom CSS for styling
st.markdown(
    """
<style>
    .stChatFloatingInputContainer {
        padding-bottom: 20px;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.title("👁️ Eye Care AI Assistant")
st.markdown(
    "Your personal AI assistant for healthy eye care routines, remedies, and habits."
)

# Initialize Groq client
api_key = os.getenv("GROQ_API_KEY")

# Check if API key is present and valid
if not api_key or api_key == "your_groq_api_key_here":
    st.error("Please add your Groq API Key to the `.env` file to use the chatbot.")
    st.stop()

# Initialize client
client = Groq(api_key=api_key)

# System Prompt
SYSTEM_PROMPT = """You are an AI Eye Care Assistant. 
Your goal is to suggest healthy eye care routines, natural remedies, screen-time management, and exercises (like the 20-20-20 rule) to keep eyes safe and healthy.

STRICT RESTRICTIONS:
1. You MUST NOT prescribe any medicine or medical treatments.
2. You MUST NOT diagnose any eye diseases or medical conditions.
3. If a user asks for medical diagnosis, prescriptions, or treatments for an eye condition, you must politely inform them that you are an AI, not a doctor, and advise them to consult a qualified eye care professional or ophthalmologist.
4. Keep your responses concise, friendly, and easy to read.
"""

CHATS_DIR = "chats"
os.makedirs(CHATS_DIR, exist_ok=True)

def save_chat(chat_id, messages, title):
    filepath = os.path.join(CHATS_DIR, f"{chat_id}.json")
    with open(filepath, "w") as f:
        json.dump({"id": chat_id, "title": title, "messages": messages, "timestamp": datetime.now().isoformat()}, f)

def load_chat(chat_id):
    filepath = os.path.join(CHATS_DIR, f"{chat_id}.json")
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    return None

def list_chats():
    chats = []
    for filename in os.listdir(CHATS_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(CHATS_DIR, filename)
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                    chats.append({
                        "id": data.get("id"),
                        "title": data.get("title", "Untitled Chat"),
                        "timestamp": data.get("timestamp", "")
                    })
            except Exception:
                continue
    return sorted(chats, key=lambda x: x["timestamp"], reverse=True)

def start_new_chat():
    st.session_state.current_chat_id = str(uuid.uuid4())
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "assistant",
            "content": "Hello! I'm your Eye Care AI Assistant. How can I help you keep your eyes healthy today?",
        },
    ]

# Initialize state
if "current_chat_id" not in st.session_state:
    start_new_chat()

# Sidebar for Chat History
with st.sidebar:
    st.header("Chat History")
    if st.button("➕ New Chat", use_container_width=True):
        start_new_chat()
        st.rerun()
        
    st.divider()
    
    saved_chats = list_chats()
    for chat in saved_chats:
        # Create a button for each chat
        if st.button(chat["title"], key=chat["id"], use_container_width=True):
            loaded_data = load_chat(chat["id"])
            if loaded_data:
                st.session_state.current_chat_id = loaded_data["id"]
                st.session_state.messages = loaded_data["messages"]
                st.rerun()

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("Ask about eye care routines..."):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        try:
            # Call Groq API
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",  # Using a standard fast model from Groq
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
                temperature=0.7,
                max_tokens=1024,
                stream=True,
            )

            # Stream the response
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    full_response += chunk.choices[0].delta.content
                    message_placeholder.markdown(full_response + "▌")

            message_placeholder.markdown(full_response)

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            full_response = "I'm sorry, I encountered an error while trying to process your request."

    # Add assistant response to chat history
    if (
        full_response
        != "I'm sorry, I encountered an error while trying to process your request."
    ):
        st.session_state.messages.append(
            {"role": "assistant", "content": full_response}
        )
        
        # Save chat logic
        # Use the first user message as title
        title = "Untitled Chat"
        user_messages = [m["content"] for m in st.session_state.messages if m["role"] == "user"]
        if user_messages:
            title = user_messages[0][:30] + ("..." if len(user_messages[0]) > 30 else "")
            
        save_chat(st.session_state.current_chat_id, st.session_state.messages, title)
