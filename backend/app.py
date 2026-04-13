"""
Sphinx-SCA — Backend API (v3 Stable)
"""

import os
import sys
import uvicorn
import logging
from typing import Optional, Any
from dotenv import load_dotenv
import re

# Load .env file at the very beginning
load_dotenv()
from fastapi import FastAPI, UploadFile, File, Request, Response, Form
from pydantic import BaseModel
from pydantic import Field
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

# Add PROJECT_ROOT and the math_engine package roots to sys.path.
# This makes imports work consistently when running via:
# - `uvicorn backend.app:app`
# - `python backend/app.py`
# - deployed process managers that set different working directories
def _safe_sys_path_prepend(p: str) -> None:
    if p and p not in sys.path:
        sys.path.insert(0, p)

_safe_sys_path_prepend(PROJECT_ROOT)
_safe_sys_path_prepend(os.path.join(BASE_DIR, "math_engine"))              # allows `import math_engine...`
_safe_sys_path_prepend(os.path.join(BASE_DIR, "math_engine", "math_engine"))  # legacy fallback (modules as top-level)

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
    # Preferred (package) import
    from math_engine.algebra.algebra_engine import solve as algebra_solve
    print("✅ Algebra engine loaded")
except Exception as e:
    try:
        # Legacy fallback (when math_engine/math_engine is on sys.path)
        from algebra.algebra_engine import solve as algebra_solve
        print("✅ Algebra engine loaded (legacy import)")
    except Exception as e2:
        algebra_solve = None
        print(f"⚠️ Algebra engine failed: {e} / {e2}")

try:
    from math_engine import calculus as _calculus
    calculus_solve = _calculus.solve
    print("✅ Calculus engine loaded")
except Exception as e:
    try:
        import calculus as _calculus  # legacy fallback
        calculus_solve = _calculus.solve
        print("✅ Calculus engine loaded (legacy import)")
    except Exception as e2:
        calculus_solve = None
        print(f"⚠️ Calculus engine failed: {e} / {e2}")

try:
    from math_engine import geometry as _geometry
    geometry_solve = _geometry.solve
    print("✅ Geometry engine loaded")
except Exception as e:
    try:
        import geometry as _geometry  # legacy fallback
        geometry_solve = _geometry.solve
        print("✅ Geometry engine loaded (legacy import)")
    except Exception as e2:
        geometry_solve = None
        print(f"⚠️ Geometry engine failed: {e} / {e2}")

try:
    from math_engine import statistics_engine as _statistics_engine
    statistics_solve = _statistics_engine.solve
    print("✅ Statistics engine loaded")
except Exception as e:
    try:
        import statistics_engine as _statistics_engine  # legacy fallback
        statistics_solve = _statistics_engine.solve
        print("✅ Statistics engine loaded (legacy import)")
    except Exception as e2:
        statistics_solve = None
        print(f"⚠️ Statistics engine failed: {e} / {e2}")

try:
    from math_engine import linear_algebra as _linear_algebra
    linear_algebra_solve = _linear_algebra.solve
    print("✅ Linear algebra engine loaded")
except Exception as e:
    try:
        import linear_algebra as _linear_algebra  # legacy fallback
        linear_algebra_solve = _linear_algebra.solve
        print("✅ Linear algebra engine loaded (legacy import)")
    except Exception as e2:
        linear_algebra_solve = None
        print(f"⚠️ Linear algebra engine failed: {e} / {e2}")

print(f"📦 Engines Loaded: Algebra={algebra_solve is not None}, Calculus={calculus_solve is not None}, Geometry={geometry_solve is not None}")

# ─────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────

# ✅ FIX: Restrict CORS to known origins instead of wildcard
_raw_origins = os.getenv("ALLOWED_ORIGINS", "https://sphinx-sca-production.up.railway.app").split(",")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins if o.strip()]

# ✅ FIX (S-12): Only add local dev origins when not in production
_is_production = os.getenv("ENV", "development").lower() == "production"
if not _is_production:
    LOCAL_DEFAULTS = [
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
        "http://localhost:8000", "http://127.0.0.1:8000",
    ]
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

# ✅ FIX (W-13): Add fallback import for presentation
try:
    from backend.presentation import attach_presentation_fields
except ImportError:
    from presentation import attach_presentation_fields

