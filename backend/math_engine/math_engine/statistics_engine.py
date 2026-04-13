"""
math_engine/statistics.py

Production-ready descriptive-statistics engine for IntelliMath.
Supports: mean, median, mode, variance, standard deviation,
range, IQR, z-score, percentile.
"""

from __future__ import annotations

import math
from typing import Any, Sequence

from sympy import Rational, sqrt, simplify, S


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _error(msg: str) -> dict[str, Any]:
    return {"error": str(msg), "confidence": 0.0}


def _to_rationals(data: Sequence) -> list[Rational]:
    """Convert a sequence of numbers to SymPy Rationals for exact arithmetic."""
    out: list[Rational] = []
    for i, v in enumerate(data):
        try:
            out.append(Rational(v))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Element at index {i} is not numeric: {v!r}") from exc
    return out


def _validate_data(data: Any) -> list[Rational] | dict:
    if not isinstance(data, (list, tuple)):
        return _error("Data must be a list or tuple of numbers.")
    if len(data) == 0:
        return _error("Data must not be empty.")
    try:
        return _to_rationals(data)
    except ValueError as exc:
        return _error(str(exc))

# ---------------------------------------------------------------------------
# Core computations (pure, no side-effects)
# ---------------------------------------------------------------------------

def _mean(vals: list[Rational]) -> Rational:
    return sum(vals) / len(vals)


def _median(vals: list[Rational]) -> Rational:
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2


def _mode(vals: list[Rational]) -> list[Rational]:
    from collections import Counter
    counts = Counter(vals)
    max_count = max(counts.values())
    if max_count == 1:
        return []  # no mode
    return sorted(k for k, v in counts.items() if v == max_count)


def _variance(vals: list[Rational], *, population: bool = True) -> Rational:
    m = _mean(vals)
    n = len(vals)
    ss = sum((x - m) ** 2 for x in vals)
    return ss / n if population else ss / (n - 1)


def _std_dev(vals: list[Rational], *, population: bool = True) -> Any:
    return sqrt(_variance(vals, population=population))

# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------

def _compute_mean(vals: list[Rational]) -> dict[str, Any]:
    steps: list[str] = []
    steps.append(f"Data ({len(vals)} values): {[str(v) for v in vals]}")
    total = sum(vals)
    steps.append(f"Sum = {total}")
    result = _mean(vals)
    steps.append(f"Mean = Sum / n = {total} / {len(vals)} = {result}")
    steps.append(f"≈ {float(result):.6f}")
    return {
        "branch": "statistics",
        "type": "mean",
        "steps": steps,
        "final_answer": str(result),
        "confidence": 0.99,
    }


def _compute_median(vals: list[Rational]) -> dict[str, Any]:
    steps: list[str] = []
    s = sorted(vals)
    steps.append(f"Sorted data: {[str(v) for v in s]}")
    n = len(s)
    result = _median(vals)
    if n % 2 == 1:
        steps.append(f"Odd count ({n}): median = middle value = {result}")
    else:
        mid = n // 2
        steps.append(
            f"Even count ({n}): median = avg of {s[mid - 1]} and {s[mid]} = {result}"
        )
    return {
        "branch": "statistics",
        "type": "median",
        "steps": steps,
        "final_answer": str(result),
        "confidence": 0.99,
    }


def _compute_mode(vals: list[Rational]) -> dict[str, Any]:
    steps: list[str] = []
    from collections import Counter
    counts = Counter(vals)
    steps.append(f"Frequency table: {dict((str(k), v) for k, v in counts.items())}")
    modes = _mode(vals)
    if not modes:
        steps.append("No mode (all values appear equally often).")
        answer = "no mode"
    else:
        steps.append(f"Mode(s): {[str(m) for m in modes]}")
        answer = str([str(m) for m in modes])
    return {
        "branch": "statistics",
        "type": "mode",
        "steps": steps,
        "final_answer": answer,
        "confidence": 0.98,
    }


def _compute_variance(
    vals: list[Rational], population: bool = True
) -> dict[str, Any]:
    steps: list[str] = []
    label = "population" if population else "sample"
    m = _mean(vals)
    steps.append(f"Mean = {m}")
    deviations = [(x - m) for x in vals]
    sq_devs = [(d ** 2) for d in deviations]
    steps.append(f"Squared deviations: {[str(d) for d in sq_devs]}")
    ss = sum(sq_devs)
    steps.append(f"Sum of squared deviations = {ss}")
    n = len(vals) if population else len(vals) - 1
    result = ss / n
    steps.append(f"{label.capitalize()} variance = {ss} / {n} = {result}")
    steps.append(f"≈ {float(result):.6f}")
    return {
        "branch": "statistics",
        "type": f"{label}_variance",
        "steps": steps,
        "final_answer": str(result),
        "confidence": 0.98,
    }


