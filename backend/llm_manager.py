"""
Sphinx-SCA — LLM Manager (Groq + Llama 3.3)
=============================================
Roles:
  0. Classifier       → classify problem branch & type  ← BERT replacement
  1. Problem Parser   → raw text to structured JSON
  2. Step Generator   → educational step-by-step solution
  3. Hint Generator   → progressive hints without spoiling
  4. Word Problem     → extract equation from natural language
  5. OCR Validator    → fix LaTeX from image and convert to SymPy
  6. Chat             → natural conversation + math solving ← NEW

Requirements:
    pip install groq
"""

import sys
import json
import re
from groq import Groq
import os


# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "moonshotai/kimi-k2-instruct"

# We initialize the client only if the API KEY is present.
# This prevents a crash during module import on platforms like Railway
# if the environment variable is not yet set.
client = None
if GROQ_API_KEY:
    try:
        client = Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        print(f"⚠️ Failed to initialize Groq client: {e}")
else:
    print("⚠️ GROQ_API_KEY not found in environment variables")

# ── System prompt — شخصية المساعد ──────────────
SYSTEM_PROMPT = """You are Sphinx-SCA, a friendly and smart AI math assistant.
You were created by students at Sphinx University in Egypt.

Your personality:
- Friendly, warm, and encouraging
- Clear and educational — you explain things simply
- You can chat normally AND solve math problems
- When someone greets you, greet them back naturally
- When someone asks a math question, solve it step by step

When solving math problems:
1. Acknowledge the problem naturally ("Great question! Let me solve this...")
2. Show the solution step by step clearly
3. State the final answer clearly at the end
4. Encourage the user

When chatting normally:
- Be natural and friendly
- Keep responses concise but warm
- If someone seems stuck, offer to help with hints

Always respond in the same language the user uses (Arabic or English).
If the user writes in Arabic, respond in Arabic.
If the user writes in English, respond in English.
"""


# ─────────────────────────────────────────────
#  BASE HELPERS
# ─────────────────────────────────────────────

def _call_llm(prompt: str, temperature: float = 0.0) -> str:
    """Send prompt to Groq and return response text."""
    if client is None:
        raise RuntimeError("Groq client not initialized. Please check your GROQ_API_KEY.")
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=1024,
        )
        text = response.choices[0].message.content
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        return text.strip()
    except Exception as e:
        raise RuntimeError(f"Groq API error: {e}")


def _call_chat(messages: list, temperature: float = 0.7) -> str:
    """Send full conversation history to Groq with system prompt."""
    if client is None:
        raise RuntimeError("Groq client not initialized. Please check your GROQ_API_KEY.")
    try:
        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=full_messages,
            temperature=temperature,
            max_tokens=2048,
        )
        text = response.choices[0].message.content
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        return text.strip()
    except Exception as e:
        raise RuntimeError(f"Groq API error: {e}")

def stream_chat(messages: list, temperature: float = 0.7):
    """Stream conversation history from Groq."""
    if client is None:
        raise RuntimeError("Groq client not initialized.")
    
    try:
        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
        stream = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=full_messages,
            temperature=temperature,
            max_tokens=2048,
            stream=True,
        )
        
        in_thinking = False
        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                if "<think>" in content:
                    in_thinking = True
                    continue
                if "</think>" in content:
                    in_thinking = False
                    continue
                
                if not in_thinking:
                    yield content
                    
    except Exception as e:
        yield f"Error: {str(e)}"


def _extract_json(text: str) -> dict:
    """Safely extract JSON dict from LLM response."""
    text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not parse JSON:\n{text}")


