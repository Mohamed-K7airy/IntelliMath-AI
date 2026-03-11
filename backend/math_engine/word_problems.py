"""
math_engine/word_problems.py

Production-ready word-problem engine for IntelliMath.
Parses natural-language math problems, extracts algebraic relationships,
solves them symbolically, and returns step-by-step explanations.
"""

from __future__ import annotations

import re
from typing import Any

import sympy as sp
from sympy import (
    Symbol, symbols, Eq, solve as sym_solve, simplify,
    Rational, oo, S,
)
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)


def _error(msg: str) -> dict[str, Any]:
    return {"error": str(msg), "confidence": 0.0}


def _safe_parse(expr_str: str, local_dict: dict | None = None) -> sp.Expr:
    return parse_expr(
        expr_str,
        local_dict=local_dict or {},
        transformations=_TRANSFORMATIONS,
        evaluate=False,
    )


# ---------------------------------------------------------------------------
# Text → algebra extraction pipeline
# ---------------------------------------------------------------------------

# Number-word map for basic parsing
_WORD_NUMS: dict[str, int] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90, "hundred": 100, "thousand": 1000,
}

_OP_KEYWORDS: dict[str, str] = {
    "sum": "+", "total": "+", "plus": "+", "added to": "+",
    "more than": "+", "increased by": "+", "combined": "+",
    "difference": "-", "minus": "-", "less than": "-",
    "decreased by": "-", "fewer than": "-", "subtract": "-",
    "product": "*", "times": "*", "multiplied by": "*",
    "of": "*",
    "quotient": "/", "divided by": "/", "per": "/", "ratio": "/",
    "twice": "2*", "double": "2*", "triple": "3*", "half": "/2",
    "square": "**2", "squared": "**2", "cube": "**3", "cubed": "**3",
}

_COMPARATORS: list[tuple[str, str]] = [
    ("is equal to", "="),
    ("equals", "="),
    ("equal to", "="),
    ("is", "="),
    ("gives", "="),
    ("results in", "="),
    ("yields", "="),
]


def _replace_word_numbers(text: str) -> str:
    """Replace written-out numbers with digits."""
    for word, num in sorted(_WORD_NUMS.items(), key=lambda x: -len(x[0])):
        text = re.sub(rf"\b{word}\b", str(num), text, flags=re.IGNORECASE)
    return text


def _extract_equations(text: str) -> list[str]:
    """
    Attempt to find explicit equations (anything with '=') or
    build them from comparative phrases.
    """
    equations: list[str] = []

    # Try explicit '=' first
    if "=" in text:
        parts = text.split(".")
        for part in parts:
            if "=" in part:
                equations.append(part.strip())
        if equations:
            return equations

    # Fall back to comparator phrases
    for phrase, _ in _COMPARATORS:
        if phrase in text.lower():
            idx = text.lower().index(phrase)
            lhs = text[:idx].strip()
            rhs = text[idx + len(phrase):].strip().rstrip(".")
            equations.append(f"{lhs} = {rhs}")
            return equations

    return equations


def _algebraise(text: str) -> tuple[list[sp.Eq], list[Symbol], list[str]]:
    """
    Best-effort conversion of natural-language problem into
    SymPy Eq objects.  Returns (equations, variables, explanation_steps).
    """
    steps: list[str] = []
    cleaned = _replace_word_numbers(text)
    steps.append(f"Normalised text: {cleaned}")

    # Discover variable references
    var_pattern = re.compile(r"\b([a-zA-Z])\b")
    candidate_vars = set(var_pattern.findall(cleaned))
    # Filter out common non-variable letters
    noise = {"a", "i", "A", "I", "s", "S"}
    # Keep single letters that look like variables
    candidate_vars -= noise
    if not candidate_vars:
        candidate_vars = {"x"}  # fallback

    sym_map: dict[str, Symbol] = {v: Symbol(v) for v in sorted(candidate_vars)}
    steps.append(f"Identified variables: {list(sym_map.keys())}")

    raw_eqs = _extract_equations(cleaned)
    if not raw_eqs:
        # Last resort: treat the whole thing as an expression = 0
        raw_eqs = [f"{cleaned} = 0"]

    equations: list[sp.Eq] = []
    for raw in raw_eqs:
        parts = raw.split("=")
        if len(parts) != 2:
            continue
        lhs_str = parts[0].strip()
        rhs_str = parts[1].strip()

        # Lightweight keyword→operator substitution
        for keyword, op in sorted(_OP_KEYWORDS.items(), key=lambda x: -len(x[0])):
            lhs_str = lhs_str.replace(keyword, f" {op} ")
            rhs_str = rhs_str.replace(keyword, f" {op} ")

        # Remove residual words (keep digits, operators, variables)
        lhs_str = re.sub(r"[^0-9a-zA-Z+\-*/().^ ]", " ", lhs_str)
        rhs_str = re.sub(r"[^0-9a-zA-Z+\-*/().^ ]", " ", rhs_str)
        lhs_str = re.sub(r"\s{2,}", " ", lhs_str).strip()
        rhs_str = re.sub(r"\s{2,}", " ", rhs_str).strip()

        if not lhs_str:
            lhs_str = "0"
        if not rhs_str:
            rhs_str = "0"

        try:
            lhs_expr = _safe_parse(lhs_str, sym_map)
            rhs_expr = _safe_parse(rhs_str, sym_map)
            eq = Eq(lhs_expr, rhs_expr)
            equations.append(eq)
            steps.append(f"Equation: {eq}")
        except Exception:
            steps.append(f"Could not parse equation fragment: {raw}")

    return equations, list(sym_map.values()), steps


