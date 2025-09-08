import streamlit as st
import requests

# FastAPI backend URL
FASTAPI_URL = "http://127.0.0.1:8000"  # Update this if running elsewhere

# App Title.
st.set_page_config(page_title="Gemini Chatbot", page_icon="🤖", layout="centered")
st.title("🤖 Gemini API Chatbot")

# Input field for user prompt
user_prompt = st.text_area(
    "Enter your prompt:",
    placeholder="Type your query here...",
    height=120
)

# Button to send the prompt
if st.button("Ask Gemini"):
    if user_prompt.strip():
        try:
            response = requests.post(
                    #We are using gemini from ai studio
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
            st.error(f"❌ An error occurred: {e}")
    else:
        st.warning("⚠️ Please enter a prompt before submitting.")

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
