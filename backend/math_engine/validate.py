"""
Quick smoke-test for all math_engine modules.
Run from the backend/ directory:  python -m math_engine.validate
"""

import json
import sys

def _pp(label: str, result: dict) -> None:
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(json.dumps(result, indent=2, default=str))
    if "error" in result:
        print("  ⚠  ERROR detected")
    else:
        print("  ✓  OK")


def main() -> None:
    failures = 0

    # --- Calculus ---
    from math_engine.calculus import solve as calc_solve
    r = calc_solve("derivative of x**3 + 2*x")
    _pp("Calculus – derivative of x³ + 2x", r)
    if "error" in r: failures += 1

    r = calc_solve("integrate x**2 from 0 to 1")
    _pp("Calculus – definite integral ∫₀¹ x² dx", r)
    if "error" in r: failures += 1

    r = calc_solve("limit of sin(x)/x as x -> 0")
    _pp("Calculus – limit sin(x)/x as x→0", r)
    if "error" in r: failures += 1

    # --- Linear Algebra ---
    from math_engine.linear_algebra import solve as la_solve
    r = la_solve("determinant", matrix=[[1, 2], [3, 4]])
    _pp("LinAlg – determinant [[1,2],[3,4]]", r)
    if "error" in r: failures += 1

    r = la_solve("inverse", matrix=[[1, 2], [3, 4]])
    _pp("LinAlg – inverse [[1,2],[3,4]]", r)
    if "error" in r: failures += 1

    r = la_solve("solve_system",
                 coefficients=[[2, 1], [5, 3]],
                 constants=[[11], [23]])
    _pp("LinAlg – solve system", r)
    if "error" in r: failures += 1

    # --- Probability ---
    from math_engine.probability import solve as prob_solve
    r = prob_solve("combination", n=10, r=3)
    _pp("Probability – C(10,3)", r)
    if "error" in r: failures += 1

    r = prob_solve("conditional", p_a_and_b="1/4", p_b="1/2")
    _pp("Probability – conditional", r)
    if "error" in r: failures += 1

    # --- Statistics ---
    from math_engine.statistics_engine import solve as stat_solve
    r = stat_solve("mean", data=[10, 20, 30, 40, 50])
    _pp("Statistics – mean", r)
    if "error" in r: failures += 1

    r = stat_solve("std_dev", data=[2, 4, 4, 4, 5, 5, 7, 9])
    _pp("Statistics – std dev", r)
    if "error" in r: failures += 1

    r = stat_solve("summary", data=[1, 3, 5, 7, 9, 11])
    _pp("Statistics – summary", r)
    if "error" in r: failures += 1

    # --- Geometry ---
    from math_engine.geometry import solve as geo_solve
    r = geo_solve("circle", "area", radius=5)
    _pp("Geometry – circle area r=5", r)
    if "error" in r: failures += 1

    r = geo_solve("sphere", "volume", radius=3)
    _pp("Geometry – sphere volume r=3", r)
    if "error" in r: failures += 1

    r = geo_solve("right_triangle", "hypotenuse", a=3, b=4)
    _pp("Geometry – right triangle hypotenuse 3-4-?", r)
    if "error" in r: failures += 1

    # --- Discrete Math ---
    from math_engine.discrete_math import solve as dm_solve
    r = dm_solve("truth_table", expression="p & q | ~p")
    _pp("Discrete – truth table (p & q | ~p)", r)
    if "error" in r: failures += 1

    r = dm_solve("combination", n=8, r=3)
    _pp("Discrete – C(8,3)", r)
    if "error" in r: failures += 1

    # --- Word Problems ---
    from math_engine.word_problems import solve as wp_solve
    r = wp_solve("John is 5 years older than Mary. The sum of their ages is 29.")
    _pp("Word Problem – age problem", r)
    if "error" in r: failures += 1

    # --- Summary ---
    print(f"\n{'='*60}")
    if failures:
        print(f"  ✗  {failures} test(s) produced errors.")
        sys.exit(1)
    else:
        print("  ✓  All smoke tests passed!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
