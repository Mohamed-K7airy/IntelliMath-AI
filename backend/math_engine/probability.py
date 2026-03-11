"""
math_engine/probability.py

Production-ready probability engine for IntelliMath.
Supports: basic probability, permutations, combinations,
conditional probability.
"""

from __future__ import annotations

import math
from typing import Any

import sympy as sp
from sympy import Rational, binomial, factorial, simplify


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _error(msg: str) -> dict[str, Any]:
    return {"error": str(msg), "confidence": 0.0}


def _validate_positive_int(value: Any, name: str) -> int | dict:
    try:
        v = int(value)
    except (TypeError, ValueError):
        return _error(f"'{name}' must be an integer, got {type(value).__name__}.")
    if v < 0:
        return _error(f"'{name}' must be non-negative, got {v}.")
    return v


def _validate_probability(value: Any, name: str) -> Rational | dict:
    try:
        p = Rational(value)
    except (TypeError, ValueError):
        return _error(f"'{name}' must be a number, got {type(value).__name__}.")
    if not (0 <= p <= 1):
        return _error(f"'{name}' must be between 0 and 1, got {float(p):.6g}.")
    return p

# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------

def _basic_probability(
    favorable: int, total: int
) -> dict[str, Any]:
    steps: list[str] = []
    if total <= 0:
        return _error("Total outcomes must be a positive integer.")
    if favorable < 0:
        return _error("Favorable outcomes must be non-negative.")
    if favorable > total:
        return _error("Favorable outcomes cannot exceed total outcomes.")

    p = Rational(favorable, total)
    steps.append(f"Favorable outcomes: {favorable}")
    steps.append(f"Total outcomes: {total}")
    steps.append(f"P(E) = favorable / total = {favorable}/{total}")
    steps.append(f"P(E) = {p} ≈ {float(p):.6f}")

    return {
        "branch": "probability",
        "type": "basic_probability",
        "steps": steps,
        "final_answer": str(p),
        "confidence": 0.99,
    }


def _permutation(n: int, r: int) -> dict[str, Any]:
    steps: list[str] = []
    if r > n:
        return _error(f"r ({r}) cannot exceed n ({n}) for permutations.")
    steps.append(f"n = {n}, r = {r}")
    steps.append(f"P(n, r) = n! / (n - r)!")
    steps.append(f"P({n}, {r}) = {n}! / {n - r}!")

    result = factorial(n) // factorial(n - r)
    steps.append(f"= {result}")

    return {
        "branch": "probability",
        "type": "permutation",
        "steps": steps,
        "final_answer": str(result),
        "confidence": 0.99,
    }


def _combination(n: int, r: int) -> dict[str, Any]:
    steps: list[str] = []
    if r > n:
        return _error(f"r ({r}) cannot exceed n ({n}) for combinations.")
    steps.append(f"n = {n}, r = {r}")
    steps.append(f"C(n, r) = n! / (r! × (n - r)!)")
    steps.append(f"C({n}, {r}) = {n}! / ({r}! × {n - r}!)")

    result = binomial(n, r)
    steps.append(f"= {result}")

    return {
        "branch": "probability",
        "type": "combination",
        "steps": steps,
        "final_answer": str(result),
        "confidence": 0.99,
    }


def _conditional_probability(
    p_a_and_b: Any,
    p_b: Any,
) -> dict[str, Any]:
    """P(A|B) = P(A ∩ B) / P(B)."""
    steps: list[str] = []
    pab = _validate_probability(p_a_and_b, "P(A ∩ B)")
    if isinstance(pab, dict):
        return pab
    pb = _validate_probability(p_b, "P(B)")
    if isinstance(pb, dict):
        return pb
    if pb == 0:
        return _error("P(B) cannot be zero for conditional probability.")

    result = Rational(pab, pb)
    steps.append(f"P(A ∩ B) = {pab}")
    steps.append(f"P(B) = {pb}")
    steps.append(f"P(A|B) = P(A ∩ B) / P(B) = {pab} / {pb}")
    steps.append(f"P(A|B) = {result} ≈ {float(result):.6f}")

    # Clamp confidence if result is out of [0,1] (shouldn't happen with valid input)
    conf = 0.97 if 0 <= result <= 1 else 0.60

    return {
        "branch": "probability",
        "type": "conditional_probability",
        "steps": steps,
        "final_answer": str(result),
        "confidence": conf,
    }


