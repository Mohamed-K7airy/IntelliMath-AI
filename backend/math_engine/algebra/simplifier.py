"""
simplifier.py - Algebraic Expression Simplifier
================================================
Simplifies algebraic expressions and explains each transformation.

Strategy:
1. Identify what "simplification" means for the given expression
   (combine like terms, cancel common factors, reduce fractions, etc.)
2. Apply SymPy simplification pipeline stage-by-stage
3. Compare each stage to show the transformations
4. Explain what changed and why

Handles:
- Polynomial simplification (combine like terms)
- Rational expressions (cancel common factors)
- Trigonometric / exponential expressions (via SymPy simplify)
- Nested expressions

Production-grade: explains transformations—not just the result.
"""

import logging

import sympy
from sympy import (
    Symbol, Expr, simplify, expand, cancel, radsimp,
    trigsimp, powsimp, factor, collect, Add, Mul, Rational,
    together, apart, nsimplify
)

from .step_generator import StepBuilder, expr_to_str

logger = logging.getLogger(__name__)


class SimplificationError(Exception):
    """Raised when simplification fails."""
    pass


def _is_rational_expression(expr: Expr, variables: list[Symbol]) -> bool:
    """Check if expression contains division by a variable-containing term."""
    return any(
        (isinstance(arg, sympy.Pow) and arg.args[1].is_negative)
        for arg in sympy.preorder_traversal(expr)
        if hasattr(arg, 'args')
    )


def _count_terms(expr: Expr) -> int:
    """Count the number of top-level additive terms."""
    return len(Add.make_args(expand(expr)))


def _count_ops(expr: Expr) -> int:
    """Count total number of operations (depth proxy)."""
    return sympy.count_ops(expr)


def simplify_expression(
    expr: Expr,
    variables: list[Symbol],
) -> dict:
    """
    Simplify an algebraic expression with step-by-step explanation.

    Args:
        expr: A SymPy expression (NOT an Eq).
        variables: Detected variables list.

    Returns:
        dict with keys: steps (list[str]), final_answer (str)

    Raises:
        SimplificationError: On failure.

    Example:
        >>> from sympy import symbols
        >>> x = symbols('x')
        >>> result = simplify_expression((x**2 - 4) / (x - 2), [x])
        >>> result['final_answer']
        'x + 2'
    """
    sb = StepBuilder()
    var_names = ", ".join(str(v) for v in variables)

    sb.add(
        f"Identify the expression to simplify in variable(s): {var_names}."
    )
    sb.add_expr("Original expression:", expr)
    sb.add(f"Complexity before simplification: {_count_ops(expr)} operations, "
           f"{_count_terms(expr)} top-level term(s).")

    simplified = expr
    transformations_applied = []

    # ---- Stage 1: Expand if compound ----
    expanded = expand(expr)
    if _count_ops(expanded) < _count_ops(expr):
        simplified = expanded
        transformations_applied.append("expand")
        sb.add_expr("Stage 1 — Expand compound terms:", expanded)
    else:
        sb.add("Stage 1 — Expansion does not reduce complexity; skip.")

    # ---- Stage 2: Cancel common factors (for rational exprs) ----
    if _is_rational_expression(simplified, variables):
        cancelled = cancel(simplified)
        if cancelled != simplified:
            transformations_applied.append("cancel")
            sb.add_computation(
                "Stage 2 — Cancel common factors in numerator/denominator:",
                simplified,
                cancelled,
            )
            simplified = cancelled
        else:
            sb.add("Stage 2 — No common factors to cancel in rational expression.")
    else:
        sb.add("Stage 2 — Not a rational expression; cancel step skipped.")

    # ---- Stage 3: Collect like terms per variable ----
    if variables:
        collected = collect(expand(simplified), variables)
        if _count_ops(collected) < _count_ops(simplified):
            transformations_applied.append("collect")
            sb.add_computation(
                f"Stage 3 — Collect like terms for {var_names}:",
                simplified,
                collected,
            )
            simplified = collected
        else:
            sb.add("Stage 3 — Like terms already collected.")

    # ---- Stage 4: Apply general SymPy simplify ----
    final_simplified = simplify(simplified)
    if _count_ops(final_simplified) < _count_ops(simplified):
        transformations_applied.append("simplify")
        sb.add_computation(
            "Stage 4 — Apply algebraic simplification rules:",
            simplified,
            final_simplified,
        )
        simplified = final_simplified
    else:
        sb.add("Stage 4 — No further algebraic simplification possible.")

    # ---- Stage 5: Factor if it reduces form ----
    factored = factor(simplified)
    if _count_ops(factored) < _count_ops(simplified):
        transformations_applied.append("factor")
        sb.add_computation(
            "Stage 5 — Factor the result for compactness:",
            simplified,
            factored,
        )
        simplified = factored
    else:
        sb.add("Stage 5 — Factored form is not more compact; keep current form.")

    # ---- Summary ----
    if transformations_applied:
        sb.add(
            f"Transformations applied: {', '.join(transformations_applied)}."
        )
    else:
        sb.add("Expression is already in its simplest form.")

    sb.add(
        f"Complexity after simplification: {_count_ops(simplified)} operations, "
        f"{_count_terms(simplified)} top-level term(s)."
    )

    final_answer = expr_to_str(simplified)
    logger.info("Simplification complete: %s", final_answer)

    return {
        "steps": sb.build(),
        "final_answer": final_answer,
    }
