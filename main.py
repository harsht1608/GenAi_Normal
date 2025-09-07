from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set")

# Configure Gemini
genai.configure(api_key=API_KEY)

app = FastAPI()

class UserQuery(BaseModel):
    prompt: str

class GeminiResponse(BaseModel):
    response: str

@app.post("/ask-gemini", response_model=GeminiResponse)
def ask_gemini(query: UserQuery):
    try:
        # Use updated Gemini model
        model = genai.GenerativeModel("gemini-1.5-flash")

        # Send prompt
        response = model.generate_content([query.prompt])

        return GeminiResponse(response=response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