RATE_LIMIT_REQUESTS = 60
RATE_LIMIT_WINDOW_SECONDS = 60
_MAX_TRACKED_IPS = 10000  # ✅ FIX (C-04): prevent unbounded memory growth
ip_requests = defaultdict(list)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Skip rate limiting for OPTIONS preflight requests
    if request.method == "OPTIONS":
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()

    # Clean up old requests for this IP
    ip_requests[client_ip] = [req_time for req_time in ip_requests[client_ip] if now - req_time < RATE_LIMIT_WINDOW_SECONDS]

    # ✅ FIX (C-04): Evict stale IPs periodically to prevent memory leak
    if len(ip_requests) > _MAX_TRACKED_IPS:
        stale_ips = [ip for ip, times in ip_requests.items() if not times or (now - max(times)) > RATE_LIMIT_WINDOW_SECONDS]
        for ip in stale_ips:
            del ip_requests[ip]

    if len(ip_requests[client_ip]) >= RATE_LIMIT_REQUESTS:
        return JSONResponse(status_code=429, content={"detail": "Too Many Requests"})

    ip_requests[client_ip].append(now)
    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# REQUEST MODELS
# ─────────────────────────────────────────────

class QuestionRequest(BaseModel):
    question: str = Field(..., max_length=10000)  # ✅ FIX (S-01): limit input size
    history: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    mode: str = "general"
    image_data: Optional[str] = None
    user_id: Optional[str] = None          # ✅ Memory: user identity

class HintRequest(BaseModel):
    question: str = Field(..., max_length=10000)
    problem_type: str = "algebra"
    num_hints: int = Field(default=3, ge=1, le=5)

class StudyRequest(BaseModel):
    question: str = Field(..., max_length=10000)
    branch: str = "algebra"
    session_id: Optional[str] = None
    user_id: Optional[str] = None          # ✅ Memory: user identity for study mode

class CheckRequest(BaseModel):
    session_id: str
    question: str = Field(..., max_length=10000)
    branch: str = "algebra"
    student_answer: str = Field(..., max_length=5000)
    correct_answer: str = Field(..., max_length=5000)
    user_id: Optional[str] = None          # ✅ Memory: user identity for study mode

# ─────────────────────────────────────────────
# SOLVER HELPER
# ─────────────────────────────────────────────

def run_solver(fn, *args, **kwargs):

    if fn is None:
        return {"success": False, "error": "engine not available"}

    try:
        result = fn(*args, **kwargs)

        if isinstance(result, dict):
            # Preserve the engine's own success flag if present.
            if "success" in result:
                return result
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

