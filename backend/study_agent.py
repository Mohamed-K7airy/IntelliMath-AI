"""
Sphinx-SCA — Study Mode Agent (v6 — Fixed & Optimized)
=======================================================
Fixes over v5:
    1. asyncio.create_task inside sync _run → replaced with background thread
    2. Memory context passed correctly to LLM functions (not just state)
    3. Route logic: giveup intent → solve node directly
    4. All node outputs: consistent keys, no missing fields
    5. hints_remaining: always accurate
    6. analyze_mistake: now returns string (fixed in study_llm)
    7. Language: detect_language used everywhere

Graph Shape (unchanged, routing fixed):
    [init] → [route_after_action]
              ├── explain → (hard → socratic | else → END)
              ├── hint    → END
              ├── solve   → END
              ├── check   → practice(correct) / socratic(wrong) → END
              ├── practice → END
              └── summary  → END
"""

import os
import sys
import logging
import threading
import asyncio
from typing import TypedDict, Optional

if __name__ == "__main__" and __package__ is None:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from langgraph.graph import StateGraph, END

try:
    from backend.study_llm import StudyLLM
except ImportError:
    from study_llm import StudyLLM

try:
    from backend.study_session import (
        create_session, get_session, update_session, end_session,
        set_phase, add_attempt, use_hint, can_use_hint,
    )
except ImportError:
    from study_session import (
        create_session, get_session, update_session, end_session,
        set_phase, add_attempt, use_hint, can_use_hint,
    )

try:
    from backend.memory_manager import MemoryManager
except ImportError:
    from memory_manager import MemoryManager

logger = logging.getLogger("sphinx-study-agent")
study_llm = StudyLLM()
_memory   = MemoryManager()


# ═══════════════════════════════════════════════════════════════════
# BACKGROUND MEMORY HELPER (fixes asyncio.create_task in sync code)
# ═══════════════════════════════════════════════════════════════════

def _fire_and_forget(coro):
    """
    Safely runs an async coroutine from synchronous code.
    Uses a background thread with its own event loop.
    Avoids the asyncio.create_task() crash when there's no running loop.
    """
    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(coro)
        except Exception as e:
            logger.warning(f"[Memory background task] {e}")
        finally:
            loop.close()
    threading.Thread(target=_run, daemon=True).start()


# ═══════════════════════════════════════════════════════════════════
# STATE
# ═══════════════════════════════════════════════════════════════════

class StudyState(TypedDict):
    session_id:          str
    user_id:             str
    question:            str
    branch:              str
    student_answer:      str
    correct_answer:      str
    hint_level:          int
    action:              str
    difficulty:          str
    concept_explanation: str
    socratic_question:   str
    hint_text:           str
    mistake_feedback:    str
    practice_problem:    str
    session_summary:     str
    solve_output:        str
    is_correct:          bool
    success:             bool
    error:               Optional[str]
    next_phase:          str
    hints_remaining:     int
    memory_context:      str


# ═══════════════════════════════════════════════════════════════════
# NODES
# ═══════════════════════════════════════════════════════════════════

def init_node(state: StudyState) -> dict:
    session_id = state.get("session_id", "")
    question   = state["question"]
    branch     = state["branch"]

    if not session_id or not get_session(session_id):
        session_id = create_session(question, branch)

    difficulty = state.get("difficulty", "")
    if not difficulty:
        try:
            difficulty = study_llm.classify_difficulty(question, branch)
        except Exception:
            difficulty = "medium"

    return {
        "session_id": session_id,
        "difficulty": difficulty,
        "success":    True,
        "error":      None,
    }


def explain_node(state: StudyState) -> dict:
    sid        = state["session_id"]
    question   = state["question"]
    branch     = state["branch"]
    difficulty = state.get("difficulty", "medium")
    memory_ctx = state.get("memory_context", "")

    explanation = study_llm.explain_concept(
        question, branch, difficulty, memory_ctx=memory_ctx
    )
    update_session(sid, {"concept_explanation": explanation})
    set_phase(sid, "socratic")

    return {"concept_explanation": explanation, "next_phase": "socratic"}


