# main.py
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv
import os
import logging
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import time

# --- Load env ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY environment variable not set")

# Optional configuration
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-1.5-flash")
ALLOWED_MODELS = [
    m.strip()
    for m in os.getenv("ALLOWED_MODELS", ",".join([DEFAULT_MODEL, "gemini-1.5-pro", "gemini-2.0-flash"])).split(",")
    if m.strip()
]

# Rate limiter config (simple in-memory)
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "60"))      # requests per window
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds

# CORS origins (comma separated), default '*' for dev
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

# --- Configure Gemini client ---
genai.configure(api_key=GEMINI_API_KEY)

# --- Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("gemini-backend")

# --- FastAPI app ---
app = FastAPI(title="Gemini Proxy API")

# CORS middleware
if CORS_ORIGINS.strip() == "*":
    allow = ["*"]
else:
    allow = [o.strip() for o in CORS_ORIGINS.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Simple in-memory rate limiter store ---
_client_requests = {}  # { client_ip: [timestamp1, timestamp2, ...] }

def is_rate_limited(client_ip: str) -> bool:
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    reqs = _client_requests.get(client_ip, [])
    # keep only timestamps within window
    reqs = [t for t in reqs if t > window_start]
    if len(reqs) >= RATE_LIMIT_MAX:
        _client_requests[client_ip] = reqs
        return True
    reqs.append(now)
    _client_requests[client_ip] = reqs
    return False

# --- Pydantic models ---
class AskRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_output_tokens: Optional[int] = None

class AskResponse(BaseModel):
    response: str
    model: str

# --- Health check ---
@app.get("/health")
def health():
    return {"status": "ok"}

# --- Main endpoint ---
@app.post("/ask-gemini", response_model=AskResponse)
async def ask_gemini(request: Request, payload: AskRequest):
    client_ip = request.client.host if request.client else "unknown"
    # rate limit
    if is_rate_limited(client_ip):
        logger.warning("Rate limit exceeded for %s", client_ip)
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")

    model_name = payload.model or DEFAULT_MODEL
    if model_name not in ALLOWED_MODELS:
        raise HTTPException(status_code=400, detail=f"Model '{model_name}' not allowed. Allowed: {ALLOWED_MODELS}")

    logger.info("Prompt received (client=%s) len=%d model=%s", client_ip, len(payload.prompt), model_name)
    try:
        model = genai.GenerativeModel(model_name)

        # Build kwargs (if supported by client)
        kwargs = {}
        if payload.temperature is not None:
            kwargs["temperature"] = float(payload.temperature)
        if payload.max_output_tokens is not None:
            kwargs["max_output_tokens"] = int(payload.max_output_tokens)

        # Call the model
        # NOTE: different versions of google.generativeai might return different structures.
        # We try to extract text robustly.
        raw_resp = model.generate_content([payload.prompt], **kwargs) if kwargs else model.generate_content([payload.prompt])

        # response text extraction helpers (robust)
        text = None
        try:
            # preferred: response.text (some client versions)
            text = getattr(raw_resp, "text", None)
        except Exception:
            text = None

        if not text:
            try:
                # fallback: look for candidates -> content -> parts[0].text
                candidates = getattr(raw_resp, "candidates", None)
                if not candidates and isinstance(raw_resp, dict):
                    candidates = raw_resp.get("candidates")
                if candidates:
                    first = candidates[0]
                    content = first.get("content") if isinstance(first, dict) else getattr(first, "content", None)
                    if content:
                        parts = content.get("parts") if isinstance(content, dict) else getattr(content, "parts", None)
                        if parts and len(parts) > 0:
                            first_part = parts[0]
                            text = first_part.get("text") if isinstance(first_part, dict) else getattr(first_part, "text", None)
            except Exception:
                text = None

        if not text:
            # last fallback: stringify
            text = str(raw_resp)

        logger.info("Got response (client=%s) len=%d model=%s", client_ip, len(text), model_name)
        return AskResponse(response=text, model=model_name)

    except Exception as e:
        logger.exception("Gemini call failed")
        # Expose minimal info to client
        raise HTTPException(status_code=500, detail=f"Failed to get response from Gemini: {str(e)}")
