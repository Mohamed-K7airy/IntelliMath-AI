"""
Sphinx-SCA — Backend API (v3 Stable)
"""

import os
import sys
import uvicorn
import logging
from typing import Optional
from dotenv import load_dotenv

# Load .env file at the very beginning
load_dotenv()
from fastapi import FastAPI, UploadFile, File, Request, Response
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import json
import asyncio

# ─────────────────────────────────────────────
# PATH CONFIG
# ─────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# Add PROJECT_ROOT and the math_engine folder to sys.path
sys.path.append(PROJECT_ROOT)
sys.path.append(os.path.join(PROJECT_ROOT, "math_engine", "math_engine"))

# ─────────────────────────────────────────────
# ENVIRONMENT
# ─────────────────────────────────────────────

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("⚠️ GROQ_API_KEY not found in environment variables")
else:
    print("🔑 Groq API key loaded")

# ─────────────────────────────────────────────
# LOAD LLM MANAGER
# ─────────────────────────────────────────────

try:
    from backend.llm_manager import LLMManager
except ImportError:
    try:
        from llm_manager import LLMManager
    except ImportError:
        LLMManager = None

if LLMManager:
    try:
        llm = LLMManager()
        print("✅ LLM Manager loaded")
    except Exception as e:
        llm = None
        print("⚠️ LLM Manager failed:", e)
else:
    llm = None
    print("⚠️ LLM Manager class could not be imported")

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sphinx")

# ─────────────────────────────────────────────
# MATH ENGINE IMPORTS
# ─────────────────────────────────────────────

try:
    from algebra.algebra_engine import solve as algebra_solve
    print("✅ Algebra engine loaded")
except Exception as e:
    algebra_solve = None
    print(f"⚠️ Algebra engine failed: {e}")

try:
    import calculus
    calculus_solve = calculus.solve
    print("✅ Calculus engine loaded")
except Exception as e:
    calculus_solve = None
    print(f"⚠️ Calculus engine failed: {e}")

try:
    import geometry
    geometry_solve = geometry.solve
    print("✅ Geometry engine loaded")
except Exception as e:
    geometry_solve = None
    print(f"⚠️ Geometry engine failed: {e}")

try:
    import statistics_engine
    statistics_solve = statistics_engine.solve
    print("✅ Statistics engine loaded")
except Exception as e:
    statistics_solve = None
    print(f"⚠️ Statistics engine failed: {e}")

try:
    import linear_algebra
    linear_algebra_solve = linear_algebra.solve
    print("✅ Linear algebra engine loaded")
except Exception as e:
    linear_algebra_solve = None
    print(f"⚠️ Linear algebra engine failed: {e}")

print(f"📦 Engines Loaded: Algebra={algebra_solve is not None}, Calculus={calculus_solve is not None}, Geometry={geometry_solve is not None}")

# ─────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────

# ✅ FIX: Restrict CORS to known origins instead of wildcard
_raw_origins = os.getenv("ALLOWED_ORIGINS", "https://sphinx-gpt-beta-production.up.railway.app").split(",")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins if o.strip()]

# Auto-add local dev origins if not present
LOCAL_DEFAULTS = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174", "http://localhost:8000", "http://127.0.0.1:8000"]
for origin in LOCAL_DEFAULTS:
    if origin not in ALLOWED_ORIGINS:
        ALLOWED_ORIGINS.append(origin)

app = FastAPI(
    title="Sphinx-SCA API",
    version="3.0"
)

# Simple In-Memory Rate Limiter (Token Bucket per IP)
import time
from fastapi import HTTPException
from collections import defaultdict

RATE_LIMIT_REQUESTS = 60
RATE_LIMIT_WINDOW_SECONDS = 60
ip_requests = defaultdict(list)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Skip rate limiting for OPTIONS preflight requests
    if request.method == "OPTIONS":
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    
    # Clean up old requests
    ip_requests[client_ip] = [req_time for req_time in ip_requests[client_ip] if now - req_time < RATE_LIMIT_WINDOW_SECONDS]
    
    if len(ip_requests[client_ip]) >= RATE_LIMIT_REQUESTS:
        return JSONResponse(status_code=429, content={"detail": "Too Many Requests"})
        
    ip_requests[client_ip].append(now)
    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for the Beta phase to handle custom domains like chat.sphinxcs.online
    allow_credentials=False, # Must be False when allow_origins is ["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# REQUEST MODELS