def _compute_std_dev(
    vals: list[Rational], population: bool = True
) -> dict[str, Any]:
    steps: list[str] = []
    label = "population" if population else "sample"
    var = _variance(vals, population=population)
    steps.append(f"{label.capitalize()} variance = {var}")
    result = sqrt(var)
    simplified = simplify(result)
    steps.append(f"Standard deviation = √({var}) = {simplified}")
    steps.append(f"≈ {float(simplified):.6f}")
    return {
        "branch": "statistics",
        "type": f"{label}_std_dev",
        "steps": steps,
        "final_answer": str(simplified),
        "confidence": 0.98,
    }


def _compute_range(vals: list[Rational]) -> dict[str, Any]:
    steps: list[str] = []
    s = sorted(vals)
    result = s[-1] - s[0]
    steps.append(f"Min = {s[0]}, Max = {s[-1]}")
    steps.append(f"Range = Max - Min = {result}")
    return {
        "branch": "statistics",
        "type": "range",
        "steps": steps,
        "final_answer": str(result),
        "confidence": 0.99,
    }


def _compute_iqr(vals: list[Rational]) -> dict[str, Any]:
    steps: list[str] = []
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    lower = s[:mid]
    upper = s[mid + 1:] if n % 2 == 1 else s[mid:]
    q1 = _median(lower) if lower else S.Zero
    q3 = _median(upper) if upper else S.Zero
    iqr = q3 - q1
    steps.append(f"Sorted data: {[str(v) for v in s]}")
    steps.append(f"Q1 (median of lower half) = {q1}")
    steps.append(f"Q3 (median of upper half) = {q3}")
    steps.append(f"IQR = Q3 - Q1 = {iqr}")
    return {
        "branch": "statistics",
        "type": "iqr",
        "steps": steps,
        "final_answer": str(iqr),
        "confidence": 0.97,
    }


def _compute_summary(vals: list[Rational]) -> dict[str, Any]:
    """Five-number summary + mean."""
    steps: list[str] = []
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    lower = s[:mid]
    upper = s[mid + 1:] if n % 2 == 1 else s[mid:]

    minimum = s[0]
    maximum = s[-1]
    med = _median(vals)
    q1 = _median(lower) if lower else med
    q3 = _median(upper) if upper else med
    avg = _mean(vals)
    sd = simplify(_std_dev(vals))

    steps.append(f"Count = {n}")
    steps.append(f"Min = {minimum}")
    steps.append(f"Q1  = {q1}")
    steps.append(f"Median = {med}")
    steps.append(f"Q3  = {q3}")
    steps.append(f"Max = {maximum}")
    steps.append(f"Mean = {avg} ≈ {float(avg):.6f}")
    steps.append(f"Std Dev = {sd} ≈ {float(sd):.6f}")

    return {
        "branch": "statistics",
        "type": "summary",
        "steps": steps,
        "final_answer": {
            "count": n,
            "min": str(minimum),
            "q1": str(q1),
            "median": str(med),
            "q3": str(q3),
            "max": str(maximum),
            "mean": str(avg),
            "std_dev": str(sd),
        },
        "confidence": 0.97,
    }

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def solve(operation: str, **kwargs: Any) -> dict[str, Any]:
    """
    Compute a descriptive-statistics measure.

    Parameters
    ----------
    operation : str
        One of: mean, median, mode, variance, std_dev, range, iqr, summary.
    **kwargs
        - data: list[number]  (required for all operations)
        - population: bool (default True; for variance / std_dev)

    Returns
    -------
    dict
        Structured JSON-serialisable result.
    """
    if not isinstance(operation, str) or not operation.strip():
        return _error("Operation must be a non-empty string.")

    op = operation.strip().lower().replace(" ", "_")
    data_raw = kwargs.get("data")
    if data_raw is None:
        return _error("Missing required parameter 'data'.")
    vals = _validate_data(data_raw)
    if isinstance(vals, dict):
        return vals

    population = kwargs.get("population", True)

    try:
        dispatch = {
            "mean":     lambda: _compute_mean(vals),
            "median":   lambda: _compute_median(vals),
            "mode":     lambda: _compute_mode(vals),
            "variance": lambda: _compute_variance(vals, population),
            "var":      lambda: _compute_variance(vals, population),
            "std_dev":  lambda: _compute_std_dev(vals, population),
            "std":      lambda: _compute_std_dev(vals, population),
            "standard_deviation": lambda: _compute_std_dev(vals, population),
            "range":    lambda: _compute_range(vals),
            "iqr":      lambda: _compute_iqr(vals),
            "interquartile_range": lambda: _compute_iqr(vals),
            "summary":  lambda: _compute_summary(vals),
        }

        handler = dispatch.get(op)
        if handler is None:
            return _error(
                f"Unknown operation '{operation}'. "
                f"Supported: {', '.join(sorted(set(dispatch.keys())))}."
            )
        return handler()

    except Exception as exc:  # noqa: BLE001
        return _error(f"Statistics solver error: {exc}")
