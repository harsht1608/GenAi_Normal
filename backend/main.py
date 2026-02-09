# main.py
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
# --- Multiple LLM clients ---
from openai import OpenAI
import google.generativeai as genai
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

# --- GEMINI API Key and Client ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_client = None
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_client = True

# --- GROQ / OpenAI key and client ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = None
if GROQ_API_KEY:
    groq_client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")

# --- OpenAI key and client ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = None
if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

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
# Already configured above in the if block

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
    llm: Optional[str] = None  # LLM selector: groq, openai, gemini

class AskResponse(BaseModel):
    response: str
    model: str
    llm: str

class DevOpsRequest(BaseModel):
    content: str
    model: Optional[str] = None
    llm: Optional[str] = None  # LLM selector: groq, openai, gemini

class DevOpsResponse(BaseModel):
    suggestions: str
    model: str
    llm: str

class GenerationRequest(BaseModel):
    description: str
    model: Optional[str] = None
    llm: Optional[str] = None  # LLM selector: groq, openai, gemini

class GenerationResponse(BaseModel):
    code: str
    model: str
    llm: str

class SecurityRequest(BaseModel):
    requirements: str
    model: Optional[str] = None
    llm: Optional[str] = None  # LLM selector: groq, openai, gemini

class SecurityResponse(BaseModel):
    vulnerabilities: str
    recommendations: str
    model: str
    llm: str

# --- Helpers ---

def call_llm(prompt: str, llm_provider: str = "groq", model_name: Optional[str] = None) -> tuple:
    """
    Unified LLM caller that routes to the selected provider (groq, openai, or gemini).
    Returns: (response_text, llm_used, model_used)
    """
    model_name = model_name or DEFAULT_MODEL
    llm_provider = llm_provider or "groq"
    
    # Validate model
    if model_name not in ALLOWED_MODELS:
        raise HTTPException(status_code=400, detail=f"Model '{model_name}' not allowed.")
    
    # Route to the appropriate LLM
    if llm_provider == "groq":
        return call_groq(prompt, model_name)
    elif llm_provider == "openai":
        return call_openai(prompt, model_name)
    elif llm_provider == "gemini":
        return call_gemini(prompt, model_name)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown LLM provider: {llm_provider}")

def call_groq(prompt: str, model_name: Optional[str] = None) -> tuple:
    """Call GROQ/OpenAI Responses API via the `openai.OpenAI` client."""
    model_name = model_name or DEFAULT_MODEL
    
    if not groq_client:
        logger.error("GROQ client not configured (GROQ_API_KEY missing)")
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured on server")

    try:
        resp = groq_client.responses.create(
            input=prompt,
            model=model_name,
        )
        text = getattr(resp, "output_text", str(resp))
        return text, "groq", model_name
    except Exception as e:
        logger.exception("GROQ call failed")
        raise HTTPException(status_code=500, detail=f"GROQ error: {str(e)}")

def call_openai(prompt: str, model_name: Optional[str] = None) -> tuple:
    """Call OpenAI Chat Completions API."""
    model_name = model_name or DEFAULT_MODEL
    
    if not openai_client:
        logger.error("OpenAI client not configured (OPENAI_API_KEY missing)")
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured on server")

    try:
        resp = openai_client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        text = resp.choices[0].message.content
        return text, "openai", model_name
    except Exception as e:
        logger.exception("OpenAI call failed")
        raise HTTPException(status_code=500, detail=f"OpenAI error: {str(e)}")

def call_gemini(prompt: str, model_name: Optional[str] = None) -> tuple:
    """Call Google Gemini API."""
    model_name = model_name or DEFAULT_MODEL
    
    if not gemini_client:
        logger.error("Gemini client not configured (GEMINI_API_KEY missing)")
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured on server")

    try:
        model = genai.GenerativeModel(model_name)
        resp = model.generate_content([prompt])
        text = getattr(resp, "text", str(resp))
        return text, "gemini", model_name
    except Exception as e:
        logger.exception("Gemini call failed")
        raise HTTPException(status_code=500, detail=f"Gemini error: {str(e)}")

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

# --- Original OpenAI and Gemini functions (commented out - using unified call_llm) ---

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

    llm_provider = payload.llm or "groq"
    logger.info("Prompt from %s len=%d model=%s llm=%s", client_ip, len(payload.prompt), payload.model or DEFAULT_MODEL, llm_provider)
    text, llm_used, model_used = call_llm(payload.prompt, llm_provider, payload.model)
    return AskResponse(response=text, model=model_used, llm=llm_used)

# --- DevOps Endpoints ---
@app.post("/analyze-logs", response_model=DevOpsResponse)
async def analyze_logs(req: DevOpsRequest):
    prompt = f"Analyze these logs and highlight errors, warnings, and possible fixes:\n\n{req.content}"
    llm_provider = req.llm or "groq"
    text, llm_used, model_used = call_llm(prompt, llm_provider, req.model)
    return DevOpsResponse(suggestions=text, model=model_used, llm=llm_used)

@app.post("/optimize-docker", response_model=DevOpsResponse)
async def optimize_docker(req: DevOpsRequest):
    prompt = f"Review this Dockerfile and suggest optimizations, best practices, and security improvements:\n\n{req.content}"
    llm_provider = req.llm or "groq"
    text, llm_used, model_used = call_llm(prompt, llm_provider, req.model)
    return DevOpsResponse(suggestions=text, model=model_used, llm=llm_used)

@app.post("/fix-ci", response_model=DevOpsResponse)
async def fix_ci(req: DevOpsRequest):
    prompt = f"Analyze this CI/CD pipeline YAML and suggest improvements for reliability, caching, and efficiency:\n\n{req.content}"
    llm_provider = req.llm or "groq"
    text, llm_used, model_used = call_llm(prompt, llm_provider, req.model)
    return DevOpsResponse(suggestions=text, model=model_used, llm=llm_used)

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
    llm_provider = req.llm or "groq"
    code, llm_used, model_used = call_llm(prompt, llm_provider, req.model)
    return GenerationResponse(code=code, model=model_used, llm=llm_used)

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
    llm_provider = req.llm or "groq"
    code, llm_used, model_used = call_llm(prompt, llm_provider, req.model)
    return GenerationResponse(code=code, model=model_used, llm=llm_used)

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
    llm_provider = req.llm or "groq"
    code, llm_used, model_used = call_llm(prompt, llm_provider, req.model)
    return GenerationResponse(code=code, model=model_used, llm=llm_used)

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
    llm_provider = req.llm or "groq"
    code, llm_used, model_used = call_llm(prompt, llm_provider, req.model)
    return GenerationResponse(code=code, model=model_used, llm=llm_used)

@app.post("/scan-security", response_model=SecurityResponse)
async def scan_security(req: SecurityRequest):
    """Scan requirements.txt for vulnerabilities and provide recommendations."""
    # First, run safety check
    vuln_summary = scan_security_vulnerabilities(req.requirements)
    
    # Then use selected LLM to analyze and recommend fixes
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
    
    llm_provider = req.llm or "groq"
    recommendations, llm_used, model_used = call_llm(prompt, llm_provider, req.model)
    
    return SecurityResponse(
        vulnerabilities=vuln_summary,
        recommendations=recommendations,
        model=model_used,
        llm=llm_used
    )
