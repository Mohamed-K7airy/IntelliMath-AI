"""
math_engine/algebra/__init__.py
Public API surface for the Algebra Engine.
"""

from .algebra_engine import solve
from .detector import AlgebraOperation

__all__ = ["solve", "AlgebraOperation"]