async def route_and_solve(
    question: str,
    history: Optional[list[dict[str, Any]]] = None,
    mode: str = "general",
    user_id: Optional[str] = None,          # ✅ Memory: passed through pipeline
) -> dict[str, Any]:

    if history is None:
        history = []

    raw_question = (question or "").strip()
    logger.info("Question: %s | User: %s", raw_question, user_id)

    if llm is None:
        return {
            "success": False,
            "error": "LLM not available"
        }

    def _normalize_mode(m: str) -> str:
        m = (m or "").strip().lower()
        return m if m in {"general", "think", "steps"} else "general"

    mode = _normalize_mode(mode)

    def _parser_key_for_branch(b: str) -> str:
        """
        `LLMManager.parse()` expects a parser key, not necessarily the classifier branch.
        - classifier uses: linear_algebra
        - parser prompt uses: matrix
        """
        if b == "linear_algebra":
            return "matrix"
        return b

    def _heuristic_engine_input(raw: str) -> str:
        """
        Best-effort fallback when LLM parsing is unavailable.
        Strips common instruction prefixes that break SymPy parsing.
        """
        s = (raw or "").strip()
        s = re.sub(r"^(please\s+)?(solve|simplify|factor|expand|differentiate|derive|integrate|find)\b[:\s]+", "", s, flags=re.I)
        s = s.strip()
        return s or raw

    # 1️⃣ classify
    try:
        c = llm.classify(raw_question)
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
            chat_question = raw_question
            if mode == "think":
                chat_question = f"{raw_question}\n\nPlease explain thoroughly and clearly."
            elif mode == "steps":
                chat_question = f"{raw_question}\n\nPlease respond with a clear step-by-step explanation."

            # ✅ Memory: pass user_id to chat so memory is loaded/saved
            answer = await llm.chat(chat_question, history, user_id=user_id)

            return attach_presentation_fields(
                question=raw_question,
                branch="chat",
                mode=mode,
                result={
                    "success": True,
                    "branch": "chat",
                    "final_answer": answer,
                    "is_chat": True,
                    "llm_steps": []
                },
            )

        except Exception as e:
            logger.error("Chat error: %s", e, exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    # 3️⃣ parse
    try:
        parsed = llm.parse(raw_question, _parser_key_for_branch(branch))
    except Exception as e:
        logger.warning("Parse failed: %s", e)
        parsed = {}

    # 4️⃣ solve
    result: dict[str, Any] = {"success": False}

    if branch == "algebra":
        expr = parsed.get("expression") or _heuristic_engine_input(raw_question)
        result = run_solver(algebra_solve, expr)

    elif branch == "calculus":
        expr = parsed.get("expression") or _heuristic_engine_input(raw_question)
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
                raw_question,
                str(result.get("final_answer", "")),
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
            steps = llm.steps(raw_question, str(result.get("final_answer", "")), branch)
            result["llm_steps"] = steps
        except Exception as e:
            logger.warning("Steps (mode=steps) generation failed: %s", e)

    # 7️⃣ ✅ Memory: wrap math result in friendly memory-aware response if user_id present
    if user_id and result.get("success"):
        try:
            friendly_answer = await llm.chat_with_math(raw_question, result, history, user_id=user_id)
            result["final_answer"] = friendly_answer
        except Exception as e:
            logger.warning("Friendly math response failed: %s", e)

    return attach_presentation_fields(
        question=raw_question,
        branch=branch,
        mode=mode,
        result=result,
    )

# ─────────────────────────────────────────────
# STUDY MODE HELPERS
# ─────────────────────────────────────────────

# ✅ FIX (W-14): Add fallback import for study_agent
try:
    from backend.study_agent import get_study_agent
except ImportError:
    from study_agent import get_study_agent

def render_study_markdown(result: dict) -> str:
    """
    Renders study result into clean markdown — NO fixed section headers.
    """
    parts = []

    if result.get("concept_explanation"):
        parts.append(result["concept_explanation"])

    if result.get("socratic_question"):
        parts.append(result["socratic_question"])

    if result.get("hint_text"):
        hints_left = result.get("hints_remaining", 0)
        parts.append(f"💡 *({hints_left} hint{'s' if hints_left != 1 else ''} remaining)*\n\n" + result["hint_text"])

    if result.get("solve_output"):
        parts.append(result["solve_output"])

    if result.get("mistake_feedback"):
        parts.append(result["mistake_feedback"])

    if result.get("practice_problem"):
        parts.append(result["practice_problem"])

    if result.get("session_summary"):
        parts.append(result["session_summary"])
        stats = result.get("stats", {})
        if stats:
            parts.append(
                f"📊 **{stats.get('problems_solved', 0)}** solved · "
                f"**{stats.get('hints_used', 0)}** hints · "
                f"**{stats.get('total_attempts', 0)}** attempts"
            )

    if not parts:
        parts.append(result.get("error") or "Session updated.")

    return "\n\n".join(parts)

# ─────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────

# ── Intent-based fast endpoints ──────────────────────────────────

@app.post("/study/chat")
async def study_chat(req: StudyRequest):
    """Casual chat — no graph, direct LLM."""
    agent = get_study_agent()
    result = await asyncio.to_thread(agent.chat, req.question)
    return result

@app.post("/study/explain")
async def study_explain(req: StudyRequest):
    """Explain a concept — direct LLM, no graph."""
    agent = get_study_agent()
    result = await asyncio.to_thread(agent.explain, req.question, req.branch)
    return result

@app.post("/study/help")
async def study_help(req: StudyRequest):
    """Help confused user — direct LLM, no graph."""
    agent = get_study_agent()
    result = await asyncio.to_thread(agent.help_user, req.question, req.branch)
    return result

@app.post("/study/classify")
async def study_classify(req: StudyRequest):
    """Classify user intent — returns casual/study/explain/help."""
    agent = get_study_agent()
    intent = agent.classify_intent(req.question)
    return {"intent": intent}

# ── Graph-based study endpoints (memory-enriched) ─────────────────

@app.post("/study/start")
async def study_start(req: StudyRequest):
    agent = get_study_agent()
    result = await agent.start(req.question, req.branch, user_id=req.user_id or "")
    result["display_markdown"] = render_study_markdown(result)
    return result

@app.post("/study/hint")
async def study_hint(req: StudyRequest):
    if not req.session_id:
        return {"success": False, "error": "session_id is required"}
    agent = get_study_agent()
    result = await agent.hint(req.session_id, req.question, req.branch, user_id=req.user_id or "")
    result["display_markdown"] = render_study_markdown(result)
    return result

@app.post("/study/solve")
async def study_solve(req: StudyRequest):
    """Immediately solve — full solution, no Socratic."""
    if not req.session_id:
        return {"success": False, "error": "session_id is required"}
    agent = get_study_agent()
    result = await agent.solve(req.session_id, req.question, req.branch, user_id=req.user_id or "")
    result["display_markdown"] = render_study_markdown(result)
    return result

@app.post("/study/check")
async def study_check(req: CheckRequest):
    agent = get_study_agent()
    result = await agent.check(
        req.session_id,
        req.question,
        req.branch,
        req.student_answer,
        req.correct_answer,
        user_id=req.user_id or ""
    )
    result["display_markdown"] = render_study_markdown(result)
    return result

@app.post("/study/next")
async def study_next(req: StudyRequest):
    if not req.session_id:
        return {"success": False, "error": "session_id is required"}
    agent = get_study_agent()
    result = await agent.next(req.session_id, req.question, req.branch, user_id=req.user_id or "")
    result["display_markdown"] = render_study_markdown(result)
    return result

@app.post("/study/next_harder")
async def study_next_harder(req: StudyRequest):
    if not req.session_id:
        return {"success": False, "error": "session_id is required"}
    agent = get_study_agent()
    result = await agent.next_harder(req.session_id, req.question, req.branch, user_id=req.user_id or "")
    result["display_markdown"] = render_study_markdown(result)
    return result

@app.post("/study/summary")
async def study_summary(req: StudyRequest):
    if not req.session_id:
        return {"success": False, "error": "session_id is required"}
    agent = get_study_agent()
    result = await agent.finish(req.session_id, req.question, req.branch, user_id=req.user_id or "")
    result["display_markdown"] = render_study_markdown(result)
    return result

# ── Main solve endpoints ──────────────────────────────────────────

@app.post("/solve")
async def solve(req: QuestionRequest):
    # ✅ Memory: pass user_id through to pipeline
    return await route_and_solve(req.question, req.history, req.mode, user_id=req.user_id)


@app.post("/solve_stream")
async def solve_stream(req: QuestionRequest):
    """Streaming endpoint for chat-like experience."""
    if llm is None:
        return JSONResponse({"success": False, "error": "LLM not initialized"}, status_code=500)

    # Capture a non-None reference for type checkers and closures.
    llm_local = llm

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
            if req.image_data:
                try:
                    import backend.vision_scout as vision_scout
                except ImportError:
                    import vision_scout

                image_context = await asyncio.to_thread(vision_scout.analyze_image_base64, req.image_data)

                # Inject the extracted context into the main LLM's prompt
                enhanced_prompt = f"Image Description (extracted by Vision Scout):\n{image_context}\n\nUser Question:\n{messages[-1]['content']}"
                messages[-1]["content"] = enhanced_prompt

                # ✅ Memory: stream with user_id
                async for chunk in llm_local.stream_chat(messages, user_id=req.user_id):
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
            else:
                # ✅ Memory: stream with user_id
                async for chunk in llm_local.stream_chat(messages, user_id=req.user_id):
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
        except asyncio.CancelledError:
            logger.info("Client disconnected during stream")
        except Exception as e:
            logger.error("Streaming error: %s", e, exc_info=True)
            yield f"data: {json.dumps({'error': 'Stream interrupted'})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(chunk_generator(), media_type="text/event-stream")


@app.post("/ocr")
async def process_ocr(file: UploadFile = File(...), user_id: str = Form(None)):
    try:
        content = await file.read()

        # Optionally upload to supabase if configured (silent fail if not)
        image_url = None
        try:
            # ✅ FIX (W-11): Removed duplicate `import os` — already imported at top
            if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"):
                try:
                    from backend.supabase_ocr import upload_image
                except ImportError:
                    from supabase_ocr import upload_image
                image_url = await upload_image(
                    content,
                    file.filename or "upload",
                    file.content_type or "application/octet-stream",
                )
        except Exception as e:
            logger.warning(f"Supabase upload failed or not available: {e}")

        try:
            import backend.vision_scout as vision_scout
        except ImportError:
            import vision_scout

        # ✅ FIX (W-15): Use asyncio.to_thread to avoid blocking the event loop
        extracted_text = await asyncio.to_thread(vision_scout.analyze_image_bytes, content)

        return {
            "success": True,
            "raw_text": extracted_text,
            "image_url": image_url
        }
    except Exception as e:
        logger.error(f"OCR failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


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

FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")

ALLOWED_FILES = [
    "index.html",
    "dashboard.html",
    "login.html",
    "signup.html",
    "about.html",
    "study-mode.html",
    "study-mode.js",
    "app.js",
    "style.css",
    "logo.png",
    "user.png",
    "bg.jpg",
    "supabaseClient.js"
]

@app.get("/")
async def home():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/{file_path:path}")
async def serve_static(file_path: str):
    full_path = os.path.join(FRONTEND_DIR, file_path)
    # Basic directory traversal protection
    if os.path.abspath(full_path).startswith(os.path.abspath(FRONTEND_DIR)):
        if os.path.exists(full_path) and os.path.isfile(full_path):
            return FileResponse(full_path)
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