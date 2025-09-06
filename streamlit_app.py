import streamlit as st
import requests

# FastAPI backend URL
FASTAPI_URL = "http://127.0.0.1:8000"  # Update this if your FastAPI server is running elsewhere

# Streamlit app title
st.title("Gemini API Chatbot Basic Level")

# Input field for user prompt
user_prompt = st.text_area(
    "Enter your prompt:",
    placeholder="Type your query here...",
    height=120  # tu isko adjust kar sakta hai
)

# Button to send the prompt to the FastAPI backend
if st.button("Ask Gemini"):
    if user_prompt:
        try:
            # Send the prompt to the FastAPI backend
            response = requests.post(
                f"{FASTAPI_URL}/ask-gemini",
                json={"prompt": user_prompt}
            )
            response.raise_for_status()  # Raise an error for bad responses (4xx, 5xx)

            # Display the response
            st.success("Response from Gemini:")
            st.write(response.json()["response"])
        except requests.exceptions.RequestException as e:
            st.error(f"An error occurred: {e}")
    else:
        st.warning("Please enter a prompt.")

# --- Footer ---
st.markdown(
    """
    <div style="
        position: fixed; 
        bottom: 20px; 
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
