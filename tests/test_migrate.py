from cdw.planner import build_plan


def test_migration_plan_is_guarded_and_write_heavy():
    plan = build_plan("migrate", "Rename User model to Account")

    assert plan.command == "migrate"
    assert plan.pattern == "guarded-migration"
    assert plan.verification_strategy == "patch-review"
    assert all("ownership" in unit.prompt.lower() for unit in plan.work_units)