def socratic_node(state: StudyState) -> dict:
    sid      = state["session_id"]
    question = state["question"]
    branch   = state["branch"]
    attempt  = state.get("student_answer", "")

    socratic_q = study_llm.generate_socratic_question(question, branch, attempt)

    session = get_session(sid)
    if session:
        existing = session.get("socratic_questions", [])
        update_session(sid, {"socratic_questions": existing + [socratic_q]})
    set_phase(sid, "check")

    return {"socratic_question": socratic_q, "next_phase": "check"}


def hint_node(state: StudyState) -> dict:
    sid        = state["session_id"]
    question   = state["question"]
    branch     = state["branch"]
    difficulty = state.get("difficulty", "medium")
    memory_ctx = state.get("memory_context", "")

    session    = get_session(sid)
    hints_used = session["hints_used"] if session else 0

    if hints_used >= 3:
        return {
            "hint_text":       "💪 استخدمت كل الهنتات! جرب حل المسألة أو اضغط **Solve** لو محتاج الحل الكامل.",
            "hints_remaining": 0,
            "next_phase":      "check",
        }

    hint_number = hints_used + 1
    hint_text   = study_llm.generate_hint(
        question, branch, hint_number, difficulty, memory_ctx=memory_ctx
    )
    use_hint(sid)

    remaining = 3 - hint_number
    return {
        "hint_text":       hint_text,
        "hints_remaining": remaining,
        "next_phase":      "check",
    }


def solve_node(state: StudyState) -> dict:
    sid        = state["session_id"]
    question   = state["question"]
    branch     = state["branch"]
    difficulty = state.get("difficulty", "medium")

    solution = study_llm.solve_direct(question, branch, difficulty)

    if sid:
        set_phase(sid, "practice")

    return {"solve_output": solution, "next_phase": "practice"}


def check_node(state: StudyState) -> dict:
    sid            = state["session_id"]
    user_id        = state.get("user_id", "")
    question       = state["question"]
    branch         = state.get("branch", "algebra")
    student_answer = state.get("student_answer", "")
    correct_answer = state.get("correct_answer", "")

    # Evaluate correctness
    try:
        is_correct = study_llm.evaluate_answer(correct_answer, student_answer)
    except Exception:
        s = student_answer.strip().lower().replace(" ", "")
        c = correct_answer.strip().lower().replace(" ", "")
        is_correct = s == c

    if is_correct:
        feedback   = "✅ صح تماماً! 🎉 أحسنت."
        next_phase = "practice"
    else:
        # analyze_mistake now returns a plain string
        feedback   = study_llm.analyze_mistake(question, correct_answer, student_answer)
        next_phase = "socratic"

    add_attempt(sid, student_answer, feedback, is_correct)
    set_phase(sid, next_phase)

    # Memory: fire and forget (background thread, safe)
    if user_id:
        _fire_and_forget(_memory.learn(user_id, [
            {"role": "user",      "content": f"[Check] Problem: {question} | Branch: {branch} | Student: {student_answer} | Correct: {correct_answer}"},
            {"role": "assistant", "content": f"Result: {'correct' if is_correct else 'incorrect'}. Feedback: {feedback}"},
        ]))

    return {
        "is_correct":       is_correct,
        "mistake_feedback": feedback,
        "next_phase":       next_phase,
    }


def practice_node(state: StudyState) -> dict:
    sid      = state["session_id"]
    user_id  = state.get("user_id", "")
    question = state["question"]
    branch   = state["branch"]
    diff     = state.get("difficulty", "medium")

    practice = study_llm.generate_practice(branch, question, difficulty="similar")
    update_session(sid, {
        "practice_problems": [{"question": practice, "difficulty": "similar", "branch": branch}]
    })
    set_phase(sid, "summary")

    if user_id:
        _fire_and_forget(_memory.learn(user_id, [
            {"role": "user",      "content": f"[Practice] Original: {question} | Branch: {branch}"},
            {"role": "assistant", "content": f"Generated practice (difficulty: {diff}): {practice}"},
        ]))

    return {"practice_problem": practice, "next_phase": "summary"}


def summary_node(state: StudyState) -> dict:
    sid     = state["session_id"]
    session = get_session(sid)
    history = session.get("attempt_history", []) if session else []
    stats   = None
    if session:
        stats = {
            "problems_solved": session["problems_solved"],
            "hints_used":      session["hints_used"],
            "total_attempts":  len(session["attempt_history"]),
        }

    summary = study_llm.summarize_session(history, stats)
    set_phase(sid, "summary")

    return {"session_summary": summary, "next_phase": "summary", "success": True}


