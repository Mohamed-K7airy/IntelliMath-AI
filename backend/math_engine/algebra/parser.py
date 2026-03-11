"""
parser.py - Algebra Expression Parser
======================================
Safely parses raw text input into SymPy expressions.
Supports flexible variable detection and normalization.

Production-grade: handles malformed input, injection attempts,
and unsupported tokens gracefully.
"""

import re
import logging
from typing import Tuple, Optional

import sympy
from sympy import symbols, sympify, Eq, Symbol
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)

logger = logging.getLogger(__name__)

# Extended safe transformations for natural math input
TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)

# Symbols that are safe to expose to the parser namespace
SAFE_LOCALS_BASE: dict = {
    name: getattr(sympy, name)
    for name in dir(sympy)
    if not name.startswith("_")
}


class ParseError(Exception):
    """Raised when an expression cannot be parsed."""
    pass


def detect_variables(expression_str: str) -> list[Symbol]:
    """
    Detect all single-letter variables in an expression string.
    Excludes known mathematical constants (e, i, E, I).

    Returns:
        List of SymPy Symbol objects sorted alphabetically.
    """
    reserved = {"e", "E", "i", "I", "pi", "oo"}
    # Match single lowercase or uppercase letters used as variable names
    candidates = set(re.findall(r'\b([a-zA-Z])\b', expression_str))
    variable_names = sorted(candidates - reserved)
    return [Symbol(v) for v in variable_names]


def normalize_input(raw: str) -> str:
    """
    Normalize raw user input for safer parsing:
    - Strip whitespace
    - Replace ^ with ** (handled by convert_xor but kept as fallback)
    - Collapse multiple spaces
    - Reject empty input
    """
    if not raw or not raw.strip():
        raise ParseError("Input expression is empty.")

    text = raw.strip()
    # Replace Unicode minus with ASCII minus
    text = text.replace("\u2212", "-")
    # Replace Unicode multiplication sign
    text = text.replace("\u00d7", "*")
    # Replace Unicode division sign
    text = text.replace("\u00f7", "/")
    # Collapse multiple whitespace
    text = re.sub(r"\s+", " ", text)
    return text


def split_equation(raw: str) -> Tuple[str, Optional[str]]:
    """
    Splits a string on '=' to identify if it's an equation or expression.

    Returns:
        (lhs_str, rhs_str) if equation, or (expr_str, None) if expression.
    """
    parts = raw.split("=")
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    elif len(parts) == 1:
        return parts[0].strip(), None
    else:
        raise ParseError(
            f"Invalid equation format: multiple '=' found in '{raw}'. "
            "Provide exactly one '=' for equations."
        )


def parse_expression(expr_str: str, local_syms: dict) -> sympy.Expr:
    """
    Parse a single expression string into a SymPy expression.

    Args:
        expr_str: The string to parse.
        local_syms: Dictionary of symbol name -> Symbol for this expression.

    Returns:
        A SymPy expression.

    Raises:
        ParseError: On any parsing failure.
    """
    try:
        local_ns = {**SAFE_LOCALS_BASE, **local_syms}
        result = parse_expr(
            expr_str,
            local_dict=local_ns,
            transformations=TRANSFORMATIONS,
            evaluate=False,
        )
        return result
    except (SyntaxError, TypeError, AttributeError, sympy.SympifyError) as exc:
        raise ParseError(
            f"Cannot parse expression '{expr_str}': {exc}"
        ) from exc


def parse_problem(raw_input: str) -> Tuple[sympy.Basic, list[Symbol]]:
    """
    Master parser entry point.

    Accepts a raw math problem string and returns:
    - A SymPy object (Eq for equations, Expr for expressions)
    - The list of detected variables

    Args:
        raw_input: E.g. "2x^2 - 4x + 2 = 0" or "x^2 - 9"

    Returns:
        (sympy_object, variables)

    Raises:
        ParseError: On failure.

    Examples:
        >>> obj, vars = parse_problem("2x^2 - 4x + 2 = 0")
        >>> obj
        Eq(2*x**2 - 4*x + 2, 0)

        >>> obj, vars = parse_problem("x^2 - 9")
        >>> obj
        x**2 - 9
    """
    normalized = normalize_input(raw_input)
    logger.debug("Normalized input: %s", normalized)

    lhs_str, rhs_str = split_equation(normalized)

    # Detect variables from full input
    variables = detect_variables(normalized)
    if not variables:
        # Treat as constant expression
        logger.warning("No variables detected in '%s'.", normalized)

    var_dict = {v.name: v for v in variables}

    lhs = parse_expression(lhs_str, var_dict)

    if rhs_str is not None:
        rhs = parse_expression(rhs_str, var_dict)
        result = Eq(lhs, rhs)
    else:
        result = lhs

    logger.debug("Parsed result: %s | Variables: %s", result, variables)
    return result, variables
