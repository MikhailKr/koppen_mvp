"""AI Assistant chat page."""

import streamlit as st

from frontend.api_client import get_api_client
from frontend.auth import init_session_state
from frontend.components import render_sidebar, require_auth
from frontend.styles import inject_css

st.set_page_config(page_title="AI Assistant - Koppen", page_icon="⚡", layout="wide")
init_session_state()
inject_css()
render_sidebar()
require_auth()

api = get_api_client()

st.title("💬 AI Assistant")
st.caption("Ask questions about your wind farms, forecasts, and generation data")

# Initialize chat history in session state
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

# Display info about capabilities
with st.expander("ℹ️ What can I help you with?", expanded=False):
    st.markdown("""
    I can help you with:

    - **Wind Farm Information**: List your wind farms, get details about turbines and locations
    - **Forecast Analysis**: View recent forecasts and weather predictions
    - **Forecast Accuracy**: Calculate error metrics (MAE, RMSE, MAPE, bias)
    - **Generation Data**: Summarize actual generation statistics

    **Example questions:**
    - "What wind farms do I have?"
    - "Show me details about my North Sea wind farm"
    - "What are the forecast errors for wind farm 1?"
    - "Give me a summary of generation for my wind farm"
    - "How accurate are my forecasts?"
    """)

# Clear chat button
col1, col2 = st.columns([4, 1])
with col2:
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.chat_messages = []
        st.rerun()

st.divider()

# Display chat messages
for message in st.session_state.chat_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask me about your wind farms..."):
    # Add user message to chat history
    st.session_state.chat_messages.append({"role": "user", "content": prompt})

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get AI response
    with st.chat_message("assistant"), st.spinner("Thinking..."):
        # Prepare conversation history for API
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.chat_messages[
                :-1
            ]  # Exclude last message (current prompt)
        ]

        response = api.chat(message=prompt, conversation_history=history)

        if response.get("success", False):
            assistant_message = response.get(
                "response", "I couldn't generate a response."
            )
        else:
            assistant_message = f"❌ {response.get('response', 'An error occurred.')}"

        st.markdown(assistant_message)

    # Add assistant response to chat history
    st.session_state.chat_messages.append(
        {"role": "assistant", "content": assistant_message}
    )

# Show a hint if no messages yet
if not st.session_state.chat_messages:
    st.info(
        "👋 Hi! I'm your AI assistant. Ask me anything about your wind farms, forecasts, or generation data."
    )

    # Quick action buttons
    st.markdown("### Quick Actions")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📋 List my wind farms", use_container_width=True):
            st.session_state.chat_messages.append(
                {"role": "user", "content": "What wind farms do I have?"}
            )
            st.rerun()

    with col2:
        if st.button("📊 Check forecast accuracy", use_container_width=True):
            st.session_state.chat_messages.append(
                {
                    "role": "user",
                    "content": "Show me the forecast accuracy for all my wind farms",
                }
            )
            st.rerun()

    with col3:
        if st.button("⚡ Generation summary", use_container_width=True):
            st.session_state.chat_messages.append(
                {
                    "role": "user",
                    "content": "Give me a summary of generation for my wind farms",
                }
            )
            st.rerun()