def _extract_json_array(text: str) -> list:
    """Safely extract JSON array from LLM response."""
    text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`")
    try:
        result = json.loads(text)
        return result if isinstance(result, list) else [result]
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return []


# ─────────────────────────────────────────────
#  ROLE 0 — CLASSIFIER
# ─────────────────────────────────────────────

def classify_problem(raw_text: str) -> dict:
    """
    Role 0 — Classify input as math problem or chat.
    Returns is_math=True/False so app.py routes correctly.
    """
    prompt = f"""
You are a math problem classifier.
Classify this input and return ONLY valid JSON, no explanation, no markdown.

Input: "{raw_text}"

Return this exact structure:
{{
  "branch": "algebra | calculus | geometry | statistics | linear_algebra | word_problem | chat",
  "problem_type": "solve | simplify | factor | differentiate | integrate | limit | area | perimeter | volume | mean | median | std | determinant | inverse | eigenvalues | multiply | calculate | conversation",
  "confidence": 0.0 to 1.0,
  "is_math": true or false
}}

Rules:
- chat    : greetings, small talk, questions about the bot, anything NOT math
- is_math : false for chat, true for all math problems

Examples:
- "hi"                            → {{"branch": "chat",          "problem_type": "conversation", "confidence": 1.0,  "is_math": false}}
- "how are you?"                  → {{"branch": "chat",          "problem_type": "conversation", "confidence": 1.0,  "is_math": false}}
- "what can you do?"              → {{"branch": "chat",          "problem_type": "conversation", "confidence": 1.0,  "is_math": false}}
- "مرحبا"                        → {{"branch": "chat",          "problem_type": "conversation", "confidence": 1.0,  "is_math": false}}
- "solve 2x + 5 = 11"            → {{"branch": "algebra",        "problem_type": "solve",        "confidence": 0.98, "is_math": true}}
- "differentiate x^2 + 3x"       → {{"branch": "calculus",       "problem_type": "differentiate","confidence": 0.97, "is_math": true}}
- "area of circle with radius 5"  → {{"branch": "geometry",       "problem_type": "area",         "confidence": 0.96, "is_math": true}}
- "mean of 4, 8, 15, 16"          → {{"branch": "statistics",     "problem_type": "mean",         "confidence": 0.95, "is_math": true}}
- "determinant of [[1,2],[3,4]]"  → {{"branch": "linear_algebra", "problem_type": "determinant",  "confidence": 0.97, "is_math": true}}
- "Ahmed has 5 apples, gave 2..." → {{"branch": "word_problem",   "problem_type": "calculate",    "confidence": 0.90, "is_math": true}}
"""
    response = _call_llm(prompt, temperature=0.0)
    result   = _extract_json(response)

    valid_branches = {"algebra", "calculus", "geometry", "statistics", "linear_algebra", "word_problem", "chat"}
    if result.get("branch") not in valid_branches:
        result["branch"]  = "algebra"
        result["is_math"] = True

    return result


# ─────────────────────────────────────────────
#  ROLE 1 — PROBLEM PARSER
# ─────────────────────────────────────────────

PARSER_PROMPTS = {

    "algebra": """
You are a math expression parser. Convert the problem to JSON.
Return ONLY valid JSON, no explanation, no markdown.

Problem: "{problem}"

Return this exact structure:
{{
  "expression": "sympy-compatible expression (move everything to left side)",
  "variables": ["list of variables"],
  "operation": "solve | simplify | factor | expand"
}}

Examples:
- "solve 2x + 5 = 11" → {{"expression": "2*x+5-11", "variables": ["x"], "operation": "solve"}}
- "factor x^2 - 4"    → {{"expression": "x**2-4",   "variables": ["x"], "operation": "factor"}}
""",

    "calculus": """
You are a calculus expression parser. Convert the problem to JSON.
Return ONLY valid JSON, no explanation, no markdown.

Problem: "{problem}"

Return this exact structure:
{{
  "expression": "sympy-compatible expression",
  "variable": "main variable",
  "operation": "differentiate | integrate | limit",
  "limit_point": null
}}

Examples:
- "differentiate x^3 + 2x" → {{"expression": "x**3+2*x", "variable": "x", "operation": "differentiate", "limit_point": null}}
- "integrate sin(x)"        → {{"expression": "sin(x)",   "variable": "x", "operation": "integrate",     "limit_point": null}}
""",

    "matrix": """
You are a matrix parser. Convert the problem to JSON.
Return ONLY valid JSON, no explanation, no markdown.

Problem: "{problem}"

Return this exact structure:
{{
  "matrix_a": [[row1], [row2]],
  "matrix_b": [[row1], [row2]] or null,
  "operation": "determinant | inverse | multiply | eigenvalues | transpose"
}}

Example:
- "determinant of [[1,2],[3,4]]" → {{"matrix_a": [[1,2],[3,4]], "matrix_b": null, "operation": "determinant"}}
""",

    "statistics": """
You are a statistics parser. Convert the problem to JSON.
Return ONLY valid JSON, no explanation, no markdown.

Problem: "{problem}"

Return this exact structure:
{{
  "data": [list of numbers],
  "operation": "mean | median | mode | std | variance | all"
}}

Example:
- "mean of 4, 8, 15, 16, 23" → {{"data": [4,8,15,16,23], "operation": "mean"}}
""",

    "geometry": """
You are a geometry parser. Convert the problem to JSON.
Return ONLY valid JSON, no explanation, no markdown.

Problem: "{problem}"

Return this exact structure:
{{
  "shape": "circle | triangle | rectangle | square | sphere | cylinder | cone",
  "known": {{"param": value}},
  "find": "area | perimeter | volume | surface_area"
}}

Example:
- "area of circle with radius 5" → {{"shape": "circle", "known": {{"radius": 5}}, "find": "area"}}
""",

    "linear_equations": """
You are a linear equations parser. Convert the problem to JSON.
Return ONLY valid JSON, no explanation, no markdown.

Problem: "{problem}"

Return this exact structure:
{{
  "equations": ["sympy eq1 (left - right)", "sympy eq2", ...],
  "variables": ["x", "y", ...]
}}

Example:
- "x + y = 5 and x - y = 1" → {{"equations": ["x+y-5", "x-y-1"], "variables": ["x","y"]}}
""",

    "word_problem": """
You are a math word problem parser. Extract the core equation.
Return ONLY valid JSON, no explanation, no markdown.

Problem: "{problem}"

Return this exact structure:
{{
  "expression": "the core math expression",
  "variables": ["variables if any"],
  "operation": "solve | calculate"
}}
"""
}


def parse_problem(raw_text: str, problem_type: str) -> dict:
    """Role 1 — Convert raw user text to structured JSON for the Solver."""
    template = PARSER_PROMPTS.get(problem_type, PARSER_PROMPTS["algebra"])
    prompt   = template.format(problem=raw_text)
    response = _call_llm(prompt, temperature=0.0)
    return _extract_json(response)


# ─────────────────────────────────────────────
#  ROLE 2 — STEP GENERATOR
# ─────────────────────────────────────────────

def generate_steps(problem: str, solution: str, problem_type: str) -> list:
    """Role 2 — Generate educational step-by-step solution."""
    prompt = f"""
You are a math teacher. Generate a clear step-by-step solution in English.
Return ONLY a valid JSON array, no explanation, no markdown.

Problem: "{problem}"
Type: {problem_type}
Final answer: {solution}

Return this exact structure:
[
  {{
    "step": 1,
    "title": "Short step title",
    "action": "The math shown clearly (e.g. 2x = 11 - 5)",
    "explanation": "Why we do this in simple English"
  }}
]

Rules:
- Max 6 steps
- Last step must show the final answer
- Keep explanations simple and educational
"""
    response = _call_llm(prompt, temperature=0.1)
    steps    = _extract_json_array(response)
    if not steps:
        return [{"step": 1, "title": "Solution", "action": str(solution), "explanation": "Final answer"}]
    return steps


# ─────────────────────────────────────────────
#  ROLE 3 — HINT GENERATOR
# ─────────────────────────────────────────────

def generate_hints(problem: str, problem_type: str, num_hints: int = 3) -> list:
    """Role 3 — Generate progressive hints without revealing the answer."""
    prompt = f"""
You are a math tutor. Generate {num_hints} progressive hints.
Return ONLY a valid JSON array of strings. No explanation, no markdown.

Problem: "{problem}"
Type: {problem_type}

Hint levels:
- Hint 1: Very vague — point to the concept only
- Hint 2: More specific — suggest the first step
- Hint 3: Almost the answer — show the key operation

Return format: ["hint1", "hint2", "hint3"]
"""
    response = _call_llm(prompt, temperature=0.2)
    hints    = _extract_json_array(response)
    if not hints:
        return [
            "Think about what type of problem this is.",
            "Identify the unknown variable and what you need to find.",
            "Apply the appropriate formula step by step."
        ]
    return hints


# ─────────────────────────────────────────────
#  ROLE 4 — WORD PROBLEM SOLVER
# ─────────────────────────────────────────────

def solve_word_problem(problem_text: str) -> dict:
    """Role 4 — Understand and solve a natural language math problem."""
    prompt = f"""
You are a math expert. Solve this word problem.
Return ONLY valid JSON, no explanation outside JSON, no markdown.

Problem: "{problem_text}"

Return this exact structure:
{{
  "extracted_equation": "the math equation from the text",
  "variables_defined": {{"var": "what it represents"}},
  "solution": "final numerical answer",
  "steps": [
    {{"step": 1, "description": "what we do", "math": "the operation"}}
  ],
  "answer_sentence": "Full sentence stating the answer clearly."
}}
"""
    response = _call_llm(prompt, temperature=0.1)
    return _extract_json(response)


# ─────────────────────────────────────────────
#  ROLE 5 — OCR VALIDATOR
# ─────────────────────────────────────────────

def validate_ocr(latex_text: str) -> str:
    """Role 5 — Fix OCR errors in LaTeX and convert to SymPy expression."""
    prompt = f"""
You are a LaTeX to SymPy converter.
Fix any OCR errors and convert to SymPy-compatible format.
Return ONLY the clean expression as plain text. No JSON, no explanation, no markdown.

LaTeX input: "{latex_text}"

Conversion rules:
- x^{{2}}          → x**2
- \\frac{{a}}{{b}} → a/b
- \\sqrt{{x}}      → sqrt(x)
- \\sin, \\cos     → sin, cos
- × or \\times     → *
- Move = to make expression = 0

Return ONLY the expression:
"""
    response = _call_llm(prompt, temperature=0.0)
    return response.replace("`", "").replace('"', "").strip()