# ---------------------------------------------------------------------------
# Specialised patterns
# ---------------------------------------------------------------------------

def _try_age_problem(text: str) -> dict[str, Any] | None:
    """
    Detect and solve common age-word-problems.
    Pattern: "X is N years older/younger than Y.  <relationship> = K."
    """
    age_pattern = re.compile(
        r"(\w+)\s+is\s+(\d+)\s+years?\s+(older|younger)\s+than\s+(\w+)",
        re.IGNORECASE,
    )
    m = age_pattern.search(text)
    if not m:
        return None

    name_a = m.group(1)
    diff = int(m.group(2))
    direction = m.group(3).lower()
    name_b = m.group(4)

    a = Symbol(name_a)
    b = Symbol(name_b)

    if direction == "older":
        eq1 = Eq(a, b + diff)
    else:
        eq1 = Eq(a, b - diff)

    steps: list[str] = [
        f"Identified age problem: {name_a} and {name_b}.",
        f"Relationship: {name_a} is {diff} years {direction} than {name_b}.",
        f"Equation 1: {eq1}",
    ]

    # Look for a second equation (e.g., sum of ages)
    sum_pattern = re.compile(
        r"(?:sum|total|combined)\s+.*?(?:ages?)?\s*(?:is|=|equals?)\s*(\d+)",
        re.IGNORECASE,
    )
    ms = sum_pattern.search(text)
    equations = [eq1]
    if ms:
        total = int(ms.group(1))
        eq2 = Eq(a + b, total)
        equations.append(eq2)
        steps.append(f"Equation 2: {eq2}")

    solution = sym_solve(equations, [a, b], dict=True)
    if solution:
        sol = solution[0]
        for var, val in sol.items():
            steps.append(f"{var} = {val}")
        return {
            "branch": "word_problems",
            "type": "age_problem",
            "steps": steps,
            "final_answer": {str(k): str(v) for k, v in sol.items()},
            "confidence": 0.92,
        }

    return None


def _try_distance_rate_time(text: str) -> dict[str, Any] | None:
    """d = r × t  pattern."""
    if not re.search(r"\b(speed|rate|velocity|km/h|mph|m/s|miles|kilometers)\b", text, re.IGNORECASE):
        return None

    steps: list[str] = ["Detected distance-rate-time problem."]
    d, r, t = symbols("d r t", positive=True)
    base_eq = Eq(d, r * t)
    steps.append(f"Base equation: {base_eq}")

    # Extract numbers
    nums = [Rational(x) for x in re.findall(r"\d+(?:\.\d+)?", text)]
    if len(nums) < 2:
        return None

    # Heuristic: assign numbers by keyword proximity
    known: dict[Symbol, Rational] = {}
    lower = text.lower()
    if "hour" in lower or "time" in lower:
        for n in nums:
            if "hour" in lower or "minute" in lower:
                if t not in known:
                    known[t] = n
                    continue
            if ("speed" in lower or "rate" in lower or "km" in lower or "mph" in lower
                    or "mile" in lower):
                if r not in known:
                    known[r] = n
                    continue
            if d not in known:
                known[d] = n

    # If we have two knowns, solve for the third
    if len(known) == 2:
        unknowns = {d, r, t} - set(known.keys())
        unknown = unknowns.pop()
        eq = base_eq.subs(known)
        steps.append(f"Substituted: {eq}")
        sol = sym_solve(eq, unknown)
        if sol:
            steps.append(f"{unknown} = {sol[0]}")
            return {
                "branch": "word_problems",
                "type": "distance_rate_time",
                "steps": steps,
                "final_answer": str(sol[0]),
                "confidence": 0.88,
            }

    return None


# ---------------------------------------------------------------------------
# Generic solver (fallback)
# ---------------------------------------------------------------------------

def _generic_solve(text: str) -> dict[str, Any]:
    equations, variables, steps = _algebraise(text)

    if not equations:
        return _error(
            "Could not extract any solvable equation from the problem text."
        )

    solution = sym_solve(equations, variables, dict=True)

    if not solution:
        # Try solving each equation independently
        for eq in equations:
            free = list(eq.free_symbols)
            sol = sym_solve(eq, free, dict=True)
            if sol:
                solution = sol
                break

    if not solution:
        return _error("Could not find a solution for the extracted equations.")

    sol = solution[0] if isinstance(solution, list) else solution
    for var, val in sol.items():
        steps.append(f"{var} = {simplify(val)}")

    return {
        "branch": "word_problems",
        "type": "algebraic_word_problem",
        "steps": steps,
        "final_answer": {str(k): str(simplify(v)) for k, v in sol.items()},
        "confidence": 0.80,
    }

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def solve(problem: str) -> dict[str, Any]:
    """
    Solve a word problem given as a natural-language string.

    The engine attempts specialised pattern matchers first
    (age problems, distance-rate-time), then falls back to
    generic algebraic extraction and solving.

    Parameters
    ----------
    problem : str
        The word problem in plain English.

    Returns
    -------
    dict
        Structured JSON-serialisable result with branch, type, steps,
        final_answer, and confidence.
    """
    if not isinstance(problem, str) or not problem.strip():
        return _error("Input must be a non-empty string.")

    text = problem.strip()

    try:
        # Specialised solvers
        result = _try_age_problem(text)
        if result:
            return result

        result = _try_distance_rate_time(text)
        if result:
            return result

        # Generic fallback
        return _generic_solve(text)

    except Exception as exc:  # noqa: BLE001
        return _error(f"Word problem solver error: {exc}")
