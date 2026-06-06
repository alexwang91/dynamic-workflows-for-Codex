# Dynamic Workflows For Codex v0.7 Plugin Skill Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the packaged Codex skill so installed users get clear dynamic workflow routing and safe adapter behavior.

**Architecture:** Keep skill content generated from `src/cdw/skill.py` and require the repo-local packaged skill to match that generator. Update plugin manifest metadata in `src/cdw/plugin_package.py` and the repo-local package copy.

**Tech Stack:** Python 3.10+, pytest, Codex plugin manifest, Markdown skill content.

---

## File Structure

- Modify `src/cdw/skill.py`: richer SKILL.md generator.
- Modify `.agents/plugins/plugins/dynamic-workflows-for-codex/skills/dynamic-workflows-for-codex/SKILL.md`: repo-local packaged skill copy.
- Modify `src/cdw/plugin_package.py`: version and metadata.
- Modify `.agents/plugins/plugins/dynamic-workflows-for-codex/.codex-plugin/plugin.json`: repo-local manifest copy.
- Modify `tests/test_skill.py`: generated skill assertions.
- Modify `tests/test_plugin_package.py`: metadata assertions and repo-local skill sync.
- Modify `README.md`, `CHANGELOG.md`, and `docs/evaluation.md`: v0.7 release notes.

### Task 1: Failing Tests

**Files:**
- Modify: `tests/test_skill.py`
- Modify: `tests/test_plugin_package.py`

- [ ] **Step 1: Add generated skill assertions**

Assert generated skill content contains:

- `## Trigger Routing`
- `## Operating Loop`
- `## Adapter Policy`
- `## Resume First`
- `cdw doctor --root <repo>`
- `--adapter codex-cli`
- `Do not ask for or assume the project author's API key`

- [ ] **Step 2: Add repo-local skill sync test**

Read `.agents/plugins/plugins/dynamic-workflows-for-codex/skills/dynamic-workflows-for-codex/SKILL.md`
and assert it equals `build_skill_content(skill_name="dynamic-workflows-for-codex")`.

- [ ] **Step 3: Add manifest metadata assertions**

Assert packaged plugin manifest version is `0.7.0` and long description includes
`doctor`, `codex-cli`, and `workflow specs`.

- [ ] **Step 4: Verify red**

```powershell
python -m pytest tests/test_skill.py tests/test_plugin_package.py -v
```

Expected: tests fail because current skill is still a short command reference
and manifest metadata is v0.6.

### Task 2: Skill Content

**Files:**
- Modify: `src/cdw/skill.py`
- Modify: `.agents/plugins/plugins/dynamic-workflows-for-codex/skills/dynamic-workflows-for-codex/SKILL.md`

- [ ] **Step 1: Rewrite generated skill**

Include sections:

- `## Trigger Routing`
- `## Operating Loop`
- `## Adapter Policy`
- `## Resume First`
- `## Command Map`
- `## Guardrails`

- [ ] **Step 2: Sync repo-local skill copy**

Copy the generated content with `skill_name="dynamic-workflows-for-codex"` into
the repo-local packaged skill.

- [ ] **Step 3: Run skill tests**

```powershell
python -m pytest tests/test_skill.py -v
```

Expected: generated and installed skill assertions pass.

### Task 3: Manifest And Docs

**Files:**
- Modify: `src/cdw/plugin_package.py`
- Modify: `.agents/plugins/plugins/dynamic-workflows-for-codex/.codex-plugin/plugin.json`
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/evaluation.md`
- Modify: `tests/test_plugin_package.py`

- [ ] **Step 1: Bump version to `0.7.0`**

Update package and plugin manifest versions.

- [ ] **Step 2: Improve marketplace metadata**

Mention clone readiness, `cdw doctor`, `codex-cli`, and reusable workflow specs.

- [ ] **Step 3: Update docs**

Add v0.7 behavior to README, changelog, and evaluation checklist.

### Task 4: Verification

**Files:**
- All changed files

- [ ] **Step 1: Run focused tests**

```powershell
python -m pytest tests/test_skill.py tests/test_plugin_package.py -v
```

- [ ] **Step 2: Validate plugin package**

```powershell
python C:\Users\Administrator\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py .agents\plugins\plugins\dynamic-workflows-for-codex
```

- [ ] **Step 3: Run full verification**

```powershell
python -m pytest -v
python -m cdw doctor
python -m cdw live-smoke
```

- [ ] **Step 4: Commit and push**

```powershell
git add src/cdw/skill.py .agents/plugins/plugins/dynamic-workflows-for-codex/skills/dynamic-workflows-for-codex/SKILL.md src/cdw/plugin_package.py .agents/plugins/plugins/dynamic-workflows-for-codex/.codex-plugin/plugin.json pyproject.toml README.md CHANGELOG.md docs/evaluation.md tests/test_skill.py tests/test_plugin_package.py docs/superpowers/specs/2026-06-06-dynamic-workflows-for-Codex-v0.7-plugin-skill-hardening.md docs/superpowers/plans/2026-06-06-dynamic-workflows-for-Codex-v0.7-plugin-skill-hardening.md
git commit -m "feat: harden plugin skill routing"
git push -u origin codex/plugin-skill-hardening-v0.7
```
