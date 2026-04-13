"""
math_engine/__init__.py

Central registry for all IntelliMath math-engine modules.
Each module exposes a ``solve()`` entry point.
"""

from math_engine import (
    calculus,
    linear_algebra,
    probability,
    statistics_engine as statistics,
    geometry,
    discrete_math,
    word_problems,
)

__all__ = [
    "calculus",
    "linear_algebra",
    "probability",
    "statistics",
    "geometry",
    "discrete_math",
    "word_problems",
]