# ═══════════════════════════════════════════════════════════════════
# ROUTING
# ═══════════════════════════════════════════════════════════════════

def route_after_action(state: StudyState) -> str:
    action     = state.get("action", "start")
    difficulty = state.get("difficulty", "medium")

    if action == "start":
        # Easy problems: solve directly (fast path)
        if difficulty == "easy":
            return "solve"
        return "explain"

    return {
        "hint":    "hint",
        "solve":   "solve",
        "giveup":  "solve",   # give-up → full solution
        "check":   "check",
        "next":    "practice",
        "summary": "summary",
    }.get(action, "explain")


def route_after_check(state: StudyState) -> str:
    return "practice" if state.get("is_correct", False) else "socratic"


def route_after_explain(state: StudyState) -> str:
    """Hard → socratic after explain. Medium/Easy → end."""
    difficulty = state.get("difficulty", "medium")
    return "socratic" if difficulty == "hard" else "end"


# ═══════════════════════════════════════════════════════════════════
# GRAPH
# ═══════════════════════════════════════════════════════════════════

def build_study_graph() -> StateGraph:
    g = StateGraph(StudyState)

    g.add_node("init",     init_node)
    g.add_node("explain",  explain_node)
    g.add_node("socratic", socratic_node)
    g.add_node("hint",     hint_node)
    g.add_node("solve",    solve_node)
    g.add_node("check",    check_node)
    g.add_node("practice", practice_node)
    g.add_node("summary",  summary_node)

    g.set_entry_point("init")

    g.add_conditional_edges("init", route_after_action, {
        "explain":  "explain",
        "hint":     "hint",
        "solve":    "solve",
        "check":    "check",
        "practice": "practice",
        "summary":  "summary",
    })

    g.add_conditional_edges("explain", route_after_explain, {
        "socratic": "socratic",
        "end":      END,
    })
    g.add_edge("socratic", END)
    g.add_edge("hint",     END)
    g.add_edge("solve",    END)

    g.add_conditional_edges("check", route_after_check, {
        "practice": "practice",
        "socratic": "socratic",
    })

    g.add_edge("practice", END)
    g.add_edge("summary",  END)

    return g


# ═══════════════════════════════════════════════════════════════════
# STUDY AGENT
# ═══════════════════════════════════════════════════════════════════

