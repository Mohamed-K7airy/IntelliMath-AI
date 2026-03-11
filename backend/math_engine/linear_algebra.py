"""
math_engine/linear_algebra.py

Production-ready linear-algebra engine for IntelliMath.
Supports: matrix operations (add, subtract, multiply, scalar multiply,
transpose, power), determinant, inverse, and solving linear systems.
"""

from __future__ import annotations

from typing import Any

import sympy as sp
from sympy import Matrix, Rational, eye


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _error(msg: str) -> dict[str, Any]:
    return {"error": str(msg), "confidence": 0.0}


def _to_matrix(data: Any) -> Matrix:
    """Convert list-of-lists (or already a Matrix) to a SymPy Matrix."""
    if isinstance(data, Matrix):
        return data
    if isinstance(data, (list, tuple)):
        return Matrix(data)
    raise TypeError(f"Cannot convert {type(data).__name__} to Matrix.")


def _validate_matrix_input(data: Any, name: str = "matrix") -> Matrix | dict:
    """Return a Matrix or an error dict."""
    try:
        return _to_matrix(data)
    except (TypeError, ValueError) as exc:
        return _error(f"Invalid {name}: {exc}")


def _matrix_str(m: Matrix) -> str:
    return str(m.tolist())

# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------

def _determinant(m: Matrix) -> dict[str, Any]:
    steps: list[str] = []
    if m.rows != m.cols:
        return _error("Determinant requires a square matrix.")
    steps.append(f"Input matrix ({m.rows}x{m.cols}): {_matrix_str(m)}")
    det = m.det()
    steps.append(f"Compute determinant using Leibniz / cofactor expansion.")
    steps.append(f"det = {det}")
    return {
        "branch": "linear_algebra",
        "type": "determinant",
        "steps": steps,
        "final_answer": str(det),
        "confidence": 0.98,
    }


def _inverse(m: Matrix) -> dict[str, Any]:
    steps: list[str] = []
    if m.rows != m.cols:
        return _error("Inverse requires a square matrix.")
    steps.append(f"Input matrix ({m.rows}x{m.cols}): {_matrix_str(m)}")
    det = m.det()
    steps.append(f"Compute determinant: {det}")
    if det == 0:
        return _error("Matrix is singular (det = 0); inverse does not exist.")
    inv = m.inv()
    steps.append(f"Compute inverse via adjugate / Gauss-Jordan elimination.")
    steps.append(f"Inverse: {_matrix_str(inv)}")
    # Verification
    identity = m * inv
    steps.append(f"Verification A·A⁻¹ = I: {_matrix_str(sp.simplify(identity))}")
    return {
        "branch": "linear_algebra",
        "type": "inverse",
        "steps": steps,
        "final_answer": _matrix_str(inv),
        "confidence": 0.97,
    }


def _add(a: Matrix, b: Matrix) -> dict[str, Any]:
    steps: list[str] = []
    if a.shape != b.shape:
        return _error(
            f"Shape mismatch for addition: {a.shape} vs {b.shape}."
        )
    steps.append(f"A = {_matrix_str(a)}")
    steps.append(f"B = {_matrix_str(b)}")
    result = a + b
    steps.append(f"A + B = {_matrix_str(result)}")
    return {
        "branch": "linear_algebra",
        "type": "addition",
        "steps": steps,
        "final_answer": _matrix_str(result),
        "confidence": 0.99,
    }


def _subtract(a: Matrix, b: Matrix) -> dict[str, Any]:
    steps: list[str] = []
    if a.shape != b.shape:
        return _error(
            f"Shape mismatch for subtraction: {a.shape} vs {b.shape}."
        )
    steps.append(f"A = {_matrix_str(a)}")
    steps.append(f"B = {_matrix_str(b)}")
    result = a - b
    steps.append(f"A - B = {_matrix_str(result)}")
    return {
        "branch": "linear_algebra",
        "type": "subtraction",
        "steps": steps,
        "final_answer": _matrix_str(result),
        "confidence": 0.99,
    }


def _multiply(a: Matrix, b: Matrix) -> dict[str, Any]:
    steps: list[str] = []
    if a.cols != b.rows:
        return _error(
            f"Cannot multiply: A is {a.rows}x{a.cols}, B is {b.rows}x{b.cols}. "
            f"A.cols must equal B.rows."
        )
    steps.append(f"A ({a.rows}x{a.cols}) = {_matrix_str(a)}")
    steps.append(f"B ({b.rows}x{b.cols}) = {_matrix_str(b)}")
    result = a * b
    steps.append(f"A × B ({result.rows}x{result.cols}) = {_matrix_str(result)}")
    return {
        "branch": "linear_algebra",
        "type": "multiplication",
        "steps": steps,
        "final_answer": _matrix_str(result),
        "confidence": 0.98,
    }


def _scalar_multiply(m: Matrix, scalar: Any) -> dict[str, Any]:
    steps: list[str] = []
    s = sp.sympify(scalar)
    steps.append(f"Matrix = {_matrix_str(m)}")
    steps.append(f"Scalar = {s}")
    result = m * s
    steps.append(f"Result = {_matrix_str(result)}")
    return {
        "branch": "linear_algebra",
        "type": "scalar_multiplication",
        "steps": steps,
        "final_answer": _matrix_str(result),
        "confidence": 0.99,
    }


def _transpose(m: Matrix) -> dict[str, Any]:
    steps: list[str] = []
    steps.append(f"Input matrix ({m.rows}x{m.cols}): {_matrix_str(m)}")
    result = m.T
    steps.append(f"Transposed ({result.rows}x{result.cols}): {_matrix_str(result)}")
    return {
        "branch": "linear_algebra",
        "type": "transpose",
        "steps": steps,
        "final_answer": _matrix_str(result),
        "confidence": 0.99,
    }


