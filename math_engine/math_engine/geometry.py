"""
math_engine/geometry.py

Production-ready geometry engine for IntelliMath.
Supports: area, perimeter, volume, surface area, and basic
trigonometric geometry for common shapes.
"""

from __future__ import annotations

from typing import Any

import sympy as sp
from sympy import (
    Rational, pi, sqrt, simplify, sin, cos, tan, asin, acos, atan,
    Symbol, S,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _error(msg: str) -> dict[str, Any]:
    return {"error": str(msg), "confidence": 0.0}


def _pos(value: Any, name: str) -> Rational | dict:
    """Validate and convert to a positive Rational."""
    try:
        v = Rational(value)
    except (TypeError, ValueError):
        return _error(f"'{name}' must be numeric, got {type(value).__name__}.")
    if v <= 0:
        return _error(f"'{name}' must be positive, got {v}.")
    return v


def _non_neg(value: Any, name: str) -> Rational | dict:
    try:
        v = Rational(value)
    except (TypeError, ValueError):
        return _error(f"'{name}' must be numeric, got {type(value).__name__}.")
    if v < 0:
        return _error(f"'{name}' must be non-negative, got {v}.")
    return v


def _fmt(expr: Any) -> str:
    s = simplify(expr)
    return str(s)

# ---------------------------------------------------------------------------
# 2-D shapes
# ---------------------------------------------------------------------------

def _circle(operation: str, **kw: Any) -> dict[str, Any]:
    r = _pos(kw.get("radius"), "radius")
    if isinstance(r, dict):
        return r
    steps: list[str] = [f"Shape: circle, radius = {r}"]

    if operation == "area":
        result = pi * r**2
        steps.append(f"Area = π × r² = π × {r}² = {_fmt(result)}")
    elif operation == "perimeter":
        result = 2 * pi * r
        steps.append(f"Circumference = 2πr = 2 × π × {r} = {_fmt(result)}")
    else:
        return _error(f"Unsupported operation '{operation}' for circle.")

    steps.append(f"≈ {float(result):.6f}")
    return {
        "branch": "geometry",
        "type": f"circle_{operation}",
        "steps": steps,
        "final_answer": _fmt(result),
        "confidence": 0.99,
    }


def _rectangle(operation: str, **kw: Any) -> dict[str, Any]:
    l = _pos(kw.get("length"), "length")
    if isinstance(l, dict):
        return l
    w = _pos(kw.get("width"), "width")
    if isinstance(w, dict):
        return w
    steps: list[str] = [f"Shape: rectangle, length = {l}, width = {w}"]

    if operation == "area":
        result = l * w
        steps.append(f"Area = l × w = {l} × {w} = {result}")
    elif operation == "perimeter":
        result = 2 * (l + w)
        steps.append(f"Perimeter = 2(l + w) = 2({l} + {w}) = {result}")
    elif operation == "diagonal":
        result = sqrt(l**2 + w**2)
        steps.append(f"Diagonal = √(l² + w²) = √({l}² + {w}²) = {_fmt(result)}")
    else:
        return _error(f"Unsupported operation '{operation}' for rectangle.")

    return {
        "branch": "geometry",
        "type": f"rectangle_{operation}",
        "steps": steps,
        "final_answer": _fmt(result),
        "confidence": 0.99,
    }


def _triangle(operation: str, **kw: Any) -> dict[str, Any]:
    steps: list[str] = []

    if operation == "area":
        base = kw.get("base")
        height = kw.get("height")
        if base is not None and height is not None:
            b = _pos(base, "base")
            if isinstance(b, dict):
                return b
            h = _pos(height, "height")
            if isinstance(h, dict):
                return h
            steps.append(f"Shape: triangle, base = {b}, height = {h}")
            result = Rational(1, 2) * b * h
            steps.append(f"Area = ½ × base × height = ½ × {b} × {h} = {result}")
        else:
            # Heron's formula
            a = _pos(kw.get("a"), "a")
            if isinstance(a, dict):
                return a
            b = _pos(kw.get("b"), "b")
            if isinstance(b, dict):
                return b
            c = _pos(kw.get("c"), "c")
            if isinstance(c, dict):
                return c
            if a + b <= c or a + c <= b or b + c <= a:
                return _error("Invalid triangle sides (triangle inequality violated).")
            s = (a + b + c) / 2
            steps.append(f"Shape: triangle, sides = {a}, {b}, {c}")
            steps.append(f"Semi-perimeter s = ({a}+{b}+{c})/2 = {s}")
            result = sqrt(s * (s - a) * (s - b) * (s - c))
            steps.append(
                f"Heron's formula: A = √(s(s-a)(s-b)(s-c)) = {_fmt(result)}"
            )

    elif operation == "perimeter":
        a = _pos(kw.get("a"), "a")
        if isinstance(a, dict):
            return a
        b = _pos(kw.get("b"), "b")
        if isinstance(b, dict):
            return b
        c = _pos(kw.get("c"), "c")
        if isinstance(c, dict):
            return c
        result = a + b + c
        steps.append(f"Shape: triangle, sides = {a}, {b}, {c}")
        steps.append(f"Perimeter = a + b + c = {result}")
    else:
        return _error(f"Unsupported operation '{operation}' for triangle.")

    return {
        "branch": "geometry",
        "type": f"triangle_{operation}",
        "steps": steps,
        "final_answer": _fmt(result),
        "confidence": 0.98,
    }


def _trapezoid(operation: str, **kw: Any) -> dict[str, Any]:
    steps: list[str] = []
    if operation == "area":
        a = _pos(kw.get("a"), "a (parallel side 1)")
        if isinstance(a, dict):
            return a
        b = _pos(kw.get("b"), "b (parallel side 2)")
        if isinstance(b, dict):
            return b
        h = _pos(kw.get("height"), "height")
        if isinstance(h, dict):
            return h
        result = Rational(1, 2) * (a + b) * h
        steps.append(f"Shape: trapezoid, a = {a}, b = {b}, height = {h}")
        steps.append(f"Area = ½(a + b) × h = ½({a} + {b}) × {h} = {result}")
    else:
        return _error(f"Unsupported operation '{operation}' for trapezoid.")

    return {
        "branch": "geometry",
        "type": f"trapezoid_{operation}",
        "steps": steps,
        "final_answer": _fmt(result),
        "confidence": 0.98,
    }

# ---------------------------------------------------------------------------
# 3-D shapes
# ---------------------------------------------------------------------------

def _sphere(operation: str, **kw: Any) -> dict[str, Any]:
    r = _pos(kw.get("radius"), "radius")
    if isinstance(r, dict):
        return r
    steps: list[str] = [f"Shape: sphere, radius = {r}"]

    if operation == "volume":
        result = Rational(4, 3) * pi * r**3
        steps.append(f"Volume = (4/3)πr³ = (4/3) × π × {r}³ = {_fmt(result)}")
    elif operation == "surface_area":
        result = 4 * pi * r**2
        steps.append(f"Surface area = 4πr² = 4 × π × {r}² = {_fmt(result)}")
    else:
        return _error(f"Unsupported operation '{operation}' for sphere.")

    steps.append(f"≈ {float(result):.6f}")
    return {
        "branch": "geometry",
        "type": f"sphere_{operation}",
        "steps": steps,
        "final_answer": _fmt(result),
        "confidence": 0.99,
    }


def _cylinder(operation: str, **kw: Any) -> dict[str, Any]:
    r = _pos(kw.get("radius"), "radius")
    if isinstance(r, dict):
        return r
    h = _pos(kw.get("height"), "height")
    if isinstance(h, dict):
        return h
    steps: list[str] = [f"Shape: cylinder, radius = {r}, height = {h}"]

    if operation == "volume":
        result = pi * r**2 * h
        steps.append(f"Volume = πr²h = π × {r}² × {h} = {_fmt(result)}")
    elif operation == "surface_area":
        result = 2 * pi * r * (r + h)
        steps.append(
            f"Surface area = 2πr(r + h) = 2π × {r} × ({r} + {h}) = {_fmt(result)}"
        )
    else:
        return _error(f"Unsupported operation '{operation}' for cylinder.")

    steps.append(f"≈ {float(result):.6f}")
    return {
        "branch": "geometry",
        "type": f"cylinder_{operation}",
        "steps": steps,
        "final_answer": _fmt(result),
        "confidence": 0.99,
    }


def _cone(operation: str, **kw: Any) -> dict[str, Any]:
    r = _pos(kw.get("radius"), "radius")
    if isinstance(r, dict):
        return r
    h = _pos(kw.get("height"), "height")
    if isinstance(h, dict):
        return h
    steps: list[str] = [f"Shape: cone, radius = {r}, height = {h}"]

    slant = sqrt(r**2 + h**2)

    if operation == "volume":
        result = Rational(1, 3) * pi * r**2 * h
        steps.append(f"Volume = (1/3)πr²h = (1/3) × π × {r}² × {h} = {_fmt(result)}")
    elif operation == "surface_area":
        result = pi * r * (r + slant)
        steps.append(f"Slant height l = √(r² + h²) = {_fmt(slant)}")
        steps.append(f"Surface area = πr(r + l) = {_fmt(result)}")
    else:
        return _error(f"Unsupported operation '{operation}' for cone.")

    steps.append(f"≈ {float(result):.6f}")
    return {
        "branch": "geometry",
        "type": f"cone_{operation}",
        "steps": steps,
        "final_answer": _fmt(result),
        "confidence": 0.98,
    }


def _cube(operation: str, **kw: Any) -> dict[str, Any]:
    a = _pos(kw.get("side"), "side")
    if isinstance(a, dict):
        return a
    steps: list[str] = [f"Shape: cube, side = {a}"]

    if operation == "volume":
        result = a**3
        steps.append(f"Volume = a³ = {a}³ = {result}")
    elif operation == "surface_area":
        result = 6 * a**2
        steps.append(f"Surface area = 6a² = 6 × {a}² = {result}")
    elif operation == "diagonal":
        result = a * sqrt(3)
        steps.append(f"Space diagonal = a√3 = {a} × √3 = {_fmt(result)}")
    else:
        return _error(f"Unsupported operation '{operation}' for cube.")

    return {
        "branch": "geometry",
        "type": f"cube_{operation}",
        "steps": steps,
        "final_answer": _fmt(result),
        "confidence": 0.99,
    }


def _rectangular_prism(operation: str, **kw: Any) -> dict[str, Any]:
    l = _pos(kw.get("length"), "length")
    if isinstance(l, dict):
        return l
    w = _pos(kw.get("width"), "width")
    if isinstance(w, dict):
        return w
    h = _pos(kw.get("height"), "height")
    if isinstance(h, dict):
        return h
    steps: list[str] = [f"Shape: rectangular prism, l={l}, w={w}, h={h}"]

    if operation == "volume":
        result = l * w * h
        steps.append(f"Volume = l × w × h = {l} × {w} × {h} = {result}")
    elif operation == "surface_area":
        result = 2 * (l*w + l*h + w*h)
        steps.append(f"SA = 2(lw + lh + wh) = {result}")
    else:
        return _error(f"Unsupported operation '{operation}' for rectangular prism.")

    return {
        "branch": "geometry",
        "type": f"rectangular_prism_{operation}",
        "steps": steps,
        "final_answer": _fmt(result),
        "confidence": 0.99,
    }

# ---------------------------------------------------------------------------
# Trigonometric geometry
# ---------------------------------------------------------------------------

def _right_triangle(operation: str, **kw: Any) -> dict[str, Any]:
    """
    Supports:
    - hypotenuse: given two legs a, b
    - leg: given hypotenuse c and one leg a
    - angle: given two sides, compute angle in degrees
    """
    steps: list[str] = ["Shape: right triangle"]

    if operation == "hypotenuse":
        a = _pos(kw.get("a"), "a")
        if isinstance(a, dict):
            return a
        b = _pos(kw.get("b"), "b")
        if isinstance(b, dict):
            return b
        result = sqrt(a**2 + b**2)
        steps.append(f"Legs: a = {a}, b = {b}")
        steps.append(f"c = √(a² + b²) = √({a}² + {b}²) = {_fmt(result)}")

    elif operation == "leg":
        c = _pos(kw.get("c"), "c (hypotenuse)")
        if isinstance(c, dict):
            return c
        a = _pos(kw.get("a"), "a (known leg)")
        if isinstance(a, dict):
            return a
        if a >= c:
            return _error("Leg must be shorter than hypotenuse.")
        result = sqrt(c**2 - a**2)
        steps.append(f"Hypotenuse c = {c}, known leg a = {a}")
        steps.append(f"b = √(c² - a²) = √({c}² - {a}²) = {_fmt(result)}")

    elif operation == "angle":
        opposite = _pos(kw.get("opposite"), "opposite")
        if isinstance(opposite, dict):
            return opposite
        hypotenuse = _pos(kw.get("hypotenuse"), "hypotenuse")
        if isinstance(hypotenuse, dict):
            return hypotenuse
        if opposite > hypotenuse:
            return _error("Opposite side cannot exceed hypotenuse.")
        angle_rad = asin(opposite / hypotenuse)
        angle_deg = sp.deg(angle_rad)
        result = simplify(angle_deg)
        steps.append(f"opposite = {opposite}, hypotenuse = {hypotenuse}")
        steps.append(f"sin(θ) = opposite / hypotenuse = {opposite}/{hypotenuse}")
        steps.append(f"θ = arcsin({opposite}/{hypotenuse}) = {_fmt(result)}°")

    else:
        return _error(f"Unsupported operation '{operation}' for right_triangle.")

    return {
        "branch": "geometry",
        "type": f"right_triangle_{operation}",
        "steps": steps,
        "final_answer": _fmt(result),
        "confidence": 0.97,
    }

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

_SHAPES = {
    "circle":            _circle,
    "rectangle":         _rectangle,
    "square":            lambda op, **kw: _rectangle(
                             op, length=kw.get("side"), width=kw.get("side")
                         ),
    "triangle":          _triangle,
    "trapezoid":         _trapezoid,
    "sphere":            _sphere,
    "cylinder":          _cylinder,
    "cone":              _cone,
    "cube":              _cube,
    "rectangular_prism": _rectangular_prism,
    "box":               _rectangular_prism,
    "right_triangle":    _right_triangle,
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def solve(shape: str, operation: str, **kwargs: Any) -> dict[str, Any]:
    """
    Solve a geometry problem.

    Parameters
    ----------
    shape : str
        One of: circle, rectangle, square, triangle, trapezoid,
        sphere, cylinder, cone, cube, rectangular_prism, right_triangle.
    operation : str
        E.g. area, perimeter, volume, surface_area, diagonal,
        hypotenuse, leg, angle.
    **kwargs
        Shape-specific dimensions.

    Returns
    -------
    dict
        Structured JSON-serialisable result.
    """
    if not isinstance(shape, str) or not shape.strip():
        return _error("Shape must be a non-empty string.")
    if not isinstance(operation, str) or not operation.strip():
        return _error("Operation must be a non-empty string.")

    shape_key = shape.strip().lower().replace(" ", "_")
    op_key = operation.strip().lower().replace(" ", "_")

    handler = _SHAPES.get(shape_key)
    if handler is None:
        return _error(
            f"Unknown shape '{shape}'. "
            f"Supported: {', '.join(sorted(_SHAPES.keys()))}."
        )

    try:
        return handler(op_key, **kwargs)
    except Exception as exc:  # noqa: BLE001
        return _error(f"Geometry solver error: {exc}")
