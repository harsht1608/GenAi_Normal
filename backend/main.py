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
from datetime import datetime

# --- Load env ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY environment variable not set")

DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-1.5-flash")
ALLOWED_MODELS = [
    m.strip()
    for m in os.getenv("ALLOWED_MODELS", ",".join([DEFAULT_MODEL, "gemini-1.5-pro", "gemini-2.0-flash"])).split(",")
    if m.strip()
]

RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "60"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

# --- Configure Gemini ---
genai.configure(api_key=GEMINI_API_KEY)

# --- Logging ---
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"backend_{datetime.now().strftime('%Y%m%d')}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file, encoding="utf-8"),
    ],
)
logger = logging.getLogger("gemini-backend")

# --- FastAPI app ---
app = FastAPI(title="Gemini Proxy API")

# CORS middleware
allow = ["*"] if CORS_ORIGINS.strip() == "*" else [o.strip() for o in CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Rate limiter ---
_client_requests = {}

def is_rate_limited(client_ip: str) -> bool:
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    reqs = _client_requests.get(client_ip, [])
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

class DevOpsRequest(BaseModel):
    content: str
    model: Optional[str] = None

class DevOpsResponse(BaseModel):
    suggestions: str
    model: str

# --- Helpers ---
def call_gemini(prompt: str, model_name: Optional[str] = None) -> str:
    model_name = model_name or DEFAULT_MODEL
    if model_name not in ALLOWED_MODELS:
        raise HTTPException(status_code=400, detail=f"Model '{model_name}' not allowed.")

    try:
        model = genai.GenerativeModel(model_name)
        resp = model.generate_content([prompt])
        return getattr(resp, "text", str(resp))
    except Exception as e:
        logger.exception("Gemini call failed")
        raise HTTPException(status_code=500, detail=f"Gemini error: {str(e)}")

# --- Health check ---
@app.get("/health")
def health():
    return {"status": "ok"}

# --- Main endpoint ---
@app.post("/ask-gemini", response_model=AskResponse)
async def ask_gemini(request: Request, payload: AskRequest):
    client_ip = request.client.host if request.client else "unknown"
    if is_rate_limited(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")

    logger.info("Prompt from %s len=%d model=%s", client_ip, len(payload.prompt), payload.model or DEFAULT_MODEL)
    text = call_gemini(payload.prompt, payload.model)
    return AskResponse(response=text, model=payload.model or DEFAULT_MODEL)

# --- DevOps Endpoints ---
@app.post("/analyze-logs", response_model=DevOpsResponse)
async def analyze_logs(req: DevOpsRequest):
    prompt = f"Analyze these logs and highlight errors, warnings, and possible fixes:\n\n{req.content}"
    text = call_gemini(prompt, req.model)
    return DevOpsResponse(suggestions=text, model=req.model or DEFAULT_MODEL)

@app.post("/optimize-docker", response_model=DevOpsResponse)
async def optimize_docker(req: DevOpsRequest):
    prompt = f"Review this Dockerfile and suggest optimizations, best practices, and security improvements:\n\n{req.content}"
    text = call_gemini(prompt, req.model)
    return DevOpsResponse(suggestions=text, model=req.model or DEFAULT_MODEL)

@app.post("/fix-ci", response_model=DevOpsResponse)
async def fix_ci(req: DevOpsRequest):
    prompt = f"Analyze this CI/CD pipeline YAML and suggest improvements for reliability, caching, and efficiency:\n\n{req.content}"
    text = call_gemini(prompt, req.model)
    return DevOpsResponse(suggestions=text, model=req.model or DEFAULT_MODEL)
