# Import
import os
import json
import time
import streamlit as st
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory

load_dotenv()
ENV_GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

st.set_page_config(
    page_title="GroqChat — AI Assistant",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Constants 
DEFAULT_SYSTEM_PROMPT = "You are a helpful AI assistant. Be clear, correct and concise."
TONE_PRESETS = {
    "Default":  DEFAULT_SYSTEM_PROMPT,
    "Friendly": "You are a warm, enthusiastic, and supportive AI assistant. Use a conversational, upbeat tone and encourage the user.",
    "Strict":   "You are a precise, formal, and no-nonsense AI assistant. Be direct, avoid filler words, and only provide factual information.",
    "Teacher":  "You are a patient, educational AI assistant. Explain concepts clearly with examples, check for understanding, and guide the user step-by-step."
}

# Session state 
if "tone_preset"         not in st.session_state: st.session_state.tone_preset         = "Default"
if "system_prompt_value" not in st.session_state: st.session_state.system_prompt_value = DEFAULT_SYSTEM_PROMPT
if "prompt_counter"      not in st.session_state: st.session_state.prompt_counter      = 0
if "history_store"       not in st.session_state: st.session_state.history_store       = {}

# Sidebar 
with st.sidebar:
    st.header("⚙️ Controls")

    api_key_input = st.text_input("Groq API Key", type="password", placeholder="gsk_…")
    GROQ_API_KEY  = api_key_input.strip() if api_key_input else ENV_GROQ_API_KEY

    model_name = st.selectbox(
        "Model",
        options=[
            "llama-3.3-70b-versatile",
            "qwen/qwen3-32b",
            "openai/gpt-4o-mini",
            "mixtral-8x7b-32768",
            "gemma2-9b-it"
        ],
        index=0
    )

    temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.4, step=0.1)
    max_tokens  = st.slider("Max Tokens",  min_value=64,  max_value=1024, value=256, step=64)

    st.divider()

    def on_tone_change():
        selected = st.session_state["tone_selectbox"]
        st.session_state.tone_preset         = selected
        st.session_state.system_prompt_value = TONE_PRESETS[selected]
        st.session_state.prompt_counter     += 1

    st.selectbox(
        "Tone Preset",
        options=list(TONE_PRESETS.keys()),
        index=list(TONE_PRESETS.keys()).index(st.session_state.tone_preset),
        key="tone_selectbox",
        on_change=on_tone_change
    )

    system_prompt = st.text_area(
        "System Prompt",
        value=st.session_state.system_prompt_value,
        height=130,
        key=f"system_prompt_widget_{st.session_state.prompt_counter}"
    )
    st.session_state.system_prompt_value = system_prompt

    if st.button("🔄 Reset Prompt"):
        st.session_state.tone_preset         = "Default"
        st.session_state.system_prompt_value = DEFAULT_SYSTEM_PROMPT
        st.session_state.prompt_counter     += 1
        st.rerun()

    st.divider()

    typing_effect = st.checkbox("Typing Effect", value=True)

    if st.button("🗑️ Clear Chat"):
        st.session_state.history_store = {}
        st.rerun()

# API Key Guard 
if not GROQ_API_KEY:
    st.error("⚠️ Groq API Key is missing. Enter it in the sidebar or add it to your .env file.")
    st.stop()

# Header 
st.title("🤖 Conversational AI Chatbot")
st.caption("Built with LangChain + Streamlit + Groq Cloud API")

# Chat history helpers 
SESSION_ID = "default_session"

def get_history(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in st.session_state.history_store:
        st.session_state.history_store[session_id] = InMemoryChatMessageHistory()
    return st.session_state.history_store[session_id]

# LLM chain 
llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model=model_name,
    temperature=temperature,
    max_tokens=max_tokens
)

prompt_template = ChatPromptTemplate.from_messages([
    ("system", "{system_prompt}"),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{user_input}")
])

chain = prompt_template | llm | StrOutputParser()

chat_with_history = RunnableWithMessageHistory(
    chain,
    get_history,
    input_messages_key="user_input",
    history_messages_key="history"
)

# Render history 
for message in get_history(SESSION_ID).messages:
    role = getattr(message, "type", "")
    with st.chat_message("user" if role == "human" else "assistant"):
        st.write(message.content)

# Chat input 
user_input = st.chat_input("Ask me anything…")

if user_input:
    st.chat_message("user").write(user_input)
    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            response_text = chat_with_history.invoke(
                {"user_input": user_input, "system_prompt": st.session_state.system_prompt_value},
                config={"configurable": {"session_id": SESSION_ID}}
            )
        except Exception as e:
            placeholder.error(f"Model error: {e}")
            response_text = ""

        if typing_effect and response_text:
            typed = ""
            for char in response_text:
                typed += char
                placeholder.markdown(typed)
                time.sleep(0.015)
        elif response_text:
            placeholder.write(response_text)

# Download section 
st.divider()
st.subheader("⬇️ Download Chat History")

export_data      = []
export_txt_lines = []

for m in get_history(SESSION_ID).messages:
    role  = getattr(m, "type", "")
    label = "user" if role == "human" else "assistant"
    export_data.append({"role": label, "content": m.content})
    export_txt_lines.append(f"{label.upper()}: {m.content}")

st.download_button(
    label="📥 Download as JSON",
    data=json.dumps(export_data, ensure_ascii=False, indent=2),
    file_name="chat_history.json",
    mime="application/json",
    use_container_width=True
)
st.download_button(
    label="📄 Export as TXT",
    data="\n\n".join(export_txt_lines),
    file_name="chat_history.txt",
    mime="text/plain",
    use_container_width=True
)
