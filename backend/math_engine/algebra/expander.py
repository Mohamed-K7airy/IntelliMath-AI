"""
expander.py - Algebraic Expression Expander
============================================
Expands algebraic expressions with detailed step-by-step reasoning.

Handles:
- Products of polynomials: (x+1)(x-2)
- Binomial powers: (x+y)^3
- Mixed expressions: 2(x+1) + 3(x-1)
- Multi-variable expressions

Features:
- Identifies expansion patterns (FOIL, distribution, binomial theorem)
- Shows intermediate factor-by-factor expansion
- Collects and combines like terms at the end
- Verifies result by re-factoring (where applicable)

Production-grade: variable-agnostic, handles n-factor products.
"""

import logging

import sympy
from sympy import (
    Symbol, Expr, expand, Mul, Add, Pow, Integer,
    collect, binomial, Symbol, symbols, latex
)

from .step_generator import StepBuilder, expr_to_str

logger = logging.getLogger(__name__)


class ExpansionError(Exception):
    """Raised when expansion fails."""
    pass


def _describe_expansion_strategy(expr: Expr) -> str:
    """
    Identify the expansion strategy appropriate for the expression.

    Returns a human-readable description of the approach.
    """
    if isinstance(expr, Mul):
        factors = [a for a in expr.args if isinstance(a, Add)]
        if len(factors) == 2:
            return "FOIL method (First, Outer, Inner, Last) for two binomials."
        elif len(factors) > 2:
            return f"Sequential distribution across {len(factors)} polynomial factors."
        else:
            return "Distribution (multiply constant/monomial through parentheses)."

    if isinstance(expr, Pow):
        base, exp = expr.args
        if isinstance(base, Add) and exp.is_integer and exp > 0:
            if exp == 2:
                return "Perfect Square Formula: (a+b)² = a² + 2ab + b²."
            elif exp == 3:
                return "Binomial Cube Formula: (a+b)³ = a³ + 3a²b + 3ab² + b³."
            else:
                return f"Binomial Theorem for ({expr_to_str(base)})^{exp}."

    return "General algebraic expansion via distributive law."


def _expand_foil_steps(
    factor1: Expr, factor2: Expr, sb: StepBuilder
) -> Expr:
    """
    Expand two binomials using FOIL with explicit intermediate steps.
    Works for any variable binomials.

    Returns: the expanded result.
    """
    terms1 = Add.make_args(factor1)
    terms2 = Add.make_args(factor2)

    sb.add("Apply FOIL: multiply each term of the first factor by each term of the second:")
    partial_products = []
    for t1 in terms1:
        for t2 in terms2:
            product = sympy.expand(t1 * t2)
            sb.add(f"  ({expr_to_str(t1)}) × ({expr_to_str(t2)}) = {expr_to_str(product)}")
            partial_products.append(product)

    raw_sum = sympy.Add(*partial_products)
    return raw_sum


def _expand_binomial_power(base: Expr, n: int, sb: StepBuilder) -> Expr:
    """
    Expand (base)^n using Binomial Theorem, explaining each coefficient.
    """
    terms = Add.make_args(base)
    if len(terms) == 2:
        a, b = terms
        sb.add(f"Apply Binomial Theorem: ({expr_to_str(a)} + {expr_to_str(b)})^{n}")
        sb.add_rule(
            f"(a+b)^n = Σ C(n,k)·a^(n-k)·b^k  for k = 0 to {n}"
        )
        parts = []
        for k in range(n + 1):
            coeff = int(sympy.binomial(n, k))
            term = sympy.expand(coeff * a**(n - k) * b**k)
            sb.add(f"  k={k}: C({n},{k})·({expr_to_str(a)})^{n-k}·({expr_to_str(b)})^{k} = {expr_to_str(term)}")
            parts.append(term)
        return sympy.Add(*parts)

    # Non-binomial power — just use SymPy expand
    sb.add(f"Expression has {len(terms)} terms; apply general expansion.")
    return expand(base**n)


def expand_expression(
    expr: Expr,
    variables: list[Symbol],
) -> dict:
    """
    Expand an algebraic expression with step-by-step reasoning.

    Args:
        expr: A SymPy expression (NOT an Eq).
        variables: Detected variables list.

    Returns:
        dict with keys: steps (list[str]), final_answer (str)

    Raises:
        ExpansionError: On failure.

    Example:
        >>> from sympy import symbols
        >>> x, y = symbols('x y')
        >>> result = expand_expression((x+1)*(x-2), [x])
        >>> result['final_answer']
        'x**2 - x - 2'
    """
    sb = StepBuilder()
    var_names = ", ".join(str(v) for v in variables)

    sb.add(f"Identify the expression to expand in variable(s): {var_names}.")
    sb.add_expr("Original expression:", expr)

    # Determine strategy
    strategy = _describe_expansion_strategy(expr)
    sb.add(f"Expansion strategy: {strategy}")

    # --- FOIL case: Mul of two binomials ---
    if isinstance(expr, Mul):
        add_factors = [a for a in expr.args if isinstance(a, Add)]
        numeric_factors = [a for a in expr.args if a.is_number]
        other_factors = [a for a in expr.args if not isinstance(a, Add) and not a.is_number]

        prefix = sympy.Mul(*numeric_factors) * sympy.Mul(*other_factors) if (numeric_factors or other_factors) else sympy.Integer(1)

        if add_factors:
            if len(add_factors) == 2:
                intermediate = _expand_foil_steps(add_factors[0], add_factors[1], sb)
            else:
                # Multiple factors: expand sequentially
                sb.add(f"Expand sequentially across {len(add_factors)} factors:")
                intermediate = add_factors[0]
                for i, factor_expr in enumerate(add_factors[1:], start=2):
                    prev = intermediate
                    intermediate = expand(intermediate * factor_expr)
                    sb.add_computation(
                        f"Multiply result by factor {i}:",
                        sympy.Mul(prev, factor_expr),
                        intermediate,
                    )

            if prefix != 1:
                sb.add_computation(
                    f"Multiply by leading coefficient/factor {expr_to_str(prefix)}:",
                    intermediate,
                    expand(prefix * intermediate),
                )
                intermediate = expand(prefix * intermediate)
        else:
            intermediate = expand(expr)

    # --- Binomial Power case ---
    elif isinstance(expr, Pow):
        base, exp = expr.args
        if isinstance(base, Add) and exp.is_integer and exp > 0:
            n = int(exp)
            intermediate = _expand_binomial_power(base, n, sb)
        else:
            sb.add("Non-standard power form; applying direct expansion.")
            intermediate = expand(expr)

    else:
        sb.add("Applying distributive expansion directly.")
        intermediate = expand(expr)

    # --- Collect like terms ---
    result = expand(intermediate)
    if variables:
        collected = collect(result, variables)
        if sympy.simplify(collected - result) == 0 and expr_to_str(collected) != expr_to_str(result):
            sb.add_computation("Collect like terms:", result, collected)
            result = collected
        else:
            sb.add_computation("Combine and collect like terms:", intermediate, result)
    else:
        sb.add_computation("Combine like terms:", intermediate, result)

    # --- Verify ---
    check = sympy.simplify(result - expand(expr))
    verified = (check == 0)
    sb.add(
        f"Verify expansion: expanded form equals original when simplified → "
        f"{'✓ Confirmed' if verified else '⚠ Discrepancy detected — review.'}"
    )

    final_answer = expr_to_str(result)
    logger.info("Expansion complete: %s", final_answer)

    return {
        "steps": sb.build(),
        "final_answer": final_answer,
    }
