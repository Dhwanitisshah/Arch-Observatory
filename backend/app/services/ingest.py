import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone

from bson import ObjectId

from app.config import settings
from app.db import db
from app.services import metrics
from app.services.depgraph import build_dependency_graph
from app.services.smells import compute_health_score, compute_smell_counts, detect_smells


class IngestError(Exception):
    pass


async def ingest_repo(run_id: str) -> None:
    runs = db["analysis_runs"]
    repos = db["repos"]

    run = await runs.find_one({"_id": ObjectId(run_id)})
    if run is None:
        return

    repo = await repos.find_one({"_id": ObjectId(run["repo_id"])})
    if repo is None:
        await runs.update_one(
            {"_id": ObjectId(run_id)},
            {
                "$set": {
                    "status": "failed",
                    "error": "Repo not found",
                    "finished_at": datetime.now(timezone.utc),
                }
            },
        )
        return

    await runs.update_one(
        {"_id": ObjectId(run_id)},
        {"$set": {"status": "running", "started_at": datetime.now(timezone.utc)}},
    )

    url = repo["url"]
    tmp = tempfile.mkdtemp(prefix="archobs_")

    try:
        _clone(url, tmp)
        total_file_count = _enforce_size_limit(tmp)
        files = _collect_py_files(tmp)
        aggregates = _compute_aggregates(files)
        dependency_aggregates = _compute_dependency_graph(tmp, files)
        smell_aggregates = _compute_smells(files, dependency_aggregates)

        await runs.update_one(
            {"_id": ObjectId(run_id)},
            {
                "$set": {
                    "status": "done",
                    "py_file_count": len(files),
                    "total_file_count": total_file_count,
                    "files": files,
                    "finished_at": datetime.now(timezone.utc),
                    **aggregates,
                    **dependency_aggregates,
                    **smell_aggregates,
                }
            },
        )
    except Exception as e:
        await runs.update_one(
            {"_id": ObjectId(run_id)},
            {
                "$set": {
                    "status": "failed",
                    "error": str(e),
                    "finished_at": datetime.now(timezone.utc),
                }
            },
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _clone(url: str, dest: str) -> None:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_ASKPASS"] = "echo"
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--single-branch", "--no-tags", url, dest],
            timeout=settings.CLONE_TIMEOUT_SECONDS,
            env=env,
            capture_output=True,
        )
    except subprocess.TimeoutExpired as e:
        raise IngestError(f"git clone timed out after {settings.CLONE_TIMEOUT_SECONDS}s") from e

    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
        raise IngestError(f"git clone failed: {stderr.strip()}")


def _enforce_size_limit(root: str) -> int:
    total_size = 0
    total_files = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for filename in filenames:
            path = os.path.join(dirpath, filename)
            if os.path.islink(path):
                continue
            try:
                total_size += os.path.getsize(path)
            except OSError:
                continue
            total_files += 1

    if total_size > settings.MAX_REPO_SIZE_MB * 1024 * 1024:
        raise IngestError(f"Repo exceeds max size of {settings.MAX_REPO_SIZE_MB}MB")
    if total_files > settings.MAX_FILE_COUNT:
        raise IngestError(f"Repo exceeds max file count of {settings.MAX_FILE_COUNT}")

    return total_files


def _collect_py_files(root: str) -> list[dict]:
    root_real = os.path.realpath(root)
    files = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]

        for filename in filenames:
            if not filename.endswith(".py"):
                continue

            path = os.path.join(dirpath, filename)

            if os.path.islink(path):
                continue

            real_path = os.path.realpath(path)
            if not (real_path == root_real or real_path.startswith(root_real + os.sep)):
                continue

            if len(files) >= settings.MAX_PY_FILE_COUNT:
                raise IngestError(f"Repo exceeds max Python file count of {settings.MAX_PY_FILE_COUNT}")

            with open(path, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()
            loc = len(source.splitlines())

            rel_path = os.path.relpath(path, root).replace(os.sep, "/")
            entry = {"path": rel_path, "loc": loc}
            entry.update(metrics.analyze_file(source))
            files.append(entry)

    return files


def _compute_dependency_graph(root: str, files: list[dict]) -> dict:
    files_with_sources = []
    for f in files:
        if not f.get("parse_ok"):
            continue
        abs_path = os.path.join(root, f["path"].replace("/", os.sep))
        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
                source = fh.read()
        except OSError:
            continue
        files_with_sources.append({"path": abs_path, "source": source})

    graph = build_dependency_graph(files_with_sources, root)

    nodes = graph["nodes"]
    most_depended_on = sorted(nodes, key=lambda n: n["ca"], reverse=True)[:10]
    most_depended_on = [{"module": n["module"], "ca": n["ca"]} for n in most_depended_on]

    most_unstable = [n for n in nodes if n["instability"] > 0.7 and n["ce"] > 0]
    most_unstable.sort(key=lambda n: n["instability"], reverse=True)
    most_unstable = [{"module": n["module"], "instability": n["instability"], "ce": n["ce"]} for n in most_unstable]

    return {
        "dependency_nodes": nodes,
        "dependency_edges": graph["edges"],
        "cycles": graph["cycles"],
        "scc_count": graph["scc_count"],
        "most_depended_on": most_depended_on,
        "most_unstable": most_unstable,
    }


def _compute_smells(files: list[dict], dependency_aggregates: dict) -> dict:
    smell_input = {
        "files": files,
        "dependency_nodes": dependency_aggregates["dependency_nodes"],
        "cycles": dependency_aggregates["cycles"],
    }
    smells = detect_smells(smell_input)

    return {
        "smells": smells,
        "smell_counts": compute_smell_counts(smells),
        "health_score": compute_health_score(smells),
    }


def _compute_aggregates(files: list[dict]) -> dict:
    parse_ok_files = [f for f in files if f.get("parse_ok")]
    unparseable_files = [f["path"] for f in files if not f.get("parse_ok")]

    total_functions = sum(len(f.get("functions", [])) for f in parse_ok_files)

    mi_values = [f["mi"] for f in parse_ok_files if "mi" in f]
    avg_mi = round(sum(mi_values) / len(mi_values), 2) if mi_values else 0

    high_complexity_functions = [
        {
            "path": f["path"],
            "name": fn["name"],
            "classname": fn.get("classname"),
            "complexity": fn["complexity"],
            "lineno": fn["lineno"],
        }
        for f in parse_ok_files
        for fn in f.get("functions", [])
        if fn["complexity"] > settings.CC_THRESHOLD
    ]
    high_complexity_functions.sort(key=lambda x: x["complexity"], reverse=True)

    return {
        "total_functions": total_functions,
        "avg_mi": avg_mi,
        "high_complexity_functions": high_complexity_functions,
        "unparseable_files": unparseable_files,
    }
