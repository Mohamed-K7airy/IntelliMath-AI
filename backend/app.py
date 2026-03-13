"""
Sphinx-SCA — Backend API (v3 Stable)
"""

import os
import sys
import uvicorn
import logging
from typing import Optional
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# ─────────────────────────────────────────────
# PATH CONFIG
# ─────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

sys.path.append(PROJECT_ROOT)

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
except:
    from backend.llm_manager import LLMManager

try:
    llm = LLMManager()
    print("✅ LLM Manager loaded")
except Exception as e:
    llm = None
    print("⚠️ LLM Manager failed:", e)

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
except:
    algebra_solve = None

try:
    import calculus
    calculus_solve = calculus.solve
except:
    calculus_solve = None

try:
    import geometry
    geometry_solve = geometry.solve
except:
    geometry_solve = None

try:
    import statistics_engine
    statistics_solve = statistics_engine.solve
except:
    statistics_solve = None

try:
    import linear_algebra
    linear_algebra_solve = linear_algebra.solve
except:
    linear_algebra_solve = None

# ─────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────

app = FastAPI(
    title="Sphinx-SCA API",
    version="3.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# REQUEST MODELS
# ─────────────────────────────────────────────

class QuestionRequest(BaseModel):
    question: str
    history: Optional[list] = []

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
        return {
            "success": False,
            "error": str(e)
        }

# ─────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────

def route_and_solve(question: str, history: list = None):

    if history is None:
        history = []

    logger.info("Question: %s", question)

    if llm is None:
        return {
            "success": False,
            "error": "LLM not available"
        }

    # 1️⃣ classify
    try:
        c = llm.classify(question)
        branch = c.get("branch", "algebra")
        problem_type = c.get("problem_type", "solve")
        is_math = c.get("is_math", True)
    except:
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
            return {
                "success": False,
                "error": str(e)
            }

    # 3️⃣ parse
    try:
        parsed = llm.parse(question, branch)
    except:
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

        try:
            wp = llm.word_problem(question)

            result = {
                "success": True,
                "final_answer": wp.get("answer_sentence")
            }

        except:
            pass

    # 6️⃣ steps
    if result.get("success"):

        try:
            steps = llm.steps(
                question,
                result.get("final_answer", ""),
                branch
            )
        except:
            steps = []

        result["llm_steps"] = steps

    result["branch"] = branch
    result["problem_type"] = problem_type
    result["is_chat"] = False

    return result

# ─────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────

@app.post("/solve")
async def solve(req: QuestionRequest):
    return route_and_solve(req.question, req.history)


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
        return {
            "success": False,
            "error": str(e)
        }

# ─────────────────────────────────────────────
# HEALTH
# ─────────────────────────────────────────────

@app.get("/health")
async def health():

    return {
        "status": "ok",
        "llm_loaded": llm is not None
    }

# ─────────────────────────────────────────────
# SERVE FRONTEND
# ─────────────────────────────────────────────

FRONTEND_DIR = PROJECT_ROOT

@app.get("/")
async def home():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/index.html")
async def index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/dashboard.html")
async def dashboard():
    return FileResponse(os.path.join(FRONTEND_DIR, "dashboard.html"))

@app.get("/login.html")
async def login():
    return FileResponse(os.path.join(FRONTEND_DIR, "login.html"))

@app.get("/signup.html")
async def signup():
    return FileResponse(os.path.join(FRONTEND_DIR, "signup.html"))

@app.get("/style.css")
async def style():
    return FileResponse(os.path.join(FRONTEND_DIR, "style.css"))

@app.get("/logo.png")
async def logo():
    return FileResponse(os.path.join(FRONTEND_DIR, "logo.png"))

@app.get("/user.png")
async def user_img():
    return FileResponse(os.path.join(FRONTEND_DIR, "user.png"))

@app.get("/bg.jpg")
async def bg():
    return FileResponse(os.path.join(FRONTEND_DIR, "bg.jpg"))

@app.get("/supabaseClient.js")
async def supabase_client():
    return FileResponse(os.path.join(FRONTEND_DIR, "supabaseClient.js"))

# ─────────────────────────────────────────────
# RUN SERVER
# ─────────────────────────────────────────────

if __name__ == "__main__":

    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000))
    )
