from statistics import mean

from app.config import settings

SMELL_TYPES = ("god_class", "complexity_hotspot", "cyclic_dependency", "painful_coupling")

# How much each smell type's severity contributes to the health-score penalty.
# A smell contributes (severity / 100) * weight penalty points; the sum across
# all smells is scaled and capped at 100, then subtracted from 100.
SEVERITY_WEIGHTS = {
    "god_class": 1.0,
    "complexity_hotspot": 0.5,
    "cyclic_dependency": 1.5,
    "painful_coupling": 1.0,
}
_PENALTY_SCALE = 5.0


def _get(obj, name, default=None):
    """Access a field on either a dict or an attribute-bearing object (pydantic model)."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _normalize(value: float, lo: float, hi: float) -> float:
    """Linearly map value from [lo, hi] to [0, 100], clamped. lo maps to 0, hi maps to 100."""
    if hi <= lo:
        return 100.0 if value >= hi else 0.0
    return max(0.0, min(100.0, (value - lo) / (hi - lo) * 100))


def _is_test_path(path: str) -> bool:
    """A file full of test functions is not a god class — it's just a big test suite."""
    if not path:
        return False
    segments = path.replace("\\", "/").split("/")
    return any(seg == "tests" or seg == "test" or seg.startswith("test_") for seg in segments)


def _god_class_smells(files: list, node_by_path: dict) -> list[dict]:
    smells = []
    for f in files:
        if not _get(f, "parse_ok", True):
            continue

        path = _get(f, "path")
        if _is_test_path(path):
            continue
        loc = _get(f, "loc", 0) or 0
        function_count = len(_get(f, "functions", []) or [])
        node = node_by_path.get(path)
        ce = _get(node, "ce", 0) if node else 0
        module = _get(node, "module", path) if node else path

        triggered = sum(
            [
                loc > settings.GOD_CLASS_LOC,
                function_count > settings.GOD_CLASS_METHODS,
                ce > settings.GOD_CLASS_CE,
            ]
        )
        if triggered < 2:
            continue

        ratio = mean(
            [
                loc / settings.GOD_CLASS_LOC,
                function_count / settings.GOD_CLASS_METHODS,
                ce / settings.GOD_CLASS_CE,
            ]
        )
        severity = _normalize(ratio, 1.0, 3.0)

        smells.append(
            {
                "type": "god_class",
                "severity": round(severity, 2),
                "target": module,
                "path": path,
                "title": f"God class: {module}",
                "detail": (
                    f"{loc} LOC, {function_count} methods, depends on {ce} modules "
                    "— doing too much."
                ),
                "metrics": {"loc": loc, "function_count": function_count, "ce": ce},
            }
        )

    return smells


def _complexity_hotspot_smells(files: list, node_by_path: dict) -> list[dict]:
    smells = []
    for f in files:
        if not _get(f, "parse_ok", True):
            continue

        path = _get(f, "path")
        mi = _get(f, "mi")
        node = node_by_path.get(path)
        module = _get(node, "module", path) if node else path

        for fn in _get(f, "functions", []) or []:
            complexity = _get(fn, "complexity", 0) or 0
            if complexity <= settings.HOTSPOT_CC:
                continue

            base = _normalize(complexity, settings.HOTSPOT_CC, settings.HOTSPOT_CC * 3)
            mi_penalty = 0.0
            if mi is not None and mi < settings.HOTSPOT_MI:
                mi_penalty = min(20.0, (settings.HOTSPOT_MI - mi) / settings.HOTSPOT_MI * 20)
            severity = min(100.0, base + mi_penalty)

            name = _get(fn, "name")
            classname = _get(fn, "classname")
            fn_label = f"{classname}.{name}" if classname else name

            smells.append(
                {
                    "type": "complexity_hotspot",
                    "severity": round(severity, 2),
                    "target": f"{module}::{fn_label}",
                    "path": path,
                    "title": f"Complexity hotspot: {fn_label}",
                    "detail": f"cyclomatic complexity {complexity} — hard to test, many branches.",
                    "metrics": {"complexity": complexity, "mi": mi},
                }
            )

    return smells


def _cyclic_dependency_smells(cycles: list, node_by_path_by_module: dict) -> list[dict]:
    smells = []
    for cycle in cycles:
        members = _get(cycle, "members", []) or []
        if len(members) <= 1:
            continue

        size = len(members)
        severity = _normalize(size, 2, 10)
        sorted_members = sorted(members)
        first_path = node_by_path_by_module.get(sorted_members[0], "")

        smells.append(
            {
                "type": "cyclic_dependency",
                "severity": round(severity, 2),
                "target": ", ".join(sorted_members),
                "path": first_path,
                "title": f"Import cycle ({size} modules)",
                "detail": f"{size} modules form an import cycle: {', '.join(sorted_members)}.",
                "metrics": {"size": size, "members": sorted_members},
            }
        )

    return smells


def _painful_coupling_smells(nodes: list) -> list[dict]:
    smells = []
    for node in nodes:
        ca = _get(node, "ca", 0) or 0
        instability = _get(node, "instability", 0) or 0

        if not (ca > settings.PAINFUL_CA and instability > settings.UNSTABLE_I):
            continue

        product = ca * instability
        threshold_product = settings.PAINFUL_CA * settings.UNSTABLE_I
        severity = _normalize(product, threshold_product, threshold_product * 3)

        module = _get(node, "module")
        path = _get(node, "path")

        smells.append(
            {
                "type": "painful_coupling",
                "severity": round(severity, 2),
                "target": module,
                "path": path,
                "title": f"Painful coupling: {module}",
                "detail": (
                    f"{ca} modules depend on this, but it has instability {instability}."
                ),
                "metrics": {"ca": ca, "instability": instability},
            }
        )

    return smells


def detect_smells(run) -> list[dict]:
    """Synthesize smells from metrics + dependency data already computed in Phases 2-3.

    `run` may be a dict or an attribute-bearing object exposing: files,
    dependency_nodes, cycles.
    """
    files = _get(run, "files", []) or []
    nodes = _get(run, "dependency_nodes", []) or []
    cycles = _get(run, "cycles", []) or []

    node_by_path = {_get(n, "path"): n for n in nodes}
    node_path_by_module = {_get(n, "module"): _get(n, "path") for n in nodes}

    smells = []
    smells.extend(_god_class_smells(files, node_by_path))
    smells.extend(_complexity_hotspot_smells(files, node_by_path))
    smells.extend(_cyclic_dependency_smells(cycles, node_path_by_module))
    smells.extend(_painful_coupling_smells(nodes))

    smells.sort(key=lambda s: s["severity"], reverse=True)
    return smells


def compute_smell_counts(smells: list[dict]) -> dict:
    counts = {t: 0 for t in SMELL_TYPES}
    for s in smells:
        counts[s["type"]] = counts.get(s["type"], 0) + 1
    return counts


def compute_health_score(smells: list[dict]) -> float:
    """100 minus a weighted penalty from smell severities, floored at 0.

    Each smell contributes (severity / 100) * SEVERITY_WEIGHTS[type] penalty
    points; the sum is scaled by _PENALTY_SCALE and capped at 100 before being
    subtracted from 100. This keeps a single mild smell from barely moving the
    score while a handful of severe ones can drive it to 0.
    """
    penalty = sum((s["severity"] / 100) * SEVERITY_WEIGHTS.get(s["type"], 1.0) for s in smells)
    penalty = min(100.0, penalty * _PENALTY_SCALE)
    return round(max(0.0, 100.0 - penalty), 2)
