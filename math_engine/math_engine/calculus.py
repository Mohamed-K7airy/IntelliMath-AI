"""
math_engine/calculus.py

Production-ready calculus engine for IntelliMath.
Supports: derivatives, integrals, limits, basic differential equations.
Detects problem type automatically from the expression string.
"""

from __future__ import annotations

import re
from typing import Any

import sympy as sp
from sympy import (
    Symbol, symbols, sympify,
    diff, integrate, limit, dsolve,
    Function, Eq, oo,
    SympifyError,
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

_PROBLEM_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("limit",        re.compile(r"\blim(?:it)?\b", re.IGNORECASE)),
    ("ode",          re.compile(r"\bode\b|differential\s+eq", re.IGNORECASE)),
    ("integral",     re.compile(r"\bintegra(?:l|te)\b", re.IGNORECASE)),
    ("derivative",   re.compile(r"\bderivativ|differentiat|\bd/d[a-z]\b", re.IGNORECASE)),
]


def _safe_parse(expr_str: str, local_dict: dict | None = None) -> sp.Expr:
    """Parse a string into a SymPy expression with robust transformations."""
    return parse_expr(
        expr_str,
        local_dict=local_dict or {},
        transformations=_TRANSFORMATIONS,
        evaluate=False,
    )


def _detect_type(problem: str) -> str:
    """Heuristically detect the calculus sub-type from the problem string."""
    for name, pattern in _PROBLEM_PATTERNS:
        if pattern.search(problem):
            return name
    return "derivative"  # safe default


def _error(msg: str) -> dict[str, Any]:
    return {"error": str(msg), "confidence": 0.0}


def _extract_var(problem: str) -> Symbol:
    """Try to pull the variable name from the problem text; default to x."""
    m = re.search(r"\bwith\s+respect\s+to\s+([a-zA-Z])\b", problem, re.IGNORECASE)
    if m:
        return Symbol(m.group(1))
    m = re.search(r"\bd/d([a-zA-Z])\b", problem)
    if m:
        return Symbol(m.group(1))
    return Symbol("x")


def _extract_expr(problem: str) -> str:
    """Strip directive words, leaving only the mathematical expression."""
    cleaned = re.sub(
        r"(?i)\b(?:find|compute|calculate|evaluate|the|of|derivative|"
        r"integral|integrate|limit|differentiate|with\s+respect\s+to\s+[a-z]"
        r"|as\s+[a-z]\s*->\s*\S+|from\s+\S+\s+to\s+\S+)\b",
        " ", problem,
    )
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned


def _extract_limit_point(problem: str) -> tuple[Symbol, sp.Expr]:
    """Parse 'as x -> value' from the problem string."""
    m = re.search(
        r"as\s+([a-zA-Z])\s*(?:->|→|approaches?)\s*(\S+)",
        problem, re.IGNORECASE,
    )
    if m:
        var = Symbol(m.group(1))
        raw = m.group(2).strip().rstrip(".,;")
        if raw.lower() in ("inf", "infinity", "oo", "+oo"):
            point = oo
        elif raw.lower() in ("-inf", "-infinity", "-oo"):
            point = -oo
        else:
            point = sympify(raw)
        return var, point
    return Symbol("x"), sympify(0)


def _extract_integral_bounds(problem: str) -> tuple[sp.Expr, sp.Expr] | None:
    """Return (lower, upper) if the problem specifies definite bounds."""
    m = re.search(
        r"from\s+(\S+)\s+to\s+(\S+)",
        problem, re.IGNORECASE,
    )
    if m:
        lo = sympify(m.group(1))
        hi = sympify(m.group(2))
        return (lo, hi)
    return None

# ---------------------------------------------------------------------------
# Solvers
# ---------------------------------------------------------------------------

def _solve_derivative(expr: sp.Expr, var: Symbol) -> dict[str, Any]:
    steps: list[str] = []
    steps.append(f"Identify expression: {expr}")
    steps.append(f"Differentiate with respect to {var}")
    result = diff(expr, var)
    simplified = sp.simplify(result)
    if simplified != result:
        steps.append(f"Raw derivative: {result}")
        steps.append(f"Simplified: {simplified}")
        result = simplified
    else:
        steps.append(f"Result: {result}")
    return {
        "branch": "calculus",
        "type": "derivative",
        "steps": steps,
        "final_answer": str(result),
        "confidence": 0.98,
    }


