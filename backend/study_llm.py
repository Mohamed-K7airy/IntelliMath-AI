"""
Sphinx-SCA — Study LLM Engine (v6 — Fixed & Optimized)
=======================================================
Fixes:
    1. analyze_mistake: JSON parsed correctly, fallback handled
    2. Language detection: Arabic math problems handled properly
    3. Hints: clean output, no language mixing unless user mixes
    4. All prompts: consistent, non-conflicting instructions
    5. Token limits: calibrated per difficulty
    6. Removed memory "NEVER say" conflict — memory is used silently
"""

import os
import sys
import re
import json

if __package__ is None:
    # ✅ FIX (W-12): study_llm.py is at backend/ — only 2 levels up to project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from typing import List

try:
    from backend.llm_manager import client as groq_client
except ImportError:
    from llm_manager import client as groq_client


# ═══════════════════════════════════════════════════════════════════
# LANGUAGE DETECTION
# ═══════════════════════════════════════════════════════════════════

def detect_language(text: str) -> str:
    """
    Returns 'ar' if Arabic script is dominant, 'en' otherwise.
    Math symbols are language-neutral and don't affect the result.
    """
    arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    latin_chars  = sum(1 for c in text if c.isalpha() and c.isascii())
    if arabic_chars > latin_chars:
        return "ar"
    return "en"


def lang_instruction(lang: str) -> str:
    if lang == "ar":
        return "Respond ENTIRELY in Arabic. Math formulas use LaTeX. Do NOT mix in English words."
    return "Respond in English. Math formulas use LaTeX."


# ═══════════════════════════════════════════════════════════════════
# PERSONAS
# ═══════════════════════════════════════════════════════════════════

def tutor_persona(lang: str) -> str:
    base = """You are Sphinx-SCA, an AI Math Tutor. Your only goal is to guide the student to solve problems themselves.

CORE RULES:
- NEVER give the final answer unless the student explicitly gave up (solve mode)
- NEVER solve more than one step at a time
- Always end your response with ONE guiding question
- Be warm, concise, encouraging
- Use emojis naturally: 💡 💭 🎯 🎉 👀

STUDENT CONTEXT: If student weakness data is provided, adapt your guidance subtly without mentioning it."""

    return f"{base}\n\nLANGUAGE: {lang_instruction(lang)}"


def solver_persona(lang: str) -> str:
    base = """You are Sphinx-SCA, a precise math solver.
- Solve completely and correctly
- Show only necessary steps
- State the final answer clearly on the last line, prefixed with "Answer:" or "الإجابة:"
- Use LaTeX for all math expressions
- No filler, no repetition of the question"""

    return f"{base}\n\nLANGUAGE: {lang_instruction(lang)}"


def chat_persona(lang: str) -> str:
    base = """You are Sphinx-SCA, a friendly AI study assistant built by students at Sphinx University, Egypt.
- Respond naturally and warmly
- Keep responses SHORT (2-4 sentences)
- You can help with math, explain concepts, or just chat"""

    return f"{base}\n\nLANGUAGE: {lang_instruction(lang)}"


# ═══════════════════════════════════════════════════════════════════
# TOKEN LIMITS
# ═══════════════════════════════════════════════════════════════════

TOKENS = {
    "easy":   100,
    "medium": 200,
    "hard":   350,
    "default": 200,
}


# ═══════════════════════════════════════════════════════════════════
# STUDY LLM CLASS
# ═══════════════════════════════════════════════════════════════════

