import streamlit as st
import requests

# FastAPI backend URL
FASTAPI_URL = "http://backend:8000"  # Update if running elsewhere

st.set_page_config(page_title="Gemini API powered Chatbot Basic Level", page_icon="🤖", layout="centered")
st.title("🤖 Gemini AI Assistant")

# Tabs for Chatbot and DevOps tools
tab1, tab2 = st.tabs(["💬 Chatbot", "🛠️ DevOps Helpers"])

# --- TAB 1: Chatbot ---
with tab1:
    st.subheader("Chat with Gemini")

    user_prompt = st.text_area("Enter your prompt:", placeholder="Type your query here...", height=120)

    if st.button("Ask Gemini", key="chat"):
        if user_prompt.strip():
            try:
                response = requests.post(
                    f"{FASTAPI_URL}/ask-gemini",
                    json={"prompt": user_prompt}
                )
                response.raise_for_status()
                gemini_response = response.json().get("response", "")
                if gemini_response:
                    st.success("Response from Gemini:")
                    st.write(gemini_response)
                else:
                    st.warning("No response received from Gemini.")
            except requests.exceptions.RequestException as e:
                st.error(f"❌ Error: {e}")
        else:
            st.warning("⚠️ Please enter a prompt before submitting.")

# --- TAB 2: DevOps Helpers ---
with tab2:
    st.subheader("DevOps Assistance")

    helper = st.selectbox(
        "Choose a tool:",
        ["Analyze Logs", "Optimize Dockerfile", "Fix CI/CD"]
    )

    content = st.text_area(
        f"Paste your {helper} content here:",
        placeholder="Paste logs, Dockerfile, or CI/CD YAML...",
        height=200
    )

    if st.button("Run Helper", key="devops"):
        if content.strip():
            try:
                endpoint_map = {
                    "Analyze Logs": "analyze-logs",
                    "Optimize Dockerfile": "optimize-docker",
                    "Fix CI/CD": "fix-ci"
                }
                endpoint = endpoint_map[helper]

                response = requests.post(
                    f"{FASTAPI_URL}/{endpoint}",
                    json={"content": content}
                )
                response.raise_for_status()
                suggestions = response.json().get("suggestions", "")
                if suggestions:
                    st.success(f"Suggestions from Gemini ({helper}):")
                    st.write(suggestions)
                else:
                    st.warning("No suggestions returned.")
            except requests.exceptions.RequestException as e:
                st.error(f"❌ Error: {e}")
        else:
            st.warning("⚠️ Please paste some content first.")

# --- Footer ---
st.markdown(
    """
    <div style="
        position: fixed; 
        bottom: 15px; 
        left: 50%; 
        transform: translateX(-50%);
        color: grey; 
        font-size: 15px;
        text-align: center;
    ">
        Made with ❤️ by <b>Harsh</b>
    </div>
    """,
    unsafe_allow_html=True
)
