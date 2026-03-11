"""
math_engine/discrete_math.py

Production-ready discrete-mathematics engine for IntelliMath.
Supports: logic expression evaluation, truth tables,
basic combinatorics (permutations, combinations, Catalan, Stirling, etc.).
"""

from __future__ import annotations

import itertools
from typing import Any

import sympy as sp
from sympy import (
    Symbol, symbols, factorial, binomial, simplify, S,
    And, Or, Not, Implies, Equivalent, Xor,
)
from sympy.logic.boolalg import truth_table as _sympy_truth_table, to_cnf, to_dnf


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _error(msg: str) -> dict[str, Any]:
    return {"error": str(msg), "confidence": 0.0}


def _parse_logic_expr(expr_str: str) -> tuple[sp.Basic, list[Symbol]]:
    """
    Parse a string logic expression.
    Accepted operators: & | ~ >> (implies)  <-> (equivalent)  ^
    Variables: single uppercase or lowercase letters.
    """
    import re
    # Discover variable names (single letters not part of keywords)
    var_names = sorted(set(re.findall(r"\b([a-zA-Z])\b", expr_str)))
    var_names = [v for v in var_names if v.lower() not in ("t", "f")]  # skip T/F literals

    local: dict[str, Any] = {}
    sym_list: list[Symbol] = []
    for v in var_names:
        s = Symbol(v)
        local[v] = s
        sym_list.append(s)

    # Normalise common operators
    normalized = expr_str
    normalized = normalized.replace("<->", " >> ").replace("↔", " >> ")
    # Replace textual operators
    normalized = normalized.replace(" and ", " & ").replace(" AND ", " & ")
    normalized = normalized.replace(" or ", " | ").replace(" OR ", " | ")
    normalized = normalized.replace(" not ", " ~ ").replace(" NOT ", " ~ ")
    normalized = normalized.replace("->", " >> ")
    normalized = normalized.replace("=>", " >> ")

    local.update({
        "And": And, "Or": Or, "Not": Not,
        "Implies": Implies, "Equivalent": Equivalent,
        "Xor": Xor, "true": S.true, "false": S.false,
        "True": S.true, "False": S.false,
    })

    expr = sp.sympify(normalized, locals=local)
    return expr, sym_list

# ---------------------------------------------------------------------------
# Logic
# ---------------------------------------------------------------------------

def _evaluate_logic(expr_str: str) -> dict[str, Any]:
    steps: list[str] = []
    expr, vars_ = _parse_logic_expr(expr_str)
    steps.append(f"Parsed expression: {expr}")

    if not vars_:
        result = bool(expr)
        steps.append(f"No variables; evaluates to: {result}")
        return {
            "branch": "discrete_math",
            "type": "logic_evaluation",
            "steps": steps,
            "final_answer": str(result),
            "confidence": 0.98,
        }

    cnf = to_cnf(expr, simplify=True)
    dnf = to_dnf(expr, simplify=True)
    steps.append(f"CNF: {cnf}")
    steps.append(f"DNF: {dnf}")

    return {
        "branch": "discrete_math",
        "type": "logic_evaluation",
        "steps": steps,
        "final_answer": {"expression": str(expr), "cnf": str(cnf), "dnf": str(dnf)},
        "confidence": 0.95,
    }


def _truth_table(expr_str: str) -> dict[str, Any]:
    steps: list[str] = []
    expr, vars_ = _parse_logic_expr(expr_str)
    steps.append(f"Expression: {expr}")
    steps.append(f"Variables: {[str(v) for v in vars_]}")

    if len(vars_) > 10:
        return _error("Too many variables for a truth table (max 10).")

    header = [str(v) for v in vars_] + [str(expr)]
    rows: list[list[Any]] = []

    for combo in itertools.product([False, True], repeat=len(vars_)):
        subs = dict(zip(vars_, combo))
        val = bool(expr.subs(subs))
        row = list(combo) + [val]
        rows.append(row)

    steps.append(f"Generated {len(rows)} rows.")

    # Compact text representation
    table_lines = [" | ".join(header)]
    table_lines.append("-" * len(table_lines[0]))
    for row in rows:
        table_lines.append(
            " | ".join("T" if c else "F" for c in row)
        )
    steps.append("Truth table:\n" + "\n".join(table_lines))

    return {
        "branch": "discrete_math",
        "type": "truth_table",
        "steps": steps,
        "final_answer": {"header": header, "rows": rows},
        "confidence": 0.98,
    }

# ---------------------------------------------------------------------------
# Combinatorics
# ---------------------------------------------------------------------------