# ─────────────────────────────────────────────

class QuestionRequest(BaseModel):
    question: str
    history: Optional[list] = []
    mode: Optional[str] = "general"

class HintRequest(BaseModel):
    question: str
    problem_type: str = "algebra"
    num_hints: int = 3

# ─────────────────────────────────────────────
# SOLVER HELPER
# ─────────────────────────────────────────────

def run_solver(fn, *args, **kwargs):

    if fn is None:
        return {"success": False, "error": "engine not available"}

    try:
        result = fn(*args, **kwargs)

        if isinstance(result, dict):
            return {"success": True, **result}

        return {
            "success": True,
            "final_answer": str(result)
        }

    except Exception as e:
        # ✅ FIX: Log the actual error instead of swallowing it silently
        logger.error("Solver error in %s: %s", fn.__name__ if hasattr(fn, '__name__') else str(fn), e, exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }

# ─────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────

def route_and_solve(question: str, history: list = None, mode: str = "general"):

    if history is None:
        history = []

    logger.info("Question: %s", question)

    if llm is None:
        return {
            "success": False,
            "error": "LLM not available"
        }
    
    # Custom Processing for "Think" or "Steps" mode
    if mode == "think":
        question = f"[Think Deeply and Explain Thoroughly] {question}"
    elif mode == "steps":
        question = f"[Provide detailed step-by-step solution] {question}"

    # 1️⃣ classify
    try:
        c = llm.classify(question)
        branch = c.get("branch", "algebra")
        problem_type = c.get("problem_type", "solve")
        is_math = c.get("is_math", True)
    except Exception as e:
        logger.warning("Classification failed, defaulting to algebra: %s", e)
        branch = "algebra"
        problem_type = "solve"
        is_math = True

    # 2️⃣ chat
    if not is_math or branch == "chat":

        try:
            answer = llm.chat(question, history)

            return {
                "success": True,
                "branch": "chat",
                "final_answer": answer,
                "is_chat": True,
                "llm_steps": []
            }

        except Exception as e:
            logger.error("Chat error: %s", e, exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    # 3️⃣ parse
    try:
        parsed = llm.parse(question, branch)
    except Exception as e:
        logger.warning("Parse failed: %s", e)
        parsed = {}

    # 4️⃣ solve
    result = {"success": False}

    if branch == "algebra":

        expr = parsed.get("expression", question)
        result = run_solver(algebra_solve, expr)

    elif branch == "calculus":

        expr = parsed.get("expression", question)
        result = run_solver(calculus_solve, expr)

    elif branch == "geometry":

        shape = parsed.get("shape")
        find = parsed.get("find")
        known = parsed.get("known", {})
        result = run_solver(geometry_solve, shape, find, **known)

    elif branch == "statistics":

        data = parsed.get("data", [])
        op = parsed.get("operation", "mean")
        result = run_solver(statistics_solve, op, data=data)

    elif branch == "linear_algebra":

        op = parsed.get("operation", "determinant")
        matrix = parsed.get("matrix_a")
        result = run_solver(linear_algebra_solve, op, matrix=matrix)

    # 5️⃣ fallback to LLM
    if not result.get("success"):
        if branch == "word_problem":
            try:
                wp = llm.word_problem(question)
                result = {
                    "success": True,
                    "final_answer": wp.get("answer_sentence")
                }
            except Exception as e:
                logger.error("Word problem fallback failed: %s", e, exc_info=True)
                result["error"] = str(e)
        else:
            result = {"success": False, "error": "Math engine failed to solve the problem."}

    # 6️⃣ steps
    if result.get("success"):

        try:
            steps = llm.steps(
                question,
                result.get("final_answer", ""),
                branch
            )
        except Exception as e:
            logger.warning("Steps generation failed: %s", e)
            steps = []

        result["llm_steps"] = steps

    result["branch"] = branch
    result["problem_type"] = problem_type
    result["is_chat"] = False
    result["mode"] = mode

    # Ensure steps are generated if mode is 'steps' and not already present
    if mode == "steps" and not result.get("llm_steps") and result.get("success"):
        try:
            steps = llm.steps(question, result.get("final_answer", ""), branch)
            result["llm_steps"] = steps
        except Exception as e:
            logger.warning("Steps (mode=steps) generation failed: %s", e)

    return result

# ─────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────

@app.post("/solve")
async def solve(req: QuestionRequest):
    return route_and_solve(req.question, req.history, req.mode)


@app.post("/solve_stream")
async def solve_stream(req: QuestionRequest):
    """Streaming endpoint for chat-like experience."""
    if llm is None:
        return JSONResponse({"success": False, "error": "LLM not initialized"}, status_code=500)

    messages = []
    if req.history:
        for m in req.history:
            # Handle both 'sender' and 'role' for compatibility
            role = m.get('role') or ("user" if m.get("sender") == "user" else "assistant")
            content = m.get("content", "")
            if role and content:
                messages.append({"role": role, "content": content})
    
    # Add current question
    prompt = req.question
    if req.mode == "think":
        prompt = f"Please solve this and explain your deep thinking process: {req.question}"
    elif req.mode == "steps":
        prompt = f"Please provide a detailed step-by-step solution for: {req.question}"
        
    messages.append({"role": "user", "content": prompt})

    async def chunk_generator():
        try:
            for chunk in llm.stream_chat(messages):
                yield f"data: {json.dumps({'content': chunk})}\n\n"
        except asyncio.CancelledError:
            logger.info("Client disconnected during stream")
        except Exception as e:
            logger.error("Streaming error: %s", e, exc_info=True)
            yield f"data: {json.dumps({'error': 'Stream interrupted'})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(chunk_generator(), media_type="text/event-stream")


@app.post("/hints")
async def hints(req: HintRequest):

    if llm is None:
        return {"success": False}

    try:
        hints = llm.hints(req.question, req.problem_type, req.num_hints)

        return {
            "success": True,
            "hints": hints
        }

    except Exception as e:
        logger.error("Hints error: %s", e, exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }

# ─────────────────────────────────────────────
# HEALTH
# ─────────────────────────────────────────────

@app.get("/health")
async def health(response: Response):

    is_healthy = llm is not None and (algebra_solve is not None)
    if not is_healthy:
        response.status_code = 503

    return {
        "status": "ok" if is_healthy else "degraded",
        "llm_loaded": llm is not None,
        "engines": {
            "algebra": algebra_solve is not None,
            "calculus": calculus_solve is not None,
            "geometry": geometry_solve is not None,
            "statistics": statistics_solve is not None,
            "linear_algebra": linear_algebra_solve is not None,
        }
    }

# ─────────────────────────────────────────────
# SERVE FRONTEND
# ─────────────────────────────────────────────

FRONTEND_DIR = PROJECT_ROOT

ALLOWED_FILES = [
    "index.html", 
    "dashboard.html", 
    "login.html", 
    "signup.html", 
    "about.html", 
    "style.css", 
    "logo.png", 
    "user.png", 
    "bg.jpg", 
    "supabaseClient.js"
]

@app.get("/")
async def home():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/{filename}")
async def serve_static(filename: str):
    if filename in ALLOWED_FILES:
        return FileResponse(os.path.join(FRONTEND_DIR, filename))
    # For subdirectories like src/ or public/assets/ if requested dynamically, 
    # though usually they are built into dist. We return 404 for unauthorized root files.
    return JSONResponse({"error": "File not found"}, status_code=404)

# ─────────────────────────────────────────────
# RUN SERVER
# ─────────────────────────────────────────────

if __name__ == "__main__":

    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000))
    )