def _solve_integral(expr: sp.Expr, var: Symbol, bounds: tuple | None) -> dict[str, Any]:
    steps: list[str] = []
    if bounds:
        lo, hi = bounds
        steps.append(f"Identify expression: {expr}")
        steps.append(f"Compute definite integral from {lo} to {hi} with respect to {var}")
        result = integrate(expr, (var, lo, hi))
        steps.append(f"Result: {result}")
    else:
        steps.append(f"Identify expression: {expr}")
        steps.append(f"Compute indefinite integral with respect to {var}")
        result = integrate(expr, var)
        steps.append(f"Result: {result} + C")
    simplified = sp.simplify(result)
    if simplified != result:
        steps.append(f"Simplified: {simplified}")
        result = simplified
    return {
        "branch": "calculus",
        "type": "definite_integral" if bounds else "indefinite_integral",
        "steps": steps,
        "final_answer": str(result) + ("" if bounds else " + C"),
        "confidence": 0.95,
    }


def _solve_limit(expr: sp.Expr, var: Symbol, point: sp.Expr) -> dict[str, Any]:
    steps: list[str] = []
    steps.append(f"Identify expression: {expr}")
    steps.append(f"Compute limit as {var} → {point}")
    result = limit(expr, var, point)
    steps.append(f"Result: {result}")
    return {
        "branch": "calculus",
        "type": "limit",
        "steps": steps,
        "final_answer": str(result),
        "confidence": 0.96,
    }


def _solve_ode(problem: str) -> dict[str, Any]:
    """Solve a basic ODE.  Expects a string like ``y'' - 3y' + 2y = 0``."""
    steps: list[str] = []
    x = Symbol("x")
    y = Function("y")

    # Normalise prime notation → SymPy Derivative notation
    eq_str = problem
    for directive in ("ode", "solve", "differential equation"):
        eq_str = re.sub(rf"\b{directive}\b", "", eq_str, flags=re.IGNORECASE)
    eq_str = eq_str.strip().rstrip(".,;")

    eq_str = eq_str.replace("y'''", "Derivative(y(x), x, 3)")
    eq_str = eq_str.replace("y''", "Derivative(y(x), x, 2)")
    eq_str = eq_str.replace("y'", "Derivative(y(x), x)")
    eq_str = eq_str.replace("y", "y(x)")

    # Split on '='
    parts = eq_str.split("=")
    if len(parts) == 2:
        lhs = _safe_parse(parts[0].strip(), {"y": y, "x": x, "Derivative": sp.Derivative})
        rhs = _safe_parse(parts[1].strip(), {"y": y, "x": x, "Derivative": sp.Derivative})
        equation = Eq(lhs, rhs)
    else:
        equation = Eq(
            _safe_parse(eq_str, {"y": y, "x": x, "Derivative": sp.Derivative}),
            0,
        )

    steps.append(f"Parsed ODE: {equation}")
    result = dsolve(equation, y(x))
    steps.append(f"General solution: {result}")

    return {
        "branch": "calculus",
        "type": "ode",
        "steps": steps,
        "final_answer": str(result),
        "confidence": 0.90,
    }

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def solve(problem: str) -> dict[str, Any]:
    """
    Solve a calculus problem given as a natural-language / symbolic string.

    Parameters
    ----------
    problem : str
        A description such as "derivative of x**3 + 2x" or
        "integrate sin(x) from 0 to pi".

    Returns
    -------
    dict
        Structured JSON-serialisable result with branch, type, steps,
        final_answer, and confidence.
    """
    if not isinstance(problem, str) or not problem.strip():
        return _error("Input must be a non-empty string.")

    problem = problem.strip()

    try:
        prob_type = _detect_type(problem)

        if prob_type == "ode":
            return _solve_ode(problem)

        var = _extract_var(problem)
        raw_expr = _extract_expr(problem)
        if not raw_expr:
            return _error("Could not extract a mathematical expression from the input.")

        expr = _safe_parse(raw_expr, {str(var): var})

        if prob_type == "derivative":
            return _solve_derivative(expr, var)

        if prob_type == "integral":
            bounds = _extract_integral_bounds(problem)
            return _solve_integral(expr, var, bounds)

        if prob_type == "limit":
            var_lim, point = _extract_limit_point(problem)
            return _solve_limit(expr, var_lim, point)

        return _error(f"Unsupported calculus sub-type: {prob_type}")

    except SympifyError as exc:
        return _error(f"Failed to parse expression: {exc}")
    except Exception as exc:  # noqa: BLE001
        return _error(f"Calculus solver error: {exc}")