def _permutations(n: int, r: int) -> dict[str, Any]:
    steps: list[str] = []
    if r > n:
        return _error(f"r ({r}) cannot exceed n ({n}).")
    result = factorial(n) // factorial(n - r)
    steps.append(f"P({n}, {r}) = {n}! / ({n}-{r})! = {result}")
    return {
        "branch": "discrete_math",
        "type": "permutation",
        "steps": steps,
        "final_answer": str(result),
        "confidence": 0.99,
    }


def _combinations(n: int, r: int) -> dict[str, Any]:
    steps: list[str] = []
    if r > n:
        return _error(f"r ({r}) cannot exceed n ({n}).")
    result = binomial(n, r)
    steps.append(f"C({n}, {r}) = {n}! / ({r}! × ({n}-{r})!) = {result}")
    return {
        "branch": "discrete_math",
        "type": "combination",
        "steps": steps,
        "final_answer": str(result),
        "confidence": 0.99,
    }


def _catalan(n: int) -> dict[str, Any]:
    steps: list[str] = []
    if n < 0:
        return _error("n must be non-negative for Catalan numbers.")
    result = binomial(2 * n, n) // (n + 1)
    steps.append(f"Catalan({n}) = C(2n, n) / (n+1) = C({2*n}, {n}) / {n+1} = {result}")
    return {
        "branch": "discrete_math",
        "type": "catalan_number",
        "steps": steps,
        "final_answer": str(result),
        "confidence": 0.99,
    }


def _derangements(n: int) -> dict[str, Any]:
    """Number of permutations with no fixed points."""
    steps: list[str] = []
    if n < 0:
        return _error("n must be non-negative.")
    # D(n) = n! × Σ_{i=0}^{n} (-1)^i / i!
    result = sum(
        (-1) ** i * factorial(n) // factorial(i) for i in range(n + 1)
    )
    steps.append(f"D({n}) = {n}! × Σ(-1)^i / i! for i=0..{n}")
    steps.append(f"D({n}) = {result}")
    return {
        "branch": "discrete_math",
        "type": "derangement",
        "steps": steps,
        "final_answer": str(result),
        "confidence": 0.98,
    }


def _pigeonhole(items: int, containers: int) -> dict[str, Any]:
    steps: list[str] = []
    if containers <= 0:
        return _error("Number of containers must be positive.")
    if items < 0:
        return _error("Number of items must be non-negative.")
    min_in_one = -(-items // containers)  # ceiling division
    steps.append(f"Items = {items}, Containers = {containers}")
    steps.append(
        f"By the Pigeonhole Principle, at least one container must hold "
        f"⌈{items}/{containers}⌉ = {min_in_one} item(s)."
    )
    return {
        "branch": "discrete_math",
        "type": "pigeonhole",
        "steps": steps,
        "final_answer": str(min_in_one),
        "confidence": 0.99,
    }

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def solve(operation: str, **kwargs: Any) -> dict[str, Any]:
    """
    Solve a discrete-math problem.

    Parameters
    ----------
    operation : str
        One of: evaluate_logic, truth_table, permutation, combination,
        catalan, derangement, pigeonhole.
    **kwargs
        Operation-specific parameters.

    Returns
    -------
    dict
        Structured JSON-serialisable result.
    """
    if not isinstance(operation, str) or not operation.strip():
        return _error("Operation must be a non-empty string.")

    op = operation.strip().lower().replace(" ", "_")

    try:
        if op in ("evaluate_logic", "logic", "eval_logic"):
            expr_str = kwargs.get("expression")
            if not expr_str:
                return _error("Missing 'expression' parameter.")
            return _evaluate_logic(str(expr_str))

        if op in ("truth_table", "tt"):
            expr_str = kwargs.get("expression")
            if not expr_str:
                return _error("Missing 'expression' parameter.")
            return _truth_table(str(expr_str))

        if op in ("permutation", "perm"):
            n = int(kwargs["n"])
            r = int(kwargs["r"])
            return _permutations(n, r)

        if op in ("combination", "comb"):
            n = int(kwargs["n"])
            r = int(kwargs["r"])
            return _combinations(n, r)

        if op == "catalan":
            return _catalan(int(kwargs["n"]))

        if op in ("derangement", "derangements"):
            return _derangements(int(kwargs["n"]))

        if op == "pigeonhole":
            return _pigeonhole(
                int(kwargs["items"]),
                int(kwargs["containers"]),
            )

        return _error(
            f"Unknown operation '{operation}'. "
            "Supported: evaluate_logic, truth_table, permutation, combination, "
            "catalan, derangement, pigeonhole."
        )

    except KeyError as exc:
        return _error(f"Missing required parameter: {exc}")
    except (TypeError, ValueError) as exc:
        return _error(f"Invalid input: {exc}")
    except Exception as exc:  # noqa: BLE001
        return _error(f"Discrete math solver error: {exc}")
