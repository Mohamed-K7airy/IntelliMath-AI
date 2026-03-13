"""
detector.py - Algebra Operation Type Detector
===============================================
Analyses a parsed SymPy expression to determine *what* algebraic
operation is needed: solving a linear/quadratic equation,
factoring, simplifying, or expanding an expression.

Design principle: the detector is pure logic — it does not
call solvers, only inspects expression structure.
"""

import logging
import re
from enum import Enum, auto
from typing import Optional

import sympy
from sympy import Eq, Poly, degree, Symbol, Expr

logger = logging.getLogger(__name__)


class AlgebraOperation(str, Enum):
    """Canonical operation categories for the Algebra Engine."""
    LINEAR_EQUATION = "Linear Equation"
    QUADRATIC_EQUATION = "Quadratic Equation"
    FACTORING = "Factoring"
    SIMPLIFICATION = "Simplification"
    EXPANSION = "Expansion"
    UNKNOWN = "Unknown"


class DetectionError(Exception):
    """Raised when the detector cannot classify an expression."""
    pass


# ---------------------------------------------------------------------------
# Keyword sets used for raw-text hinting
# ---------------------------------------------------------------------------
_FACTOR_KEYWORDS = frozenset(["factor", "factorise", "factorize"])
_EXPAND_KEYWORDS = frozenset(["expand", "distribute", "foil"])
_SIMPLIFY_KEYWORDS = frozenset(["simplify", "reduce", "simplification"])
_SOLVE_KEYWORDS = frozenset(["solve", "find", "calculate", "determine"])


def _hint_from_raw(raw_input: str) -> Optional[AlgebraOperation]:
    """
    Look for explicit operation keywords in the raw user text.
    Returns an operation hint or None if unclear.
    """
    lower = raw_input.lower()
    if any(k in lower for k in _FACTOR_KEYWORDS):
        return AlgebraOperation.FACTORING
    if any(k in lower for k in _EXPAND_KEYWORDS):
        return AlgebraOperation.EXPANSION
    if any(k in lower for k in _SIMPLIFY_KEYWORDS):
        return AlgebraOperation.SIMPLIFICATION
    return None


def _poly_degree(expr: Expr, variables: list[Symbol]) -> Optional[int]:
    """
    Compute polynomial degree of expr over detected variables.
    Returns None if expression is not a polynomial.
    """
    if not variables:
        return None
    try:
        # Use the first detected variable for single-var analysis
        # For multi-var, compute total degree
        if len(variables) == 1:
            poly = Poly(expr, variables[0])
            return poly.degree()
        else:
            # Total degree across all variables
            poly = Poly(expr, *variables)
            return poly.total_degree()
    except (sympy.PolynomialError, sympy.GeneratorsNeeded):
        return None


def _is_expanded(expr: Expr) -> bool:
    """
    Heuristic: an expression that is already in expanded form
    (flat sum of monomials) is a candidate for simplification,
    not expansion.
    """
    expanded = sympy.expand(expr)
    return sympy.simplify(expr - expanded) == 0


def detect_operation(
    sympy_obj: sympy.Basic,
    variables: list[Symbol],
    raw_input: str = "",
) -> AlgebraOperation:
    """
    Determine the algebraic operation required.

    Priority order:
    1. Keyword hints from raw text
    2. If it's an Eq → inspect degree → linear or quadratic
    3. If it's a bare expression → factor / simplify / expand

    Args:
        sympy_obj: Parsed SymPy object (Eq or Expr).
        variables: Detected variables.
        raw_input: Original user text for keyword analysis.

    Returns:
        AlgebraOperation enum value.
    """
    # --- Step 1: Keyword hint ---
    hint = _hint_from_raw(raw_input) if raw_input else None

    # --- Step 2a: It's an equation ---
    if isinstance(sympy_obj, Eq):
        lhs = sympy_obj.lhs
        rhs = sympy_obj.rhs
        # Combine into lhs - rhs for degree check
        diff_expr = sympy.expand(lhs - rhs)
        deg = _poly_degree(diff_expr, variables)

        if deg is None:
            logger.warning(
                "Non-polynomial equation detected: %s", sympy_obj
            )
            # If keyword says simplify, respect it
            return hint if hint else AlgebraOperation.UNKNOWN

        if deg <= 1:
            return AlgebraOperation.LINEAR_EQUATION
        elif deg == 2:
            return AlgebraOperation.QUADRATIC_EQUATION
        else:
            # Higher degree — still solvable, but out of current scope
            logger.info("Degree-%d equation — routing as quadratic (fallback).", deg)
            return AlgebraOperation.QUADRATIC_EQUATION

    # --- Step 2b: Bare expression ---
    expr = sympy_obj  # type: sympy.Expr

    # Keyword takes priority for expressions
    if hint is not None:
        logger.debug("Keyword hint resolved operation to: %s", hint)
        return hint

    # Heuristic: if expression contains unexpanded products like (x+1)(x-1),
    # it's a candidate for expansion
    # We check if expanding changes the form meaningfully
    expanded = sympy.expand(expr)
    if not sympy.Eq(expr, expanded):  # expression changes upon expansion
        # If original had explicit Mul of Add nodes → it's unexpanded
        has_mul_of_add = any(
            isinstance(arg, sympy.Add)
            for factor in sympy.Mul.make_args(expr)
            for arg in [factor]
            if isinstance(factor, sympy.Add)
        )
        if has_mul_of_add or _looks_expandable(expr):
            return AlgebraOperation.EXPANSION

    # Check if factorable: factoring changes form AND has non-trivial factors
    factored = sympy.factor(expr)
    if not sympy.Eq(expr, factored) and isinstance(factored, sympy.Mul):
        return AlgebraOperation.FACTORING

    # Default: simplification
    return AlgebraOperation.SIMPLIFICATION


def _looks_expandable(expr: sympy.Expr) -> bool:
    """
    Check if top-level expression is a product that contains sums.
    E.g. (x+1)*(x-2) → True
    """
    if isinstance(expr, sympy.Mul):
        return any(isinstance(arg, sympy.Add) for arg in expr.args)
    if isinstance(expr, sympy.Pow):
        base, exp = expr.args
        return isinstance(base, sympy.Add) and exp.is_integer and exp > 1
    return False


def classify_difficulty(
    sympy_obj: sympy.Basic,
    operation: AlgebraOperation,
    variables: list[Symbol],
) -> str:
    """
    Assign a difficulty rating based on structural complexity.

    Returns:
        "easy" | "medium" | "hard"
    """
    expr = sympy_obj.lhs if isinstance(sympy_obj, Eq) else sympy_obj
    diff_expr = (
        sympy.expand(sympy_obj.lhs - sympy_obj.rhs)
        if isinstance(sympy_obj, Eq)
        else expr
    )

    num_terms = len(sympy.Add.make_args(sympy.expand(diff_expr)))
    num_vars = len(variables)
    deg = _poly_degree(diff_expr, variables) or 1

    # Scoring heuristic
    score = num_vars + deg + (num_terms // 3)

    if score <= 2:
        return "easy"
    elif score <= 5:
        return "medium"
    else:
        return "hard"
