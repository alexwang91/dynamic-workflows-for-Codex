from __future__ import annotations

import fnmatch
import json
import re

from pydantic import ValidationError

from cdw.schemas import (
    BoundaryResult,
    BoundaryViolation,
    WorkflowSpecConstraints,
    WorkflowStage,
    WritePathIntent,
    WorkerResult,
)


_SECTION_RE = re.compile(
    r"^\s*(?:WRITE_PATHS|write paths|planned paths|paths)\s*:\s*(.*)$",
    re.IGNORECASE,
)
_CONTRACT_RE = re.compile(
    r"^\s*(?:WRITE_CONTRACT|write contract)\s*:\s*(.*)$",
    re.IGNORECASE,
)
_KNOWN_ACTIONS = {"create", "modify", "delete", "move", "rename", "unknown"}


def extract_declared_write_paths(text: str) -> list[str]:
    paths: list[str] = []
    in_section = False
    for line in text.splitlines():
        section_match = _SECTION_RE.match(line)
        if section_match:
            in_section = True
            paths.extend(_split_inline_paths(section_match.group(1)))
            continue

        if not in_section:
            continue

        stripped = line.strip()
        if not stripped:
            break
        path = _path_from_section_line(stripped)
        if path is None:
            break
        paths.append(path)

    return _unique(paths)


def check_stage_boundaries(
    constraints: WorkflowSpecConstraints,
    stage: WorkflowStage,
    results: list[WorkerResult],
) -> BoundaryResult:
    declared_write_paths = _structured_paths_from_results(results)
    contract_checks = _contract_checks_from_results(results)
    contract_required = constraints.requires_write_contract
    contract_found = bool(declared_write_paths)
    checked_paths = _unique(
        [
            *[intent.path for intent in declared_write_paths],
            *_declared_paths_from_results(results),
        ]
    )
    violations = [
        violation
        for path in checked_paths
        if (violation := _check_path(path, constraints)) is not None
    ]
    if contract_required and not contract_found:
        violations.insert(
            0,
            BoundaryViolation(
                path="<write-contract>",
                reason="missing_write_contract",
            ),
        )
    return BoundaryResult(
        stage_id=stage.id,
        status="failed" if violations else "passed",
        checked_paths=checked_paths,
        violations=violations,
        contract_required=contract_required,
        contract_found=contract_found,
        declared_write_paths=declared_write_paths,
        contract_checks=contract_checks,
    )


def _declared_paths_from_results(results: list[WorkerResult]) -> list[str]:
    paths: list[str] = []
    for result in results:
        paths.extend(extract_declared_write_paths(result.summary))
        paths.extend(extract_declared_write_paths(result.raw_output))
        for evidence in result.evidence:
            paths.extend(extract_declared_write_paths(evidence))
    return _unique(paths)


def _structured_paths_from_results(results: list[WorkerResult]) -> list[WritePathIntent]:
    paths: list[WritePathIntent] = []
    for result in results:
        paths.extend(extract_structured_write_paths(result.summary))
        paths.extend(extract_structured_write_paths(result.raw_output))
        for evidence in result.evidence:
            paths.extend(extract_structured_write_paths(evidence))
    return _unique_write_intents(paths)


def _contract_checks_from_results(results: list[WorkerResult]) -> list[str]:
    checks: list[str] = []
    for result in results:
        checks.extend(extract_write_contract_checks(result.summary))
        checks.extend(extract_write_contract_checks(result.raw_output))
        for evidence in result.evidence:
            checks.extend(extract_write_contract_checks(evidence))
    return _unique(checks)


def extract_structured_write_paths(text: str) -> list[WritePathIntent]:
    paths: list[WritePathIntent] = []
    for contract in _extract_contract_objects(text):
        paths.extend(_paths_from_contract(contract))
    return _unique_write_intents(paths)


def extract_write_contract_checks(text: str) -> list[str]:
    checks: list[str] = []
    for contract in _extract_contract_objects(text):
        if not isinstance(contract, dict):
            continue
        raw_checks = contract.get("checks", [])
        if isinstance(raw_checks, list):
            checks.extend(check for check in raw_checks if isinstance(check, str))
    return _unique(checks)


def _check_path(
    path: str,
    constraints: WorkflowSpecConstraints,
) -> BoundaryViolation | None:
    normalized = _normalize_declared_path(path)
    if normalized is None:
        return BoundaryViolation(path=path, reason="invalid_path")

    forbidden_pattern = _matching_pattern(normalized, constraints.forbidden_paths)
    if forbidden_pattern is not None:
        return BoundaryViolation(
            path=normalized,
            reason="forbidden",
            pattern=forbidden_pattern,
        )

    if constraints.allowed_paths:
        allowed_pattern = _matching_pattern(normalized, constraints.allowed_paths)
        if allowed_pattern is None:
            return BoundaryViolation(
                path=normalized,
                reason="outside_allowed_paths",
                pattern=", ".join(constraints.allowed_paths),
            )
    return None


