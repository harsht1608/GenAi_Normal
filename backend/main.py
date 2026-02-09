# main.py
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
# --- GROQ / OpenAI client (GROQ) ---
from openai import OpenAI
# --- OpenAI (commented out) ---
# import google.generativeai as genai
from dotenv import load_dotenv
import os
import logging
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import time
from datetime import datetime
import subprocess
import json

# --- Load env ---
load_dotenv()
# --- GEMINI (commented out) ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# if not GEMINI_API_KEY:
#     raise RuntimeError("GEMINI_API_KEY environment variable not set")

# --- GROQ / OpenAI key and client ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = None
if GROQ_API_KEY:
    groq_client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")

# --- OpenAI key and client (commented out) ---
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# openai_client = None
# if OPENAI_API_KEY:
#     openai_client = OpenAI(api_key=OPENAI_API_KEY)

DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-1.5-flash")
ALLOWED_MODELS = [
    m.strip()
    for m in os.getenv("ALLOWED_MODELS", ",".join([DEFAULT_MODEL, "gemini-1.5-pro", "gemini-2.0-flash"])).split(",")
    if m.strip()
]

RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "60"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

# --- Configure Gemini (commented out) ---
# genai.configure(api_key=GEMINI_API_KEY)

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

class GenerationRequest(BaseModel):
    description: str
    model: Optional[str] = None

class GenerationResponse(BaseModel):
    code: str
    model: str

class SecurityRequest(BaseModel):
    requirements: str
    model: Optional[str] = None

class SecurityResponse(BaseModel):
    vulnerabilities: str
    recommendations: str
    model: str

# --- Helpers ---
def call_groq(prompt: str, model_name: Optional[str] = None) -> str:
    """Call GROQ/OpenAI Responses API via the `openai.OpenAI` client.
    Falls back to returning an error if GROQ client not configured.
    """
    model_name = model_name or DEFAULT_MODEL
    # NOTE: ALLOWED_MODELS check kept for parity with prior code
    if model_name not in ALLOWED_MODELS:
        raise HTTPException(status_code=400, detail=f"Model '{model_name}' not allowed.")

    if not groq_client:
        logger.error("GROQ client not configured (GROQ_API_KEY missing)")
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured on server")

    try:
        # Use the Responses API - mirrors the boilerplate provided by the user
        resp = groq_client.responses.create(
            input=prompt,
            model=model_name,
        )
        # Many SDK responses expose `output_text`; fall back to str(resp)
        return getattr(resp, "output_text", str(resp))
    except Exception as e:
        logger.exception("GROQ call failed")
        raise HTTPException(status_code=500, detail=f"GROQ error: {str(e)}")

