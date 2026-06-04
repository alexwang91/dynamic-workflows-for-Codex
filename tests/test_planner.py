from cdw.planner import build_plan


def test_review_plan_uses_fan_out_with_verification():
    plan = build_plan("review", "Review this branch")

    assert plan.command == "review"
    assert plan.pattern == "fan-out-and-synthesize"
    assert plan.verification_strategy == "adversarial"
    assert {unit.id for unit in plan.work_units} >= {
        "security",
        "tests",
        "compatibility",
        "maintainability",
    }


def test_debug_plan_uses_hypothesis_loop():
    plan = build_plan("debug", "This test fails 1 in 50 runs")

    assert plan.command == "debug"
    assert plan.pattern == "hypothesis-fan-out-loop"
    assert plan.max_iterations == 3
    assert {unit.id for unit in plan.work_units} >= {
        "logs",
        "tests",
        "code-path",
        "timing",
    }
