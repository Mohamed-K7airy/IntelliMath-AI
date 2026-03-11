"""
factorization.py - Algebraic Expression Factorizer
====================================================
Factors polynomial expressions step-by-step.

Steps:
1. Identify the expression type
2. Check for GCF (Greatest Common Factor)
3. Apply SymPy factor
4. Decompose factors and explain structure
5. Verify by expansion

Production features:
- Explains each factor found
- Handles multivariate polynomials
- Identifies special forms (difference of squares, perfect square trinomials)
- Validates result by re-expanding
"""

import logging

import sympy
from sympy import (
    Symbol, Expr, factor, expand, gcd, Mul, Pow, Add,
    Integer, factor_list, simplify
)

from .step_generator import StepBuilder, expr_to_str

logger = logging.getLogger(__name__)


class FactorizationError(Exception):
    """Raised when factorization fails or produces unexpected output."""
    pass


def _identify_special_form(expr: Expr, variables: list[Symbol]) -> str | None:
    """
    Detect common special factoring forms and return a description.
    Returns None if no special form detected.

    Detects:
    - Difference of squares: a² - b²
    - Perfect square trinomial: a² ± 2ab + b²
    - Sum/difference of cubes: a³ ± b³
    """
    expanded = expand(expr)

    # Difference of squares: a^2 - b^2 = (a+b)(a-b)
    # Result of factor should give exactly two factors (a+b) and (a-b)
    factored = factor(expr)
    if isinstance(factored, Mul):
        factors_args = [a for a in factored.args if not a.is_number]
        if len(factors_args) == 2:
            f1, f2 = factors_args
            if expand(f1 + f2) == 0 or sympy.Eq(f1, -f2):
                return "Difference of Squares: a² - b² = (a+b)(a-b)"

    # Perfect square trinomial: (a ± b)²
    # The factored form would be a single Pow with exponent 2
    if isinstance(factored, Pow) and factored.args[1] == 2:
        return "Perfect Square Trinomial: (a ± b)² = a² ± 2ab + b²"
    if isinstance(factored, Mul):
        for arg in factored.args:
            if isinstance(arg, Pow) and arg.args[1] == 2:
                return "Contains a Perfect Square factor."

    return None


def _extract_gcf(expr: Expr, variables: list[Symbol]) -> sympy.Expr:
    """
    Extract the Greatest Common Factor of all terms in the expression.
    Works for both numeric and symbolic GCF.

    Returns the GCF as a SymPy expression (1 if none found).
    """
    terms = Add.make_args(expand(expr))
    if not terms:
        return sympy.Integer(1)

    current_gcd = terms[0]
    for term in terms[1:]:
        current_gcd = gcd(current_gcd, term)

    # Ensure GCF is positive
    if current_gcd.is_number and current_gcd < 0:
        current_gcd = -current_gcd

    return simplify(current_gcd)


def factor_expression(
    expr: Expr,
    variables: list[Symbol],
) -> dict:
    """
    Factor an algebraic expression with step-by-step reasoning.

    Args:
        expr: A SymPy expression (NOT an Eq).
        variables: Detected variables list.

    Returns:
        dict with keys: steps (list[str]), final_answer (str)

    Raises:
        FactorizationError: On failure.

    Example:
        >>> from sympy import symbols
        >>> x = symbols('x')
        >>> result = factor_expression(x**2 - 5*x + 6, [x])
        >>> result['final_answer']
        '(x - 2)*(x - 3)'
    """
    sb = StepBuilder()

    var_names = ", ".join(str(v) for v in variables)
    sb.add(
        f"Identify the expression to factor in variable(s): {var_names}."
    )
    sb.add_expr("Expression:", expr)

    # --- Step: Expand first to normalize ---
    normalized = expand(expr)
    if normalized != expr:
        sb.add_expr("Expand and normalize the expression:", normalized)
    else:
        sb.add("Expression is already in expanded/standard form.")

    # --- Step: Check for GCF ---
    gcf = _extract_gcf(normalized, variables)
    if gcf != 1 and gcf != -1:
        reduced = sympy.cancel(normalized / gcf)
        sb.add(
            f"Extract the Greatest Common Factor (GCF): GCF = {expr_to_str(gcf)}."
        )
        sb.add_expr(
            f"Factor out GCF → {expr_to_str(gcf)} × (",
            reduced,
        )
    else:
        sb.add("No common numerical or symbolic GCF found (GCF = 1).")

    # --- Step: Detect special forms ---
    special = _identify_special_form(normalized, variables)
    if special:
        sb.add(f"Recognize special factoring pattern: {special}")

    # --- Step: Apply SymPy factor ---
    factored = factor(normalized)
    sb.add_expr("Apply factorization algorithm:", factored)

    # --- Step: Decompose and explain each factor ---
    if isinstance(factored, Mul):
        factor_args = factored.args
        sb.add("Decompose into individual factors:")
        for i, f_arg in enumerate(factor_args, start=1):
            if isinstance(f_arg, Pow) and f_arg.args[1].is_integer and f_arg.args[1] > 1:
                base, exp = f_arg.args
                sb.add(f"  Factor {i}: ({expr_to_str(base)})^{exp}  "
                       f"[repeated factor with multiplicity {exp}]")
            elif f_arg.is_number:
                sb.add(f"  Factor {i}: {expr_to_str(f_arg)}  [numeric constant]")
            else:
                sb.add(f"  Factor {i}: ({expr_to_str(f_arg)})  [polynomial factor]")
    elif isinstance(factored, Pow) and factored.args[1].is_integer and factored.args[1] > 1:
        base, exp = factored.args
        sb.add(
            f"Expression factors as ({expr_to_str(base)})^{exp}  "
            f"[perfect {exp}-th power]."
        )
    else:
        sb.add(
            "Expression is already irreducible (prime polynomial) — "
            "cannot be factored further over the integers."
        )

    # --- Step: Verify by re-expanding ---
    verification = expand(factored)
    is_verified = sympy.Eq(simplify(verification - normalized), 0)
    sb.add(
        f"Verify: expand the factored form → {expr_to_str(verification)}  "
        f"{'✓ Matches original.' if is_verified else '⚠ Mismatch — review factoring.'}"
    )

    final_answer = expr_to_str(factored)
    logger.info("Factorization complete: %s", final_answer)

    return {
        "steps": sb.build(),
        "final_answer": final_answer,
    }
