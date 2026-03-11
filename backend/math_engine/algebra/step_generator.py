"""
step_generator.py - Structured Step Builder
=============================================
Provides utilities for building numbered, readable step strings
and assembling the canonical step trace list used across all solvers.

All solvers in the Algebra Engine delegate step construction here,
keeping formatting concerns out of mathematical logic.
"""

import sympy
from sympy import latex, Symbol, Expr, Eq


class StepBuilder:
    """
    Accumulates steps and renders them as clean numbered strings.

    Usage:
        sb = StepBuilder()
        sb.add("Identify the equation type: linear")
        sb.add_expr("Rewrite as:", equation)
        steps = sb.build()
    """

    def __init__(self):
        self._steps: list[str] = []

    def add(self, text: str) -> "StepBuilder":
        """Append a plain-text step."""
        self._steps.append(text.strip())
        return self

    def add_expr(self, label: str, expr: sympy.Basic) -> "StepBuilder":
        """
        Append a step with a human-readable expression.
        Uses SymPy's pretty string representation for readability,
        with LaTeX as supplementary notation.
        """
        pretty = sympy.pretty(expr, use_unicode=False)
        lx = latex(expr)
        self._steps.append(f"{label.strip()} {pretty}  (LaTeX: ${lx}$)")
        return self

    def add_substitution(
        self, label: str, var: Symbol, value: sympy.Basic
    ) -> "StepBuilder":
        """Record a substitution step."""
        pretty_val = sympy.pretty(value, use_unicode=False)
        self._steps.append(f"{label.strip()} {var} = {pretty_val}")
        return self

    def add_computation(
        self, label: str, lhs: sympy.Basic, rhs: sympy.Basic
    ) -> "StepBuilder":
        """Record a computation step: lhs => rhs."""
        pretty_lhs = sympy.pretty(lhs, use_unicode=False)
        pretty_rhs = sympy.pretty(rhs, use_unicode=False)
        self._steps.append(f"{label.strip()} {pretty_lhs}  =>  {pretty_rhs}")
        return self

    def add_rule(self, rule: str) -> "StepBuilder":
        """Add a mathematical rule / theorem reference."""
        self._steps.append(f"[Rule] {rule.strip()}")
        return self

    def build(self) -> list[str]:
        """Return list of numbered step strings."""
        return [f"Step {i + 1}: {step}" for i, step in enumerate(self._steps)]

    def clear(self) -> "StepBuilder":
        """Reset steps."""
        self._steps.clear()
        return self


def format_solution_set(solutions: list) -> str:
    """
    Format a list of SymPy solutions into a clean string.

    Examples:
        [2]          -> "x = 2"
        [2, -3]      -> "x = 2  or  x = -3"
        []           -> "No real solution"
        {x: 2, y: 3} -> listed as x = 2, y = 3
    """
    if not solutions:
        return "No real solution"

    parts = []
    for sol in solutions:
        if isinstance(sol, dict):
            pair = ", ".join(f"{k} = {sympy.pretty(v)}" for k, v in sol.items())
            parts.append(pair)
        else:
            parts.append(str(sol))

    return "  or  ".join(parts)


def expr_to_str(expr: sympy.Basic) -> str:
    """Convert a SymPy expression to a clean printable string."""
    return sympy.pretty(expr, use_unicode=False)