class StudyLLM:
    def __init__(self):
        self.client = groq_client
        self.model  = "openai/gpt-oss-120b"

    def _call(self, system: str, user: str, *,
              json_mode: bool = False,
              temperature: float = 0.4,
              max_tokens: int = 300) -> str:
        try:
            kwargs = {
                "model":       self.model,
                "temperature": temperature,
                "max_tokens":  max_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            resp = self.client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content.strip()
        except Exception as e:
            if json_mode:
                return json.dumps({"error": str(e)})
            return f"Error: {e}"

    # ── INTENT CLASSIFICATION ───────────────────────────────────────

    def classify_intent(self, text: str) -> str:
        """
        Returns: casual | study | explain | help | giveup
        Regex-first for speed, LLM fallback for ambiguous cases.
        """
        t = text.strip().lower()

        # Math operators / expressions → study
        if re.search(r'[\d]+\s*[+\-*/^=×÷]\s*[\d]', t): return "study"
        if re.search(r'[a-zA-Z]\s*[+\-*/^=]',         t): return "study"
        if re.search(r'\\frac|\\sqrt|\\int|\\sum',     t): return "study"
        if re.search(r'\d+x|\d+y|\d+z',               t): return "study"

        # Give-up patterns (check before help)
        if re.search(r'(i give up|show.?solution|show.?answer|استسلم|وريني الحل|ورني الحل|حل لي|حلها)', t):
            return "giveup"

        # Help / confused
        if re.search(r'(مش فاهم|مش عارف|لا أفهم|لا افهم|ساعدني|help me|confused|stuck|i.?m lost|don.?t understand)', t):
            return "help"

        # Explain / theory
        if re.search(r'(explain|اشرح|وضح|فهمني|ايه هو|what is|what are|يعني ايه|definition|concept)', t):
            return "explain"

        # Casual greetings
        if re.search(r'^(hi|hello|hey|مرحبا|اهلا|السلام|ازيك|صباح|مساء|شكرا|thanks|bye|كيفك|عامل ايه|how are you|who are you|what can you do)[\s!?.]*$', t):
            return "casual"

        # Math words (Arabic + English)
        if re.search(r'(solve|حل|factor|simplify|differentiate|integrate|calculate|find|evaluate|compute|limit|derive|prove|احسب|بسّط|اشتق|تكامل|عامل|حدد)', t):
            return "study"

        # Short text with no math → casual
        if len(t) < 20 and not any(c in t for c in '+-*/=^()[]{}'):
            return "casual"

        return "study"

    # ── DIFFICULTY CLASSIFICATION ───────────────────────────────────

    def classify_difficulty(self, question: str, branch: str) -> str:
        result = self._call(
            """Classify math problem difficulty. Output ONLY one word: easy, medium, or hard.

easy:   basic arithmetic, simple one-step equations
medium: quadratics, basic calculus, systems of equations
hard:   complex integrals, differential equations, multi-concept proofs""",
            f"Problem: {question}\nBranch: {branch}",
            temperature=0.0, max_tokens=5,
        ).lower()
        return result if result in ("easy", "medium", "hard") else "medium"

    # ── CASUAL CHAT ─────────────────────────────────────────────────

    def chat_casual(self, message: str) -> str:
        lang = detect_language(message)
        return self._call(chat_persona(lang), message, temperature=0.7, max_tokens=200)

    # ── EXPLAIN (concept/theory questions) ─────────────────────────

    def explain_topic(self, question: str, branch: str) -> str:
        lang = detect_language(question)
        system = f"""{tutor_persona(lang)}

The student wants a CONCEPT EXPLANATION (not problem solving).

Steps:
1. Explain the concept clearly in 3-4 sentences
2. Give one concrete example if helpful
3. End with a CHECK QUESTION to test understanding

Keep it concise. No unnecessary preamble."""

        return self._call(system, f"Topic: {question}\nBranch: {branch}",
                          temperature=0.3, max_tokens=400)

    # ── STUDY START (Socratic intro) ────────────────────────────────

    def explain_concept(self, question: str, branch: str, difficulty: str = "medium",
                        memory_ctx: str = "") -> str:
        lang = detect_language(question)

        depth_map = {
            "easy":   "One sentence. Identify the problem type. Ask what the first step is.",
            "medium": "1-2 sentences. Name the concept. Ask what approach the student would try.",
            "hard":   "2-3 sentences. Name the concept and what makes it complex. Ask a strategic thinking question.",
        }
        depth = depth_map.get(difficulty, depth_map["medium"])

        ctx_block = f"\n\nStudent background: {memory_ctx}" if memory_ctx else ""

        system = f"""{tutor_persona(lang)}

Introduce this problem's concept and get the student THINKING.
{depth}
{ctx_block}

STRICT RULES:
- Do NOT reveal any solution steps
- Do NOT give formulas yet
- End with exactly ONE guiding question
- Be conversational, not like a textbook"""

        return self._call(system,
                          f"Problem: {question}\nBranch: {branch}",
                          temperature=0.4,
                          max_tokens=TOKENS.get(difficulty, 200))

    # ── HINT SYSTEM ─────────────────────────────────────────────────

    def generate_hint(self, question: str, branch: str, hint_number: int,
                      difficulty: str = "medium", memory_ctx: str = "") -> str:
        lang = detect_language(question)

        level_map = {
            1: "Point to the TECHNIQUE or FORMULA CATEGORY needed. No calculations. Make them identify the method.",
            2: "Name the EXACT formula or operation. Show the structure without numbers. Still no calculation.",
            3: "Show the FIRST STEP of calculation. Stop before the final answer. Almost a spoiler, but not quite.",
        }
        level = level_map.get(hint_number, level_map[1])

        ctx_block = f"\nStudent weakness context (use subtly): {memory_ctx}" if memory_ctx else ""

        system = f"""{tutor_persona(lang)}

You are giving Hint #{hint_number} of 3.
Level: {level}
{ctx_block}

Rules:
- MAXIMUM 2 sentences
- End with a short encouraging phrase or micro-question
- Do NOT solve the problem"""

        return self._call(system,
                          f"Problem: {question}\nBranch: {branch}\nHint #{hint_number}:",
                          temperature=0.35,
                          max_tokens=120)

    # ── SOLVE (give-up mode only) ───────────────────────────────────

    def solve_direct(self, question: str, branch: str, difficulty: str = "medium") -> str:
        lang = detect_language(question)

        depth_map = {
            "easy":   "Direct answer in 1-2 lines. Example: 2x+5=15 → x=5",
            "medium": "Key steps only (max 4 lines). Clear final answer.",
            "hard":   "Structured steps (max 6). Each step labeled. Clear final answer.",
        }
        depth = depth_map.get(difficulty, depth_map["medium"])

        system = f"""{solver_persona(lang)}

Depth: {depth}

Format:
- Jump straight into the math — NO intro sentence
- Use LaTeX for all expressions
- Last line MUST be: "**Answer:** ..." or "**الإجابة:** ..."
- Do NOT repeat the question"""

        return self._call(system, question,
                          temperature=0.1,
                          max_tokens=TOKENS.get(difficulty, 200))

    # ── SOCRATIC QUESTION ───────────────────────────────────────────

    def generate_socratic_question(self, question: str, branch: str,
                                   attempt: str = "") -> str:
        lang = detect_language(question)
        ctx = f"Student's attempt: {attempt}" if attempt else "Student hasn't attempted yet."

        system = f"""{tutor_persona(lang)}

Ask ONE specific guiding question (1-2 sentences).
- If the student attempted: acknowledge it first, then redirect
- If no attempt: ask about the approach or first step
- Be specific to THIS problem, not generic
- Never answer your own question"""

        return self._call(system,
                          f"Problem: {question}\nBranch: {branch}\n{ctx}",
                          temperature=0.4, max_tokens=120)

    # ── MISTAKE ANALYSIS ────────────────────────────────────────────

    def analyze_mistake(self, question: str, correct_answer: str,
                        student_answer: str, attempt_count: int = 1) -> str:
        """
        Returns a plain feedback STRING (not JSON).
        Internally uses JSON for structured analysis, then formats output.
        """
        lang = detect_language(question)

        raw = self._call(
            f"""You are a math tutor analyzing a student mistake.
Return ONLY valid JSON, no extra text:
{{
  "feedback": "Supportive 1-2 sentence feedback. NEVER say wrong/incorrect. Say 'قريب جداً 👀' or 'Almost there! 👀'. End with a guiding question.",
  "error_type": "sign_error | calculation_error | wrong_formula | missing_step | conceptual_error",
  "hint": "One sentence pointing to what to recheck"
}}

Language for feedback: {"Arabic" if lang == "ar" else "English"}
NEVER use the words: wrong, incorrect, خطأ (as a judgment)""",
            f"Problem: {question}\nCorrect: {correct_answer}\nStudent: {student_answer}\nAttempt #{attempt_count}",
            json_mode=True, max_tokens=250,
        )

        try:
            data = json.loads(raw)
            feedback = data.get("feedback", "")
            hint     = data.get("hint", "")
            if hint:
                feedback = f"{feedback}\n💡 {hint}"
            return feedback or self._fallback_feedback(lang)
        except (json.JSONDecodeError, KeyError):
            return self._fallback_feedback(lang)

    def _fallback_feedback(self, lang: str) -> str:
        if lang == "ar":
            return "قريب جداً 👀 راجع خطواتك مرة تانية — فين بالظبط الخطوة اللي مش متأكد منها؟"
        return "Almost there! 👀 Review your steps — which part are you least confident about?"

    # ── ANSWER EVALUATION ───────────────────────────────────────────

    def evaluate_answer(self, correct_answer: str, student_answer: str) -> bool:
        result = self._call(
            """Determine if these two math answers are equivalent.
Consider: equivalent fractions, simplified forms, different variable names.
Output ONLY: TRUE or FALSE""",
            f"Correct: {correct_answer}\nStudent: {student_answer}",
            temperature=0.0, max_tokens=5,
        )
        return "TRUE" in result.upper()

    # ── PRACTICE GENERATION ─────────────────────────────────────────

    def generate_practice(self, branch: str, original_question: str = "",
                          difficulty: str = "similar") -> str:
        lang = detect_language(original_question)

        system = f"""{tutor_persona(lang)}

Generate ONE new practice problem. Same concept, different numbers.

Rules:
- Problem statement ONLY — absolutely NO solution
- Use LaTeX for all math
- Keep it 1-3 lines
- Add ONE motivating line at the end

Do NOT include any answer or hint."""

        return self._call(system,
                          f"Original: {original_question}\nBranch: {branch}\nDifficulty: {difficulty}",
                          temperature=0.6, max_tokens=150)

    def generate_harder_practice(self, branch: str, original_question: str = "") -> str:
        lang = detect_language(original_question)

        system = f"""{tutor_persona(lang)}

Generate ONE harder practice problem. More steps, harder numbers, or an extra twist.

Rules:
- Problem statement ONLY — NO solution, NO answer
- Use LaTeX for all math
- 1-3 lines
- Add a short challenge line at the end (e.g., "🔥 Level up!")

Do NOT include any answer or hint."""

        return self._call(system,
                          f"Original: {original_question}\nBranch: {branch}",
                          temperature=0.6, max_tokens=150)

    # ── HELP MODE ───────────────────────────────────────────────────

    def help_response(self, question: str, branch: str) -> str:
        lang = detect_language(question)

        system = f"""{tutor_persona(lang)}

The student is CONFUSED. Be extra gentle.

Steps:
1. Acknowledge that it's okay to be confused (1 sentence)
2. Simplify the problem in plain language (1-2 sentences)
3. Give a very gentle nudge about where to start (1 sentence)
4. Encourage warmly

NO solution. NO formulas yet. Just clarity and calm."""

        return self._call(system,
                          f"Problem: {question}\nBranch: {branch}",
                          temperature=0.5, max_tokens=220)

    # ── SESSION SUMMARY ─────────────────────────────────────────────

    def summarize_session(self, session_history: list, stats: dict = None) -> str:
        stats_block = ""
        if stats:
            stats_block = (
                f"\nStats: {stats.get('problems_solved', 0)} solved, "
                f"{stats.get('total_attempts', 0)} attempts, "
                f"{stats.get('hints_used', 0)} hints used"
            )

        lang = "ar" if any(
            '\u0600' <= c <= '\u06FF'
            for item in session_history
            for c in str(item)
        ) else "en"

        system = f"""{tutor_persona(lang)}

Write a SESSION SUMMARY (3-4 sentences max):
1. 🎉 Celebrate what the student did well
2. 🎯 One thing to focus on next
3. 💪 Brief motivating closing line

Keep it short, warm, upbeat."""

        return self._call(system,
                          f"History: {session_history}{stats_block}",
                          temperature=0.5, max_tokens=200)