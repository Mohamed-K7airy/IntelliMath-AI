"""
test_algebra_engine.py
=======================
Comprehensive test suite for the IntelliMath Algebra Engine.

Covers:
  - Linear equations (simple, fractional, multi-step)
  - Quadratic equations (two real roots, one repeated, complex)
  - Factoring (GCF, difference of squares, trinomials)
  - Simplification (rational expressions, polynomial reduction)
  - Expansion (FOIL, binomial cube, multi-factor)
  - Error handling (invalid input, empty input, non-algebraic)
  - Variable-agnostic behaviour

Run with:
    cd backend
    python -m pytest math_engine/tests/test_algebra_engine.py -v

Or directly:
    python math_engine/tests/test_algebra_engine.py
"""

import sys
import os
import json
import pprint
import logging

# ---------------------------------------------------------------------------
# Path setup — allows running the tests from anywhere inside the project
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.abspath(os.path.join(_HERE, "..", ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from math_engine.algebra.algebra_engine import solve

# Configure logging so test output shows engine internals
logging.basicConfig(
    level=logging.WARNING,     # set to DEBUG for maximum verbosity
    format="%(levelname)s [%(name)s] %(message)s",
)

# ---------------------------------------------------------------------------
# ANSI colours for terminal readability
# ---------------------------------------------------------------------------
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


# ---------------------------------------------------------------------------
# Test runner helpers
# ---------------------------------------------------------------------------

def _print_result(result: dict, indent: int = 2) -> None:
    """Pretty-print a result, hiding metadata for readability."""
    display = {k: v for k, v in result.items() if k != "metadata"}
    print(json.dumps(display, indent=indent, ensure_ascii=False))
    if "metadata" in result:
        extra = {k: v for k, v in result["metadata"].items() if k != "elapsed_ms"}
        if extra:
            print(f"  [metadata extras]: {extra}")
        print(f"  [elapsed]: {result['metadata'].get('elapsed_ms', '?')} ms")


def run_test(
    label: str,
    raw_input: str,
    expected_type: str,
    expected_answer_contains: str | None = None,
    should_fail: bool = False,
) -> bool:
    """
    Execute a single test case.

    Args:
        label: Human-readable test name.
        raw_input: The string to pass to solve().
        expected_type: The 'type' value expected in the response.
        expected_answer_contains: Substring expected in 'final_answer'.
        should_fail: If True, expects confidence < 0.5 or error key present.

    Returns:
        True if test passed, False otherwise.
    """
    print(f"\n{CYAN}{BOLD}{'─'*60}{RESET}")
    print(f"{BOLD}TEST: {label}{RESET}")
    print(f"  Input: {YELLOW}{raw_input!r}{RESET}")

    try:
        result = solve(raw_input)
    except Exception as exc:
        if should_fail:
            print(f"  {GREEN}✓ Expected exception: {exc}{RESET}")
            return True
        print(f"  {RED}✗ Unexpected exception: {exc}{RESET}")
        return False

    _print_result(result)

    passed = True
    failures = []

    # Check type matches
    if result.get("type", "").lower() != expected_type.lower():
        if not should_fail:
            failures.append(
                f"type mismatch: got '{result.get('type')}', expected '{expected_type}'"
            )

    # Check answer contains substring
    if expected_answer_contains is not None:
        answer = result.get("final_answer", "")
        if expected_answer_contains.lower() not in answer.lower():
            if not should_fail:
                failures.append(
                    f"answer '{answer}' does not contain '{expected_answer_contains}'"
                )

    # Check error handling
    if should_fail:
        if result.get("confidence", 1.0) >= 0.5 and "error" not in result:
            failures.append("Expected failure but got confident result.")

    # Check steps exist
    if not should_fail:
        if not result.get("steps"):
            failures.append("No steps returned.")

        if result.get("confidence", 0) < 0.5:
            failures.append(f"Low confidence: {result.get('confidence')}")

    if failures:
        for f in failures:
            print(f"  {RED}✗ {f}{RESET}")
        passed = False
    else:
        print(f"  {GREEN}✓ PASSED{RESET}")

    return passed


# ---------------------------------------------------------------------------
# TEST CASES
# ---------------------------------------------------------------------------

TEST_CASES = [
    # ── LINEAR EQUATIONS ──────────────────────────────────────────────────
    {
        "label": "01. Simple linear equation (x)",
        "input": "2x + 4 = 10",
        "expected_type": "Linear Equation",
        "expected_answer_contains": "3",
    },
    {
        "label": "02. Linear equation with negatives",
        "input": "5x - 15 = 0",
        "expected_type": "Linear Equation",
        "expected_answer_contains": "3",
    },
    {
        "label": "03. Linear equation — different variable (t)",
        "input": "3t + 9 = 0",
        "expected_type": "Linear Equation",
        "expected_answer_contains": "-3",
    },
    {
        "label": "04. Linear equation with fractions",
        "input": "x/2 + 3 = 7",
        "expected_type": "Linear Equation",
        "expected_answer_contains": "8",
    },
    {
        "label": "05. Linear — keyword 'solve' hint",
        "input": "Solve 7y - 14 = 0",
        "expected_type": "Linear Equation",
        "expected_answer_contains": "2",
    },

    # ── QUADRATIC EQUATIONS ───────────────────────────────────────────────
    {
        "label": "06. Quadratic with two distinct real roots",
        "input": "x^2 - 5x + 6 = 0",
        "expected_type": "Quadratic Equation",
        "expected_answer_contains": "2",          # roots 2 and 3
    },
    {
        "label": "07. Quadratic — perfect square (repeated root)",
        "input": "x^2 - 6x + 9 = 0",
        "expected_type": "Quadratic Equation",
        "expected_answer_contains": "3",
    },
    {
        "label": "08. Quadratic with complex roots",
        "input": "x^2 + x + 1 = 0",
        "expected_type": "Quadratic Equation",
        "expected_answer_contains": "x",    # complex expression contains 'x' or 'I'
    },
    {
        "label": "09. Quadratic — different variable (n)",
        "input": "2n^2 - 8 = 0",
        "expected_type": "Quadratic Equation",
        "expected_answer_contains": "2",
    },
    {
        "label": "10. Quadratic via keyword 'solve'",
        "input": "Solve x^2 - 4 = 0",
        "expected_type": "Quadratic Equation",
        "expected_answer_contains": "2",
    },

    # ── FACTORING ─────────────────────────────────────────────────────────
    {
        "label": "11. Factor simple trinomial",
        "input": "Factor x^2 - 5x + 6",
        "expected_type": "Factoring",
        "expected_answer_contains": "x",
    },
    {
        "label": "12. Difference of squares",
        "input": "Factor x^2 - 9",
        "expected_type": "Factoring",
        "expected_answer_contains": "x",
    },
    {
        "label": "13. Factor with GCF",
        "input": "Factor 6x^2 + 12x",
        "expected_type": "Factoring",
        "expected_answer_contains": "x",
    },
    {
        "label": "14. Factor with different variable (z)",
        "input": "Factorise z^2 - z - 6",
        "expected_type": "Factoring",
        "expected_answer_contains": "z",
    },
    {
        "label": "15. Multivariate factoring",
        "input": "Factor x^2*y - x*y^2",
        "expected_type": "Factoring",
        "expected_answer_contains": "x",
    },

    # ── SIMPLIFICATION ────────────────────────────────────────────────────
    {
        "label": "16. Simplify rational expression",
        "input": "Simplify (x^2 - 4) / (x - 2)",
        "expected_type": "Simplification",
        "expected_answer_contains": "x",          # should simplify to x + 2
    },
    {
        "label": "17. Simplify polynomial expression",
        "input": "Simplify 3x + 2x - x",
        "expected_type": "Simplification",
        "expected_answer_contains": "4",
    },
    {
        "label": "18. Simplify with multiple variables",
        "input": "simplify 2x + 3y + x - y",
        "expected_type": "Simplification",
        "expected_answer_contains": "x",
    },

    # ── EXPANSION ─────────────────────────────────────────────────────────
    {
        "label": "19. Expand FOIL (x+1)(x-2)",
        "input": "Expand (x+1)*(x-2)",
        "expected_type": "Expansion",
        "expected_answer_contains": "x",
    },
    {
        "label": "20. Expand binomial cube",
        "input": "Expand (x+1)^3",
        "expected_type": "Expansion",
        "expected_answer_contains": "x",
    },
    {
        "label": "21. Expand with coefficient",
        "input": "Distribute 3*(x+4)",
        "expected_type": "Expansion",
        "expected_answer_contains": "12",
    },
    {
        "label": "22. Expand two-variable expression",
        "input": "Expand (x+y)^2",
        "expected_type": "Expansion",
        "expected_answer_contains": "x",
    },

    # ── ERROR HANDLING ────────────────────────────────────────────────────
    {
        "label": "23. Empty input (should error gracefully)",
        "input": "   ",
        "expected_type": "Error",
        "should_fail": True,
    },
    {
        "label": "24. Pure number — no variables",
        "input": "42",
        "expected_type": "Simplification",    # constant expression
        "expected_answer_contains": None,
    },
]


def main() -> None:
    print(f"\n{BOLD}{CYAN}{'='*60}")
    print("  IntelliMath — Algebra Engine Test Suite")
    print(f"{'='*60}{RESET}")

    passed = 0
    failed = 0
    failed_labels = []

    for tc in TEST_CASES:
        ok = run_test(
            label=tc["label"],
            raw_input=tc["input"],
            expected_type=tc["expected_type"],
            expected_answer_contains=tc.get("expected_answer_contains"),
            should_fail=tc.get("should_fail", False),
        )
        if ok:
            passed += 1
        else:
            failed += 1
            failed_labels.append(tc["label"])

    total = passed + failed
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}Results: {GREEN}{passed}/{total} passed{RESET}", end="")
    if failed:
        print(f"  {RED}({failed} failed){RESET}")
    else:
        print(f"  {GREEN}— All tests passed ✓{RESET}")

    if failed_labels:
        print(f"\n{RED}Failed tests:{RESET}")
        for label in failed_labels:
            print(f"  • {label}")

    print(f"\n{CYAN}{'='*60}{RESET}\n")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
