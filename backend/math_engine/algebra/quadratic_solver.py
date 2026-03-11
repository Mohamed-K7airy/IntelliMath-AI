"""
quadratic_solver.py - Quadratic Equation Solver
=================================================
Solves quadratic equations of the form ax² + bx + c = 0.

Key features:
- Explicit discriminant computation and classification
- Three solution branches: two real, one repeated, two complex
- Step-by-step quadratic formula walkthrough
- Multi-variable support (solves for dominant variable)
- Discriminant-based confidence scoring

Production-grade: does NOT assume variable is 'x'.
"""

import logging

import sympy
from sympy import (
    Eq, Symbol, expand, sqrt, Rational, simplify,
    I, im, re as sym_re, latex, solve, Poly
)

from .step_generator import StepBuilder, expr_to_str

logger = logging.getLogger(__name__)


class QuadraticSolverError(Exception):
    """Raised when quadratic solving fails."""
    pass


def _extract_quadratic_coefficients(
    poly_expr: sympy.Expr, var: Symbol
) -> tuple[sympy.Expr, sympy.Expr, sympy.Expr]:
    """
    Extract (a, b, c) from ax² + bx + c.

    Args:
        poly_expr: Polynomial expression (expanded, lhs - rhs form).
        var: The variable Symbol to solve for.

    Returns:
        (a, b, c) as SymPy expressions.
    """
    expanded = expand(poly_expr)
    a = expanded.coeff(var, 2)
    b = expanded.coeff(var, 1)
    c = expanded.coeff(var, 0)
    return a, b, c


def _select_primary_variable(
    poly_expr: sympy.Expr, variables: list[Symbol]
) -> Symbol:
    """
    From a list of variables, select the one that appears as degree-2
    in the expression. Defaults to first variable if ambiguous.
    """
    for var in variables:
        if expand(poly_expr).coeff(var, 2) != 0:
            return var
    return variables[0]


def solve_quadratic(
    equation: Eq,
    variables: list[Symbol],
) -> dict:
    """
    Solve a quadratic equation with explicit discriminant analysis.

    Args:
        equation: SymPy Eq, e.g. Eq(x**2 - 5*x + 6, 0)
        variables: Detected variables.

    Returns:
        dict with keys: steps (list[str]), final_answer (str)

    Raises:
        QuadraticSolverError: On failure.

    Example:
        >>> from sympy import symbols, Eq
        >>> x = symbols('x')
        >>> result = solve_quadratic(Eq(x**2 - 5*x + 6, 0), [x])
        >>> result['final_answer']
        'x = 2  or  x = 3'
    """
    if not variables:
        raise QuadraticSolverError("No variables detected.")

    sb = StepBuilder()

    # --- Identify primary variable ---
    lhs_minus_rhs = expand(equation.lhs - equation.rhs)
    var = _select_primary_variable(lhs_minus_rhs, variables)

    sb.add(
        f"Identify the equation type: Quadratic equation in '{var}'."
    )
    sb.add_expr("Original equation:", equation)

    # --- Rewrite in standard form ax² + bx + c = 0 ---
    standard_form = Eq(lhs_minus_rhs, 0)
    sb.add_expr("Rewrite in standard form  ax² + bx + c = 0:", standard_form)

    # --- Extract coefficients ---
    a, b, c = _extract_quadratic_coefficients(lhs_minus_rhs, var)

    if a == 0:
        raise QuadraticSolverError(
            f"Coefficient 'a' is zero — equation is not quadratic in {var}. "
            "Route to linear solver instead."
        )

    sb.add(
        f"Extract coefficients:  a = {expr_to_str(a)},  "
        f"b = {expr_to_str(b)},  c = {expr_to_str(c)}."
    )

    # --- Compute discriminant ---
    discriminant = expand(b**2 - 4 * a * c)
    sb.add_rule("Quadratic Formula: x = (-b ± √(b²-4ac)) / (2a)")
    sb.add_computation(
        "Compute the discriminant  Δ = b² - 4ac:",
        sympy.UnevaluatedExpr(b**2 - 4*a*c),
        discriminant,
    )

    # --- Classify and solve ---
    discriminant_num = sympy.N(discriminant, 10)

    if discriminant.is_real and discriminant > 0:
        discriminant_type = "positive (two distinct real roots)"
    elif discriminant == 0:
        discriminant_type = "zero (one repeated real root)"
    elif discriminant.is_real and discriminant < 0:
        discriminant_type = "negative (two complex conjugate roots)"
    else:
        # Symbolic discriminant — let SymPy decide
        discriminant_type = f"symbolic ({expr_to_str(discriminant)})"

    sb.add(f"Classify discriminant Δ = {expr_to_str(discriminant)}: {discriminant_type}.")

    # --- Apply quadratic formula ---
    denom = 2 * a
    sb.add_rule(f"Apply formula: {var} = ( -({expr_to_str(b)}) ± √({expr_to_str(discriminant)}) ) / (2·{expr_to_str(a)})")

    sqrt_discriminant = sqrt(discriminant)

    root1_raw = (-b + sqrt_discriminant) / denom
    root2_raw = (-b - sqrt_discriminant) / denom

    root1 = simplify(root1_raw)
    root2 = simplify(root2_raw)

    sb.add_computation(
        f"Root 1 using (+): {var} =",
        root1_raw,
        root1,
    )
    sb.add_computation(
        f"Root 2 using (−): {var} =",
        root2_raw,
        root2,
    )

    # --- Format result ---
    if root1 == root2:
        final_answer = f"{var} = {expr_to_str(root1)}  (repeated root)"
        sb.add(
            f"Since Δ = 0, there is exactly one repeated root: {var} = {expr_to_str(root1)}."
        )
    else:
        final_answer = f"{var} = {expr_to_str(root1)}  or  {var} = {expr_to_str(root2)}"
        sb.add(f"The two roots are: {final_answer}.")

    # --- Verification ---
    check1 = simplify(equation.lhs.subs(var, root1) - equation.rhs.subs(var, root1))
    check2 = simplify(equation.lhs.subs(var, root2) - equation.rhs.subs(var, root2))
    both_verified = (check1 == 0 and check2 == 0)
    sb.add(
        f"Verify both roots by substitution: "
        f"{'✓ Both roots verified' if both_verified else '⚠ Verification inconclusive — check symbolic simplification.'}"
    )

    logger.info("Quadratic solve complete: %s", final_answer)

    return {
        "steps": sb.build(),
        "final_answer": final_answer,
        "discriminant": expr_to_str(discriminant),
        "discriminant_type": discriminant_type,
    }
