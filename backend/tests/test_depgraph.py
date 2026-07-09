import os

from app.services.depgraph import build_dependency_graph

REPO_ROOT = os.path.join("repo")


def _files(sources: dict) -> list[dict]:
    return [{"path": os.path.join(REPO_ROOT, rel_path), "source": source} for rel_path, source in sources.items()]


def test_simple_import_creates_edge_and_coupling():
    sources = {
        "a.py": "import b\n",
        "b.py": "x = 1\n",
    }
    result = build_dependency_graph(_files(sources), REPO_ROOT)

    assert {"source": "a", "target": "b"} in result["edges"]

    nodes_by_module = {n["module"]: n for n in result["nodes"]}
    assert nodes_by_module["b"]["ca"] == 1
    assert nodes_by_module["a"]["ce"] == 1


def test_three_module_cycle_detected_as_single_scc():
    sources = {
        "a.py": "import b\n",
        "b.py": "import c\n",
        "c.py": "import a\n",
    }
    result = build_dependency_graph(_files(sources), REPO_ROOT)

    assert result["scc_count"] == 1
    assert len(result["cycles"]) == 1
    cycle = result["cycles"][0]
    assert sorted(cycle["members"]) == ["a", "b", "c"]
    assert len(cycle["concrete_cycles"]) > 0


def test_stdlib_import_creates_no_edge():
    sources = {
        "a.py": "import os\n",
    }
    result = build_dependency_graph(_files(sources), REPO_ROOT)

    assert result["edges"] == []
    assert result["edge_count"] == 0


def test_relative_import_resolves_to_sibling_module():
    sources = {
        "pkg/__init__.py": "",
        "pkg/a.py": "from . import sibling\n",
        "pkg/sibling.py": "x = 1\n",
    }
    result = build_dependency_graph(_files(sources), REPO_ROOT)

    assert {"source": "pkg.a", "target": "pkg.sibling"} in result["edges"]


def test_instability_only_importer_is_fully_instable():
    sources = {
        "a.py": "import b\n",
        "b.py": "x = 1\n",
    }
    result = build_dependency_graph(_files(sources), REPO_ROOT)

    nodes_by_module = {n["module"]: n for n in result["nodes"]}
    assert nodes_by_module["a"]["instability"] == 1.0
    assert nodes_by_module["b"]["instability"] == 0.0