# --- Security scanning helper ---
def scan_security_vulnerabilities(requirements_content: str) -> str:
    """Scan requirements.txt for vulnerabilities using safety package.
    Returns a formatted string of findings.
    """
    try:
        # Write requirements to temp file
        temp_file = "/tmp/requirements_temp.txt"
        with open(temp_file, "w") as f:
            f.write(requirements_content)
        
        # Run safety check
        result = subprocess.run(
            ["safety", "check", "--file", temp_file, "--json"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Parse output
        if result.returncode == 0:
            return "No vulnerabilities detected in your requirements."
        else:
            # Try to parse JSON output from safety
            try:
                vuln_data = json.loads(result.stdout)
                return json.dumps(vuln_data, indent=2)
            except:
                return result.stdout if result.stdout else "Vulnerabilities found - please review safety output."
    except subprocess.TimeoutExpired:
        return "Security scan timed out. Please try again."
    except FileNotFoundError:
        return "Safety package not installed. Install it with: pip install safety"
    except Exception as e:
        logger.exception("Security scan failed")
        return f"Error during security scan: {str(e)}"

# --- Original OpenAI function (commented out) ---
# def call_openai(prompt: str, model_name: Optional[str] = None) -> str:
#     """Call OpenAI Chat Completions API via the `openai.OpenAI` client.
#     Falls back to returning an error if OpenAI client not configured.
#     """
#     model_name = model_name or DEFAULT_MODEL
#     # NOTE: ALLOWED_MODELS check kept for parity with prior code
#     if model_name not in ALLOWED_MODELS:
#         raise HTTPException(status_code=400, detail=f"Model '{model_name}' not allowed.")
#
#     if not openai_client:
#         logger.error("OpenAI client not configured (OPENAI_API_KEY missing)")
#         raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured on server")
#
#     try:
#         # Use the Chat Completions API from OpenAI
#         resp = openai_client.chat.completions.create(
#             model=model_name,
#             messages=[
#                 {"role": "user", "content": prompt}
#             ]
#         )
#         # Extract text from the first choice
#         return resp.choices[0].message.content
#     except Exception as e:
#         logger.exception("OpenAI call failed")
#         raise HTTPException(status_code=500, detail=f"OpenAI error: {str(e)}")

# --- Original Gemini function kept for reference (commented) ---
# def call_gemini(prompt: str, model_name: Optional[str] = None) -> str:
#     model_name = model_name or DEFAULT_MODEL
#     if model_name not in ALLOWED_MODELS:
#         raise HTTPException(status_code=400, detail=f"Model '{model_name}' not allowed.")
#
#     try:
#         model = genai.GenerativeModel(model_name)
#         resp = model.generate_content([prompt])
#         return getattr(resp, "text", str(resp))
#     except Exception as e:
#         logger.exception("Gemini call failed")
#         raise HTTPException(status_code=500, detail=f"Gemini error: {str(e)}")

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
    text = call_groq(payload.prompt, payload.model)
    return AskResponse(response=text, model=payload.model or DEFAULT_MODEL)

# --- DevOps Endpoints ---
@app.post("/analyze-logs", response_model=DevOpsResponse)
async def analyze_logs(req: DevOpsRequest):
    prompt = f"Analyze these logs and highlight errors, warnings, and possible fixes:\n\n{req.content}"
    text = call_groq(prompt, req.model)
    return DevOpsResponse(suggestions=text, model=req.model or DEFAULT_MODEL)

@app.post("/optimize-docker", response_model=DevOpsResponse)
async def optimize_docker(req: DevOpsRequest):
    prompt = f"Review this Dockerfile and suggest optimizations, best practices, and security improvements:\n\n{req.content}"
    text = call_groq(prompt, req.model)
    return DevOpsResponse(suggestions=text, model=req.model or DEFAULT_MODEL)

@app.post("/fix-ci", response_model=DevOpsResponse)
async def fix_ci(req: DevOpsRequest):
    prompt = f"Analyze this CI/CD pipeline YAML and suggest improvements for reliability, caching, and efficiency:\n\n{req.content}"
    text = call_groq(prompt, req.model)
    return DevOpsResponse(suggestions=text, model=req.model or DEFAULT_MODEL)

# --- Code Generation Endpoints ---
@app.post("/generate-dockerfile", response_model=GenerationResponse)
async def generate_dockerfile(req: GenerationRequest):
    prompt = f"""Generate a production-ready Dockerfile based on this description:
{req.description}

Include best practices for:
- Multi-stage builds
- Minimal image size
- Security hardening
- Layer caching optimization

Provide only the Dockerfile content without explanations."""
    code = call_groq(prompt, req.model)
    return GenerationResponse(code=code, model=req.model or DEFAULT_MODEL)

@app.post("/generate-cicd", response_model=GenerationResponse)
async def generate_cicd(req: GenerationRequest):
    prompt = f"""Generate a complete CI/CD pipeline configuration based on this description:
{req.description}

Include:
- Build steps
- Testing stages
- Security scanning
- Deployment strategy
- Notifications

Provide the configuration file (GitHub Actions YAML, Jenkins, or GitLab CI) without explanations."""
    code = call_groq(prompt, req.model)
    return GenerationResponse(code=code, model=req.model or DEFAULT_MODEL)

@app.post("/generate-k8s", response_model=GenerationResponse)
async def generate_k8s(req: GenerationRequest):
    prompt = f"""Generate Kubernetes YAML manifests based on this description:
{req.description}

Include:
- Deployment/StatefulSet
- Service
- ConfigMap
- Secrets (if needed)
- Health checks
- Resource limits

Provide complete Kubernetes manifests without explanations."""
    code = call_groq(prompt, req.model)
    return GenerationResponse(code=code, model=req.model or DEFAULT_MODEL)

@app.post("/generate-iac", response_model=GenerationResponse)
async def generate_iac(req: GenerationRequest):
    prompt = f"""Generate Infrastructure as Code configuration based on this description:
{req.description}

Include:
- Resource definitions
- Network configuration
- Security groups/policies
- Monitoring setup
- Environment variables

Provide Terraform or CloudFormation code without explanations."""
    code = call_groq(prompt, req.model)
    return GenerationResponse(code=code, model=req.model or DEFAULT_MODEL)

@app.post("/scan-security", response_model=SecurityResponse)
async def scan_security(req: SecurityRequest):
    """Scan requirements.txt for vulnerabilities and provide recommendations."""
    # First, run safety check
    vuln_summary = scan_security_vulnerabilities(req.requirements)
    
    # Then use GROQ to analyze and recommend fixes
    prompt = f"""Analyze these security scan results and provide remediation recommendations:

SCAN RESULTS:
{vuln_summary}

REQUIREMENTS FILE:
{req.requirements}

Provide:
1. Summary of vulnerabilities found
2. Risk assessment (critical/high/medium/low)
3. Recommended fixes and package updates
4. Best practices for secure dependency management"""
    
    recommendations = call_groq(prompt, req.model)
    
    return SecurityResponse(
        vulnerabilities=vuln_summary,
        recommendations=recommendations,
        model=req.model or DEFAULT_MODEL
    )