class StudyAgent:
    def __init__(self):
        self.graph  = build_study_graph()
        self.app    = self.graph.compile()
        self.memory = _memory
        logger.info("[StudyAgent v6] Ready ✓")

    def _build_state(self, action, question, branch, session_id="",
                     student_answer="", correct_answer="", difficulty="",
                     user_id="", memory_context="") -> StudyState:
        return StudyState(
            session_id=session_id, user_id=user_id,
            question=question, branch=branch,
            action=action, student_answer=student_answer,
            correct_answer=correct_answer, hint_level=1,
            difficulty=difficulty, concept_explanation="",
            socratic_question="", hint_text="", mistake_feedback="",
            practice_problem="", session_summary="", solve_output="",
            is_correct=False, next_phase="", success=False,
            error=None, hints_remaining=3, memory_context=memory_context,
        )

    async def _get_memory_ctx(self, user_id: str, query: str) -> str:
        if not user_id:
            return ""
        try:
            return await self.memory.get_context(user_id, query)
        except Exception as e:
            logger.warning(f"[Memory] get_context failed: {e}")
            return ""

    def _run(self, state: StudyState) -> dict:
        try:
            result = self.app.invoke(state)
            return {**result, "success": result.get("success", True), "error": None}
        except Exception as e:
            logger.error(f"[StudyAgent] Graph error: {e}", exc_info=True)
            return {"success": False, "error": str(e), "session_id": state.get("session_id", "")}

    def _hints_remaining(self, session_id: str) -> int:
        session = get_session(session_id)
        return (3 - session["hints_used"]) if session else 3

    # ── FAST PATHS (no graph) ───────────────────────────────────────

    def classify_intent(self, text: str) -> str:
        return study_llm.classify_intent(text)

    def chat(self, message: str) -> dict:
        return {
            "success":          True,
            "intent":           "casual",
            "display_markdown": study_llm.chat_casual(message),
        }

    def explain(self, question: str, branch: str) -> dict:
        return {
            "success":          True,
            "intent":           "explain",
            "display_markdown": study_llm.explain_topic(question, branch),
        }

    def help_user(self, question: str, branch: str) -> dict:
        return {
            "success":          True,
            "intent":           "help",
            "display_markdown": study_llm.help_response(question, branch),
        }

    # ── GRAPH-BASED PATHS ──────────────────────────────────────────

    async def start(self, question: str, branch: str, user_id: str = "") -> dict:
        memory_ctx = await self._get_memory_ctx(user_id, question)
        state  = self._build_state("start", question, branch,
                                   user_id=user_id, memory_context=memory_ctx)
        result = self._run(state)
        result["hints_remaining"] = self._hints_remaining(result.get("session_id", ""))
        result["difficulty"]      = result.get("difficulty", "medium")
        return result

    async def hint(self, session_id: str, question: str, branch: str,
                   user_id: str = "") -> dict:
        memory_ctx = await self._get_memory_ctx(user_id, question)
        state  = self._build_state("hint", question, branch,
                                   session_id=session_id, user_id=user_id,
                                   memory_context=memory_ctx)
        result = self._run(state)
        result["hints_remaining"] = self._hints_remaining(session_id)
        return result

    async def solve(self, session_id: str, question: str, branch: str,
                    user_id: str = "") -> dict:
        state = self._build_state("solve", question, branch,
                                  session_id=session_id, user_id=user_id)
        return self._run(state)

    async def giveup(self, session_id: str, question: str, branch: str,
                     user_id: str = "") -> dict:
        """Explicit give-up: same as solve but tracked separately."""
        state = self._build_state("giveup", question, branch,
                                  session_id=session_id, user_id=user_id)
        return self._run(state)

    async def check(self, session_id: str, question: str, branch: str,
                    student_answer: str, correct_answer: str,
                    user_id: str = "") -> dict:
        memory_ctx = await self._get_memory_ctx(user_id, question)
        state  = self._build_state("check", question, branch,
                                   session_id=session_id,
                                   student_answer=student_answer,
                                   correct_answer=correct_answer,
                                   user_id=user_id, memory_context=memory_ctx)
        result = self._run(state)
        result["hints_remaining"] = self._hints_remaining(session_id)
        return result

    async def next(self, session_id: str, question: str, branch: str,
                   user_id: str = "") -> dict:
        return self._run(self._build_state("next", question, branch,
                                           session_id=session_id, user_id=user_id))

    async def next_harder(self, session_id: str, question: str, branch: str,
                          user_id: str = "") -> dict:
        practice = study_llm.generate_harder_practice(branch, question)
        session  = get_session(session_id)
        if session:
            update_session(session_id, {
                "practice_problems": [{"question": practice, "difficulty": "harder", "branch": branch}]
            })
        if user_id:
            _fire_and_forget(_memory.learn(user_id, [
                {"role": "user",      "content": f"[Harder] Original: {question} | Branch: {branch}"},
                {"role": "assistant", "content": f"Harder practice: {practice}"},
            ]))
        return {
            "success":          True,
            "practice_problem": practice,
            "next_phase":       "summary",
            "difficulty_bump":  True,
        }

    async def finish(self, session_id: str, question: str, branch: str,
                     user_id: str = "") -> dict:
        state  = self._build_state("summary", question, branch,
                                   session_id=session_id, user_id=user_id)
        result = self._run(state)
        session = get_session(session_id)
        if session:
            result["stats"] = {
                "problems_solved": session["problems_solved"],
                "hints_used":      session["hints_used"],
                "total_attempts":  len(session["attempt_history"]),
            }
            if user_id:
                _fire_and_forget(_memory.learn(user_id, [
                    {"role": "user",      "content": f"[Summary] Branch: {branch} | Question: {question}"},
                    {"role": "assistant", "content": f"Stats: {result['stats']}. Summary: {result.get('session_summary', '')}"},
                ]))
        return result


# ═══════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════

_instance: Optional[StudyAgent] = None
_lock = threading.Lock()

def get_study_agent() -> StudyAgent:
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = StudyAgent()
    return _instance