def _extract_contract_objects(text: str) -> list[object]:
    lines = text.splitlines()
    contracts: list[object] = []
    for index, line in enumerate(lines):
        match = _CONTRACT_RE.match(line)
        if match is None:
            continue
        parsed = _parse_contract_json(lines, index + 1, match.group(1))
        if parsed is not None:
            contracts.append(parsed)
    return contracts


def _parse_contract_json(
    lines: list[str],
    start_index: int,
    inline: str,
) -> object | None:
    fragments: list[str] = []
    if inline.strip():
        inline_json = _strip_json_fence(inline.strip())
        parsed_inline = _try_parse_json(inline_json)
        if parsed_inline is not None:
            return parsed_inline
        fragments.append(inline_json)

    for line in lines[start_index:]:
        stripped = line.strip()
        if stripped.startswith("```"):
            continue
        if not fragments and not stripped:
            continue
        fragments.append(line)
        candidate = "\n".join(fragments).strip()
        parsed = _try_parse_json(candidate)
        if parsed is not None:
            return parsed
        if not stripped and fragments:
            return None
    return _try_parse_json("\n".join(fragments).strip())


def _try_parse_json(candidate: str) -> object | None:
    if not candidate:
        return None
    try:
        return json.loads(_strip_json_fence(candidate))
    except json.JSONDecodeError:
        return None


def _strip_json_fence(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("```json"):
        stripped = stripped.removeprefix("```json").strip()
    if stripped.startswith("```"):
        stripped = stripped.removeprefix("```").strip()
    if stripped.endswith("```"):
        stripped = stripped.removesuffix("```").strip()
    return stripped


def _paths_from_contract(contract: object) -> list[WritePathIntent]:
    raw_paths: object
    if isinstance(contract, dict):
        raw_paths = contract.get("paths", [])
    else:
        raw_paths = contract

    if not isinstance(raw_paths, list):
        return []

    paths = []
    for raw_path in raw_paths:
        intent = _write_intent_from_raw(raw_path)
        if intent is not None:
            paths.append(intent)
    return paths


def _write_intent_from_raw(raw_path: object) -> WritePathIntent | None:
    if isinstance(raw_path, str):
        return WritePathIntent(path=raw_path)
    if not isinstance(raw_path, dict):
        return None

    path = raw_path.get("path") or raw_path.get("file")
    if not isinstance(path, str):
        return None
    action = raw_path.get("action", "modify")
    if not isinstance(action, str) or action not in _KNOWN_ACTIONS:
        action = "unknown"
    reason = raw_path.get("reason", "")
    if not isinstance(reason, str):
        reason = ""
    try:
        return WritePathIntent(path=path, action=action, reason=reason)
    except ValidationError:
        return None


def _normalize_declared_path(path: str) -> str | None:
    normalized = path.strip().replace("\\", "/")
    normalized = re.sub(r"/+", "/", normalized)
    if re.match(r"^[A-Za-z]:/", normalized) or normalized.startswith("/"):
        return None
    parts = [part for part in normalized.split("/") if part not in {"", "."}]
    if any(part == ".." for part in parts):
        return None
    if not parts:
        return None
    return "/".join(parts)


def _matching_pattern(path: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        normalized_pattern = pattern.strip().replace("\\", "/")
        if fnmatch.fnmatchcase(path, normalized_pattern):
            return pattern
    return None


def _split_inline_paths(value: str) -> list[str]:
    if not value.strip():
        return []
    return [_clean_path_token(part) for part in value.split(",") if part.strip()]


def _path_from_section_line(line: str) -> str | None:
    has_list_marker = re.match(r"^(?:[-*]|\d+[.)])\s*", line) is not None
    cleaned = re.sub(r"^(?:[-*]|\d+[.)])\s*", "", line).strip()
    has_path_label = re.match(r"^(?:path|file)\s*:\s*", cleaned, re.IGNORECASE)
    cleaned = re.sub(r"^(?:path|file)\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = _clean_path_token(cleaned)
    if not cleaned:
        return None
    if not has_list_marker and not has_path_label and not _looks_like_path(cleaned):
        return None
    return cleaned


def _looks_like_path(value: str) -> bool:
    if ":" in value and not re.match(r"^[A-Za-z]:[\\/]", value):
        return False
    if "/" in value or "\\" in value:
        return True
    if any(character in value for character in "*?[]"):
        return True
    return not any(character.isspace() for character in value)


def _clean_path_token(value: str) -> str:
    cleaned = value.strip().strip("`'\"")
    cleaned = cleaned.split("#", 1)[0].strip()
    return cleaned.rstrip(".,;")


def _unique(paths: list[str]) -> list[str]:
    seen = set()
    unique_paths = []
    for path in paths:
        if path and path not in seen:
            seen.add(path)
            unique_paths.append(path)
    return unique_paths


def _unique_write_intents(paths: list[WritePathIntent]) -> list[WritePathIntent]:
    seen = set()
    unique_paths = []
    for path in paths:
        key = (path.path, path.action, path.reason)
        if key not in seen:
            seen.add(key)
            unique_paths.append(path)
    return unique_paths
