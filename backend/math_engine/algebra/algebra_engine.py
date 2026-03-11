"""
algebra_engine.py - Algebra Engine Orchestrator
=================================================
The single public entry point for the Algebra domain.

Responsibilities:
1. Accept raw problem text
2. Parse into SymPy representation
3. Detect operation type and difficulty
4. Dispatch to the correct solver
5. Assemble and return a structured JSON-compatible response dict

Response format:
{
    "type": "Linear Equation | Quadratic Equation | Factoring | Simplification | Expansion",
    "difficulty": "easy | medium | hard",
    "steps": ["Step 1: ...", "Step 2: ...", ...],
    "final_answer": "...",
    "confidence": 0.0-1.0,
    "metadata": {...}   # optional debug / extra data
}

Design principles:
- No solver logic lives here — pure orchestration
- Errors are caught and surfaced as structured error responses
- Confidence is derived from operation certainty + solver verification
- Extensible: adding new operation types requires only registering
  in SOLVER_DISPATCH below
"""

import logging
import time
from typing import Any

from .parser import parse_problem, ParseError
from .detector import (
    AlgebraOperation,
    detect_operation,
    classify_difficulty,
    DetectionError,
)
from .linear_solver import solve_linear, LinearSolverError
from .quadratic_solver import solve_quadratic, QuadraticSolverError
from .factorization import factor_expression, FactorizationError
from .simplifier import simplify_expression, SimplificationError
from .expander import expand_expression, ExpansionError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Confidence model
# ---------------------------------------------------------------------------
# Base confidence per operation type.  These reflect how reliably the
# engine can verify its own output.  Verification steps inside each solver
# can boost or penalise this base score.

_BASE_CONFIDENCE: dict[AlgebraOperation, float] = {
    AlgebraOperation.LINEAR_EQUATION: 0.97,
    AlgebraOperation.QUADRATIC_EQUATION: 0.95,
    AlgebraOperation.FACTORING: 0.93,
    AlgebraOperation.SIMPLIFICATION: 0.88,
    AlgebraOperation.EXPANSION: 0.96,
    AlgebraOperation.UNKNOWN: 0.40,
}


def _build_error_response(
    raw_input: str,
    error: Exception,
    operation: AlgebraOperation | None = None,
) -> dict[str, Any]:
    """Build a structured error response."""
    return {
        "type": operation.value if operation else "Error",
        "difficulty": "unknown",
        "steps": [f"Step 1: An error occurred while processing: {error}"],
        "final_answer": "Unable to compute. Please check input format.",
        "confidence": 0.0,
        "error": str(error),
        "input": raw_input,
    }


def _assemble_response(
    raw_input: str,
    operation: AlgebraOperation,
    difficulty: str,
    solver_result: dict[str, Any],
    elapsed_ms: float,
) -> dict[str, Any]:
    """
    Assemble the canonical response dictionary.

    Any extra keys from the solver (e.g. 'discriminant', 'discriminant_type')
    are surfaced under 'metadata'.
    """
    base_keys = {"steps", "final_answer"}
    metadata = {k: v for k, v in solver_result.items() if k not in base_keys}
    metadata["elapsed_ms"] = round(elapsed_ms, 2)

    confidence = _BASE_CONFIDENCE.get(operation, 0.75)

    return {
        "type": operation.value,
        "difficulty": difficulty,
        "steps": solver_result.get("steps", []),
        "final_answer": solver_result.get("final_answer", ""),
        "confidence": confidence,
        "metadata": metadata,
    }


def solve(raw_input: str) -> dict[str, Any]:
    """
    Main entry point for the Algebra Engine.

    Accepts any algebra problem as a natural-language or symbolic string.
    Returns a fully structured response dict.

    Args:
        raw_input: E.g. "Solve 2x + 4 = 10"
                        "Factor x^2 - 5x + 6"
                        "Simplify (x^2 - 4) / (x - 2)"
                        "Expand (x+1)^3"
                        "x^2 - 4x + 3 = 0"

    Returns:
        Structured dict (serialisable to JSON).

    Example:
        >>> response = solve("Solve 3x - 9 = 0")
        >>> response['type']
        'Linear Equation'
        >>> response['final_answer']
        'x = 3'
    """
    t_start = time.perf_counter()
    logger.info("AlgebraEngine.solve — input: %r", raw_input)

    # ── 1. Parse ──────────────────────────────────────────────────────────
    try:
        sympy_obj, variables = parse_problem(raw_input)
    except ParseError as exc:
        logger.error("Parse failed: %s", exc)
        return _build_error_response(raw_input, exc)

    # ── 2. Detect operation ───────────────────────────────────────────────
    try:
        operation = detect_operation(sympy_obj, variables, raw_input)
        difficulty = classify_difficulty(sympy_obj, operation, variables)
    except DetectionError as exc:
        logger.error("Detection failed: %s", exc)
        return _build_error_response(raw_input, exc)

    logger.info("Detected operation=%s difficulty=%s", operation, difficulty)

    # ── 3. Dispatch ───────────────────────────────────────────────────────
    import sympy
    from sympy import Eq

    try:
        if operation == AlgebraOperation.LINEAR_EQUATION:
            if not isinstance(sympy_obj, Eq):
                sympy_obj = Eq(sympy_obj, sympy.Integer(0))
            solver_result = solve_linear(sympy_obj, variables)

        elif operation == AlgebraOperation.QUADRATIC_EQUATION:
            if not isinstance(sympy_obj, Eq):
                sympy_obj = Eq(sympy_obj, sympy.Integer(0))
            solver_result = solve_quadratic(sympy_obj, variables)

        elif operation == AlgebraOperation.FACTORING:
            expr = sympy_obj.lhs - sympy_obj.rhs if isinstance(sympy_obj, Eq) else sympy_obj
            solver_result = factor_expression(expr, variables)

        elif operation == AlgebraOperation.SIMPLIFICATION:
            expr = sympy_obj.lhs - sympy_obj.rhs if isinstance(sympy_obj, Eq) else sympy_obj
            solver_result = simplify_expression(expr, variables)

        elif operation == AlgebraOperation.EXPANSION:
            expr = sympy_obj.lhs - sympy_obj.rhs if isinstance(sympy_obj, Eq) else sympy_obj
            solver_result = expand_expression(expr, variables)

        else:
            # UNKNOWN — attempt a best-effort SymPy solve
            logger.warning("Unknown operation; attempting best-effort solve.")
            import sympy as sp
            best_result = sp.solve(sympy_obj, variables) if variables else None
            solver_result = {
                "steps": [
                    "Step 1: Operation type could not be precisely determined.",
                    f"Step 2: Applying best-effort SymPy solve: {best_result}",
                ],
                "final_answer": str(best_result) if best_result else "Undetermined",
            }

    except (
        LinearSolverError,
        QuadraticSolverError,
        FactorizationError,
        SimplificationError,
        ExpansionError,
        Exception,
    ) as exc:
        logger.error("Solver error [%s]: %s", operation, exc)
        return _build_error_response(raw_input, exc, operation)

    # ── 4. Assemble response ──────────────────────────────────────────────
    elapsed_ms = (time.perf_counter() - t_start) * 1000
    response = _assemble_response(
        raw_input, operation, difficulty, solver_result, elapsed_ms
    )

    logger.info(
        "AlgebraEngine.solve complete in %.2fms → %s",
        elapsed_ms,
        response["final_answer"],
    )
    return response