# ─────────────────────────────────────────────
#  ROLE 6 — CHAT (NEW)
# ─────────────────────────────────────────────

def chat(message: str, history: list = None) -> str:
    """
    Role 6 — Natural conversation.

    Args:
        message : current user message
        history : [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]

    Returns:
        AI response string
    """
    if history is None:
        history = []
    messages = history + [{"role": "user", "content": message}]
    return _call_chat(messages, temperature=0.7)


def chat_with_math(message: str, math_result: dict, history: list = None) -> str:
    """
    Role 6b — Wrap a math solution in a natural friendly response.

    Args:
        message     : original user question
        math_result : result dict from SymPy solver
        history     : conversation history

    Returns:
        Natural language response with math solution embedded
    """
    if history is None:
        history = []

    answer = math_result.get("final_answer") or math_result.get("answer") or "unknown"
    steps  = math_result.get("llm_steps", [])

    steps_text = ""
    if steps:
        steps_text = "\n".join(
            f"Step {s.get('step', i+1)}: {s.get('title','')}"
            f" → {s.get('action','')}"
            f" ({s.get('explanation','')})"
            for i, s in enumerate(steps)
        )

    context = f"""The user asked: "{message}"
The math solver found the answer: {answer}
{"Steps found:\n" + steps_text if steps_text else ""}

Now respond as Sphinx-SCA naturally. Present the answer warmly with the steps. Encourage the user."""

    messages = history + [{"role": "user", "content": context}]
    return _call_chat(messages, temperature=0.5)