def _bayes_theorem(
    p_b_given_a: Any,
    p_a: Any,
    p_b: Any,
) -> dict[str, Any]:
    """P(A|B) = P(B|A) × P(A) / P(B)."""
    steps: list[str] = []
    pba = _validate_probability(p_b_given_a, "P(B|A)")
    if isinstance(pba, dict):
        return pba
    pa = _validate_probability(p_a, "P(A)")
    if isinstance(pa, dict):
        return pa
    pb = _validate_probability(p_b, "P(B)")
    if isinstance(pb, dict):
        return pb
    if pb == 0:
        return _error("P(B) cannot be zero.")

    result = simplify(pba * pa / pb)
    steps.append(f"P(B|A) = {pba}")
    steps.append(f"P(A) = {pa}")
    steps.append(f"P(B) = {pb}")
    steps.append(f"P(A|B) = P(B|A) × P(A) / P(B)")
    steps.append(f"P(A|B) = {pba} × {pa} / {pb}")
    steps.append(f"P(A|B) = {result} ≈ {float(result):.6f}")

    return {
        "branch": "probability",
        "type": "bayes_theorem",
        "steps": steps,
        "final_answer": str(result),
        "confidence": 0.96,
    }


def _binomial_probability(
    n: int, k: int, p: Any
) -> dict[str, Any]:
    """P(X = k) = C(n, k) × p^k × (1-p)^(n-k)."""
    steps: list[str] = []
    prob = _validate_probability(p, "p")
    if isinstance(prob, dict):
        return prob
    if k > n or k < 0:
        return _error(f"k must satisfy 0 <= k <= n. Got k={k}, n={n}.")

    q = 1 - prob
    coeff = binomial(n, k)
    result = simplify(coeff * prob**k * q**(n - k))

    steps.append(f"n = {n}, k = {k}, p = {prob}")
    steps.append(f"P(X = k) = C(n,k) × p^k × (1-p)^(n-k)")
    steps.append(f"C({n},{k}) = {coeff}")
    steps.append(f"p^{k} = {prob**k}")
    steps.append(f"(1-p)^{n - k} = {q**(n - k)}")
    steps.append(f"P(X = {k}) = {coeff} × {prob**k} × {q**(n - k)}")
    steps.append(f"= {result} ≈ {float(result):.6f}")

    return {
        "branch": "probability",
        "type": "binomial_probability",
        "steps": steps,
        "final_answer": str(result),
        "confidence": 0.97,
    }

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def solve(operation: str, **kwargs: Any) -> dict[str, Any]:
    """
    Solve a probability problem.

    Parameters
    ----------
    operation : str
        One of: basic, permutation, combination, conditional, bayes,
        binomial.
    **kwargs
        Operation-specific parameters.
        - basic: favorable (int), total (int)
        - permutation: n (int), r (int)
        - combination: n (int), r (int)
        - conditional: p_a_and_b (number), p_b (number)
        - bayes: p_b_given_a, p_a, p_b  (numbers in [0,1])
        - binomial: n (int), k (int), p (number in [0,1])

    Returns
    -------
    dict
        Structured JSON-serialisable result.
    """
    if not isinstance(operation, str) or not operation.strip():
        return _error("Operation must be a non-empty string.")

    op = operation.strip().lower().replace(" ", "_")

    try:
        if op in ("basic", "basic_probability"):
            fav = _validate_positive_int(kwargs.get("favorable"), "favorable")
            if isinstance(fav, dict):
                return fav
            tot = _validate_positive_int(kwargs.get("total"), "total")
            if isinstance(tot, dict):
                return tot
            return _basic_probability(fav, tot)

        if op in ("permutation", "perm", "p"):
            n = _validate_positive_int(kwargs.get("n"), "n")
            if isinstance(n, dict):
                return n
            r = _validate_positive_int(kwargs.get("r"), "r")
            if isinstance(r, dict):
                return r
            return _permutation(n, r)

        if op in ("combination", "comb", "c"):
            n = _validate_positive_int(kwargs.get("n"), "n")
            if isinstance(n, dict):
                return n
            r = _validate_positive_int(kwargs.get("r"), "r")
            if isinstance(r, dict):
                return r
            return _combination(n, r)

        if op in ("conditional", "conditional_probability"):
            return _conditional_probability(
                kwargs.get("p_a_and_b"),
                kwargs.get("p_b"),
            )

        if op in ("bayes", "bayes_theorem"):
            return _bayes_theorem(
                kwargs.get("p_b_given_a"),
                kwargs.get("p_a"),
                kwargs.get("p_b"),
            )

        if op in ("binomial", "binomial_probability"):
            n = _validate_positive_int(kwargs.get("n"), "n")
            if isinstance(n, dict):
                return n
            k = _validate_positive_int(kwargs.get("k"), "k")
            if isinstance(k, dict):
                return k
            return _binomial_probability(n, k, kwargs.get("p"))

        return _error(
            f"Unknown operation '{operation}'. "
            f"Supported: basic, permutation, combination, conditional, bayes, binomial."
        )

    except Exception as exc:  # noqa: BLE001
        return _error(f"Probability solver error: {exc}")
