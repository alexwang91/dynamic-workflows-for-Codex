from cdw.planner import build_plan
from cdw.workflow_spec import build_workflow_spec_bundle


def test_migration_plan_is_guarded_and_write_heavy():
    plan = build_plan("migrate", "Rename User model to Account")
    patch_plan = next(unit for unit in plan.work_units if unit.id == "patch-plan")

    assert plan.command == "migrate"
    assert plan.pattern == "guarded-migration"
    assert plan.verification_strategy == "patch-review"
    assert all("ownership" in unit.prompt.lower() for unit in plan.work_units)
    assert "WRITE_CONTRACT" in patch_plan.prompt
    assert '"paths"' in patch_plan.expected_output


def test_migration_workflow_spec_has_strict_boundaries():
    bundle = build_workflow_spec_bundle(
        build_plan("migrate", "Rename User model to Account")
    )
    assert bundle.procedure is not None

    inventory_stage = bundle.procedure.stages[0]
    review_stage = bundle.procedure.stages[1]

    assert bundle.constraints.write_policy == "write-heavy"
    assert bundle.constraints.requires_human_approval is True
    assert bundle.constraints.requires_write_contract is True
    assert inventory_stage.write_policy == "read-only"
    assert inventory_stage.produces == ["migration inventory"]
    assert review_stage.write_policy == "guarded"
    assert review_stage.depends_on == ["migration-inventory"]
    assert review_stage.consumes == ["migration inventory"]
    assert review_stage.produces == [
        "guarded patch plan",
        "migration risk review",
        "write path contract",
    ]
    assert review_stage.gate == "manual_review"
    assert review_stage.on_failure == "require_human"