# ─────────────────────────────────────────────
#  UNIFIED INTERFACE
# ─────────────────────────────────────────────

class LLMManager:
    """
    Single interface for all LLM roles in Sphinx-SCA.

    ─────────────────────────────────────────────
    When BERT is ready — replace classify() only:
    ─────────────────────────────────────────────
        classification = bert_classifier.predict(question)
        # Must return: {"branch": "...", "problem_type": "...", "confidence": ..., "is_math": true/false}
    """

    def classify(self, raw_text: str) -> dict:
        return classify_problem(raw_text)

    def parse(self, raw_text: str, problem_type: str) -> dict:
        return parse_problem(raw_text, problem_type)

    def steps(self, problem: str, solution: str, problem_type: str) -> list:
        return generate_steps(problem, solution, problem_type)

    def hints(self, problem: str, problem_type: str, num: int = 3) -> list:
        return generate_hints(problem, problem_type, num)

    def word_problem(self, problem_text: str) -> dict:
        return solve_word_problem(problem_text)

    def ocr_fix(self, latex_text: str) -> str:
        return validate_ocr(latex_text)

    def chat(self, message: str, history: list = None) -> str:
        """Chat normally — greetings, questions, small talk."""
        return chat(message, history)

    def chat_with_math(self, message: str, math_result: dict, history: list = None) -> str:
        """Wrap math solution in natural friendly response."""
        return chat_with_math(message, math_result, history)

    def stream_chat(self, messages: list, temperature: float = 0.7):
        """Stream conversation history from Groq."""
        return stream_chat(messages, temperature)


# ─────────────────────────────────────────────
#  QUICK TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    llm = LLMManager()

    print("=" * 55)
    print("TEST 0 — Classifier (math)")
    print(json.dumps(llm.classify("solve 2x + 5 = 11"), indent=2))

    print("\n" + "=" * 55)
    print("TEST 0b — Classifier (chat)")
    print(json.dumps(llm.classify("hi, how are you?"), indent=2))

    print("\n" + "=" * 55)
    print("TEST 6a — Chat (English greeting)")
    print(llm.chat("hi! what can you do?"))

    print("\n" + "=" * 55)
    print("TEST 6b — Chat (Arabic)")
    print(llm.chat("مرحبا، كيف حالك؟"))

    print("\n" + "=" * 55)
    print("TEST 6c — Chat with math result")
    fake_result = {
        "final_answer": "x = 3",
        "llm_steps": [
            {"step": 1, "title": "Move constant", "action": "2x = 11 - 5", "explanation": "Subtract 5 from both sides"},
            {"step": 2, "title": "Divide",         "action": "x = 6 / 2",   "explanation": "Divide both sides by 2"},
            {"step": 3, "title": "Answer",          "action": "x = 3",       "explanation": "Final answer"}
        ]
    }
    print(llm.chat_with_math("solve 2x + 5 = 11", fake_result))

    print("\n" + "=" * 55)
    print("TEST 6d — Multi-turn conversation")
    history = [
        {"role": "user",      "content": "hi!"},
        {"role": "assistant", "content": "Hello! I'm Sphinx-SCA. How can I help you?"}
    ]
    print(llm.chat("can you solve quadratic equations?", history))