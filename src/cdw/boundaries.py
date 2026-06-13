from __future__ import annotations

import fnmatch
import re

from cdw.schemas import (
    BoundaryResult,
    BoundaryViolation,
    WorkflowSpecConstraints,
    WorkflowStage,
    WorkerResult,
)


_SECTION_RE = re.compile(
    r"^\s*(?:WRITE_PATHS|write paths|planned paths|paths)\s*:\s*(.*)$",
    re.IGNORECASE,
)


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
    checked_paths = _declared_paths_from_results(results)
    violations = [
        violation
        for path in checked_paths
        if (violation := _check_path(path, constraints)) is not None
    ]
    return BoundaryResult(
        stage_id=stage.id,
        status="failed" if violations else "passed",
        checked_paths=checked_paths,
        violations=violations,
    )


def _declared_paths_from_results(results: list[WorkerResult]) -> list[str]:
    paths: list[str] = []
    for result in results:
        paths.extend(extract_declared_write_paths(result.summary))
        paths.extend(extract_declared_write_paths(result.raw_output))
        for evidence in result.evidence:
            paths.extend(extract_declared_write_paths(evidence))
    return _unique(paths)


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
