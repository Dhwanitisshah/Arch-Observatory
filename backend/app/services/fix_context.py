import hashlib

from app.config import settings
from app.db import db


def compute_smell_key(smell: dict) -> str:
    """Deterministic hash of a smell's identity so the same smell in the same
    run always maps to one fix_suggestions cache entry."""
    raw = f"{smell.get('type')}|{smell.get('target')}|{smell.get('path')}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


async def build_fix_context(run: dict, smell: dict) -> str:
    smell_type = smell.get("type")
    if smell_type == "complexity_hotspot":
        return await _function_context(run, smell)
    if smell_type == "god_class":
        return await _file_context(run, smell)
    if smell_type in ("cyclic_dependency", "painful_coupling"):
        return _graph_context(run, smell)
    return _header(smell)


def _header(smell: dict) -> list[str]:
    metrics = smell.get("metrics", {})
    return [
        f"Smell: {smell.get('title')}",
        f"Target: {smell.get('target')}",
        f"Metrics: {metrics}",
    ]


def _cap_lines(lines: list[str]) -> str:
    return "\n".join(lines[: settings.FIX_MAX_SPAN_LINES])


async def _function_context(run: dict, smell: dict) -> str:
    path = smell.get("path")
    target = smell.get("target", "")
    fn_label = target.split("::")[-1] if "::" in target else target
    name = fn_label.split(".")[-1]
    classname = fn_label.split(".")[0] if "." in fn_label else None

    span = None
    doc = await db["code_spans"].find_one({"run_id": run.get("_id")})
    if doc:
        for fs in doc.get("function_spans", []):
            if fs["path"] == path and fs["name"] == name and fs.get("classname") == classname:
                span = fs
                break

    lines = _header(smell)
    if span:
        source_lines = span["source"].splitlines()[: settings.FIX_MAX_SPAN_LINES]
        lines.append(f"\nSource ({span['path']}, function {span['name']}):")
        lines.append("```python")
        lines.extend(source_lines)
        lines.append("```")
    else:
        lines.append("\n(Original source for this function is no longer available.)")
    return _cap_lines(lines)


async def _file_context(run: dict, smell: dict) -> str:
    path = smell.get("path")

    span = None
    doc = await db["code_spans"].find_one({"run_id": run.get("_id")})
    if doc:
        for fs in doc.get("file_spans", []):
            if fs["path"] == path:
                span = fs
                break

    lines = _header(smell)
    if span:
        source_lines = span["source"].splitlines()[: settings.FIX_MAX_SPAN_LINES]
        lines.append(f"\nSource ({span['path']}):")
        lines.append("```python")
        lines.extend(source_lines)
        lines.append("```")
    else:
        lines.append("\n(Original source for this file is no longer available.)")
    return _cap_lines(lines)


def _graph_context(run: dict, smell: dict) -> str:
    metrics = smell.get("metrics", {})
    lines = _header(smell)

    if smell.get("type") == "cyclic_dependency":
        members = metrics.get("members") or [m.strip() for m in smell.get("target", "").split(",")]
        lines.append(f"\nCycle members ({len(members)}): {', '.join(members)}")
        edges = [
            e
            for e in run.get("dependency_edges", [])
            if e.get("source") in members and e.get("target") in members
        ]
        if edges:
            lines.append("Edges within the cycle:")
            for e in edges:
                lines.append(f"  {e['source']} -> {e['target']}")
    else:
        module = smell.get("target")
        lines.append(f"\nAfferent coupling (Ca): {metrics.get('ca')}")
        lines.append(f"Instability (I): {metrics.get('instability')}")
        edges = [
            e
            for e in run.get("dependency_edges", [])
            if e.get("source") == module or e.get("target") == module
        ]
        if edges:
            lines.append("Related dependency edges:")
            for e in edges:
                lines.append(f"  {e['source']} -> {e['target']}")

    return _cap_lines(lines)