def _power(m: Matrix, n: int) -> dict[str, Any]:
    steps: list[str] = []
    if m.rows != m.cols:
        return _error("Matrix power requires a square matrix.")
    steps.append(f"Input matrix ({m.rows}x{m.cols}): {_matrix_str(m)}")
    steps.append(f"Exponent: {n}")
    result = m ** n
    steps.append(f"Result: {_matrix_str(result)}")
    return {
        "branch": "linear_algebra",
        "type": "power",
        "steps": steps,
        "final_answer": _matrix_str(result),
        "confidence": 0.97,
    }


def _solve_system(coefficients: Matrix, constants: Matrix) -> dict[str, Any]:
    """Solve A·x = b via Gaussian elimination / LU decomposition."""
    steps: list[str] = []
    steps.append(f"Coefficient matrix A ({coefficients.rows}x{coefficients.cols}): "
                 f"{_matrix_str(coefficients)}")
    steps.append(f"Constants vector b: {_matrix_str(constants)}")

    if coefficients.rows != constants.rows:
        return _error(
            "Dimension mismatch: A rows must equal b rows."
        )

    # Build augmented matrix for row-reduction
    augmented = coefficients.row_join(constants)
    steps.append(f"Augmented matrix [A|b]: {_matrix_str(augmented)}")

    rref, pivots = augmented.rref()
    steps.append(f"Row-reduced echelon form: {_matrix_str(rref)}")

    n = coefficients.cols
    if len(pivots) < n:
        if any(
            rref[i, -1] != 0 and all(rref[i, j] == 0 for j in range(n))
            for i in range(rref.rows)
        ):
            return _error("System is inconsistent (no solution).")
        return {
            "branch": "linear_algebra",
            "type": "linear_system",
            "steps": steps + ["System has infinitely many solutions."],
            "final_answer": "infinitely many solutions",
            "confidence": 0.90,
        }

    try:
        solution = coefficients.solve(constants)
    except Exception as exc:
        return _error(f"Could not solve system: {exc}")

    sol_list = solution.tolist()
    steps.append(f"Solution vector x: {sol_list}")
    # Verification
    check = coefficients * solution
    steps.append(f"Verification A·x = {_matrix_str(check)} (should equal b)")

    return {
        "branch": "linear_algebra",
        "type": "linear_system",
        "steps": steps,
        "final_answer": str(sol_list),
        "confidence": 0.97,
    }

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_OPERATIONS = {
    "determinant":           lambda kw: _determinant(_to_matrix(kw["matrix"])),
    "det":                   lambda kw: _determinant(_to_matrix(kw["matrix"])),
    "inverse":               lambda kw: _inverse(_to_matrix(kw["matrix"])),
    "inv":                   lambda kw: _inverse(_to_matrix(kw["matrix"])),
    "add":                   lambda kw: _add(_to_matrix(kw["a"]), _to_matrix(kw["b"])),
    "subtract":              lambda kw: _subtract(_to_matrix(kw["a"]), _to_matrix(kw["b"])),
    "sub":                   lambda kw: _subtract(_to_matrix(kw["a"]), _to_matrix(kw["b"])),
    "multiply":              lambda kw: _multiply(_to_matrix(kw["a"]), _to_matrix(kw["b"])),
    "mul":                   lambda kw: _multiply(_to_matrix(kw["a"]), _to_matrix(kw["b"])),
    "scalar_multiply":       lambda kw: _scalar_multiply(_to_matrix(kw["matrix"]), kw["scalar"]),
    "transpose":             lambda kw: _transpose(_to_matrix(kw["matrix"])),
    "power":                 lambda kw: _power(_to_matrix(kw["matrix"]), int(kw["n"])),
    "solve_system":          lambda kw: _solve_system(
                                  _to_matrix(kw["coefficients"]),
                                  _to_matrix(kw["constants"]),
                              ),
    "system":                lambda kw: _solve_system(
                                  _to_matrix(kw["coefficients"]),
                                  _to_matrix(kw["constants"]),
                              ),
}


def solve(operation: str, **kwargs: Any) -> dict[str, Any]:
    """
    Solve a linear-algebra problem.

    Parameters
    ----------
    operation : str
        One of: determinant, inverse, add, subtract, multiply,
        scalar_multiply, transpose, power, solve_system.
    **kwargs
        Operation-specific parameters.
        - determinant / inverse / transpose: ``matrix=[[...], ...]``
        - add / subtract / multiply: ``a=[[...]], b=[[...]]``
        - scalar_multiply: ``matrix=[[...]], scalar=<value>``
        - power: ``matrix=[[...]], n=<int>``
        - solve_system: ``coefficients=[[...]], constants=[[...]]``

    Returns
    -------
    dict
        Structured JSON-serialisable result.
    """
    if not isinstance(operation, str) or not operation.strip():
        return _error("Operation must be a non-empty string.")

    op_key = operation.strip().lower().replace(" ", "_")

    handler = _OPERATIONS.get(op_key)
    if handler is None:
        return _error(
            f"Unknown operation '{operation}'. "
            f"Supported: {', '.join(sorted(set(_OPERATIONS.keys())))}."
        )

    try:
        return handler(kwargs)
    except KeyError as exc:
        return _error(f"Missing required parameter: {exc}")
    except (TypeError, ValueError) as exc:
        return _error(f"Invalid input: {exc}")
    except Exception as exc:  # noqa: BLE001
        return _error(f"Linear algebra solver error: {exc}")
