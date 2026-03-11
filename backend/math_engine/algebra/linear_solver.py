"""
linear_solver.py - Linear Equation Solver
==========================================
Solves single-variable and multi-variable linear equations.

For single-variable equations:
- Rearranges to standard form: ax = b
- Extracts coefficients explicitly
- Generates a clear step-by-step derivation

For multi-variable systems (future extensibility):
- Identifies system, delegates gracefully

Production-grade: no assumptions about variable name.
"""

import logging
from typing import Union

import sympy
from sympy import Eq, Symbol, solve, Rational, expand, collect, latex

from .step_generator import StepBuilder, format_solution_set, expr_to_str

logger = logging.getLogger(__name__)


class LinearSolverError(Exception):
    """Raised when linear solving fails."""
    pass


def _extract_linear_coefficients(
    expr: sympy.Expr, var: Symbol
) -> tuple[sympy.Expr, sympy.Expr]:
    """
    For a linear expression ax + b, extract (a, b).

    Returns:
        (coefficient_of_var, constant_term)
    """
    expanded = expand(expr)
    a = expanded.coeff(var, 1)
    b = expanded - a * var
    return a, b


def solve_linear(
    equation: Eq,
    variables: list[Symbol],
) -> dict:
    """
    Solve a linear equation with detailed step generation.

    Args:
        equation: A SymPy Eq object, e.g. Eq(2*x + 4, 10)
        variables: Detected variables list.

    Returns:
        dict with keys: steps (list[str]), final_answer (str)

    Raises:
        LinearSolverError: On failure.

    Example:
        >>> from sympy import symbols, Eq
        >>> x = symbols('x')
        >>> result = solve_linear(Eq(2*x + 4, 10), [x])
        >>> result['final_answer']
        'x = 3'
    """
    if not variables:
        raise LinearSolverError("No variables detected in the equation.")

    # For now: single-variable linear solver
    # Multi-variable support flag for future extension
    if len(variables) > 1:
        return _solve_linear_system(equation, variables)

    var = variables[0]
    sb = StepBuilder()

    sb.add(
        f"Identify the equation type: Linear equation in one variable '{var}'."
    )
    sb.add_expr("Original equation:", equation)

    # --- Move all terms to LHS ---
    lhs = equation.lhs
    rhs = equation.rhs

    combined = expand(lhs - rhs)
    sb.add_computation(
        "Move all terms to left-hand side (subtract RHS from both sides):",
        equation,
        Eq(combined, 0),
    )

    # --- Extract coefficients ---
    a, b = _extract_linear_coefficients(combined, var)

    if a == 0:
        # Degenerate case
        if b == 0:
            result_str = "Infinitely many solutions (identity equation)."
            sb.add(result_str)
            return {
                "steps": sb.build(),
                "final_answer": result_str,
            }
        else:
            result_str = "No solution (contradiction — constant equation)."
            sb.add(result_str)
            return {
                "steps": sb.build(),
                "final_answer": result_str,
            }

    sb.add(
        f"Identify coefficients: coefficient of {var} is {expr_to_str(a)}, "
        f"constant term is {expr_to_str(b)}."
    )
    sb.add_rule(f"Standard linear form: {var} = -b/a = -({expr_to_str(b)}) / ({expr_to_str(a)})")

    # --- Isolate variable: ax + b = 0 → ax = -b → x = -b/a ---
    stage1 = Eq(a * var, -b)
    sb.add_computation(
        f"Subtract constant {expr_to_str(b)} from both sides:",
        Eq(combined, 0),
        stage1,
    )

    solution_val = sympy.simplify(-b / a)
    sb.add_computation(
        f"Divide both sides by {expr_to_str(a)}:",
        stage1,
        Eq(var, solution_val),
    )

    # --- Verification step ---
    lhs_check = sympy.simplify(equation.lhs.subs(var, solution_val))
    rhs_check = sympy.simplify(equation.rhs.subs(var, solution_val))
    verified = (lhs_check == rhs_check)
    sb.add(
        f"Verify solution: substitute {var} = {expr_to_str(solution_val)} "
        f"back into original equation → "
        f"{'✓ Verified' if verified else '⚠ Verification mismatch — check equation.'}"
    )

    final_answer = f"{var} = {expr_to_str(solution_val)}"
    logger.info("Linear solve complete: %s", final_answer)

    return {
        "steps": sb.build(),
        "final_answer": final_answer,
    }


def _solve_linear_system(equation: Eq, variables: list[Symbol]) -> dict:
    """
    Placeholder for multi-variable linear equation handling.
    Currently surfaces a clear message and delegates to SymPy solve.

    This will be expanded in the LinearAlgebra module for full system solving.
    """
    sb = StepBuilder()
    sb.add(
        f"Detected {len(variables)}-variable linear equation. "
        "Multi-variable linear system solving is handled by the Linear Algebra engine. "
        "Attempting single-equation solve with SymPy."
    )

    solutions = solve(equation, variables)
    if not solutions:
        answer = "No solution found."
    elif isinstance(solutions, dict):
        parts = [f"{k} = {sympy.pretty(v)}" for k, v in solutions.items()]
        answer = ", ".join(parts)
    else:
        answer = format_solution_set(solutions)

    sb.add(f"SymPy solution: {answer}")

    return {
        "steps": sb.build(),
        "final_answer": answer,
    }
