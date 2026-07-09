from app.services.smells import compute_health_score, detect_smells


def _file(path, loc=50, function_count=2, mi=80, extra_functions=None):
    functions = [
        {"name": f"fn{i}", "complexity": 2, "classname": None} for i in range(function_count)
    ]
    if extra_functions:
        functions.extend(extra_functions)
    return {
        "path": path,
        "parse_ok": True,
        "loc": loc,
        "mi": mi,
        "functions": functions,
    }


def _node(module, path, ca=0, ce=0, instability=0.0):
    return {"module": module, "path": path, "ca": ca, "ce": ce, "instability": instability}


def test_god_class_detected_for_large_highly_coupled_file():
    run = {
        "files": [_file("big.py", loc=1200, function_count=40)],
        "dependency_nodes": [_node("big", "big.py", ce=15)],
        "cycles": [],
    }

    smells = detect_smells(run)

    god_classes = [s for s in smells if s["type"] == "god_class"]
    assert len(god_classes) == 1
    assert god_classes[0]["path"] == "big.py"
    assert god_classes[0]["metrics"]["loc"] == 1200


def test_complexity_hotspot_detected_with_high_severity():
    run = {
        "files": [
            _file(
                "hot.py",
                function_count=0,
                extra_functions=[{"name": "do_it", "complexity": 25, "classname": None}],
            )
        ],
        "dependency_nodes": [_node("hot", "hot.py")],
        "cycles": [],
    }

    smells = detect_smells(run)

    hotspots = [s for s in smells if s["type"] == "complexity_hotspot"]
    assert len(hotspots) == 1
    assert hotspots[0]["severity"] > 60
    assert hotspots[0]["target"] == "hot::do_it"


def test_scc_of_four_produces_exactly_one_cyclic_dependency_smell():
    run = {
        "files": [],
        "dependency_nodes": [
            _node("a", "a.py"),
            _node("b", "b.py"),
            _node("c", "c.py"),
            _node("d", "d.py"),
        ],
        "cycles": [{"members": ["a", "b", "c", "d"], "concrete_cycles": []}],
    }

    smells = detect_smells(run)

    cyclic = [s for s in smells if s["type"] == "cyclic_dependency"]
    assert len(cyclic) == 1
    assert cyclic[0]["metrics"]["size"] == 4


def test_painful_coupling_detected_for_unstable_heavily_depended_module():
    run = {
        "files": [],
        "dependency_nodes": [_node("core", "core.py", ca=10, instability=0.9)],
        "cycles": [],
    }

    smells = detect_smells(run)

    painful = [s for s in smells if s["type"] == "painful_coupling"]
    assert len(painful) == 1
    assert painful[0]["target"] == "core"


def test_clean_file_has_no_smells_and_health_score_near_100():
    run = {
        "files": [_file("clean.py", loc=100, function_count=3)],
        "dependency_nodes": [_node("clean", "clean.py", ca=1, ce=1, instability=0.5)],
        "cycles": [],
    }

    smells = detect_smells(run)

    assert smells == []
    assert compute_health_score(smells) >= 99


def test_severity_ordering_higher_complexity_ranks_first():
    run = {
        "files": [
            _file(
                "mixed.py",
                function_count=0,
                extra_functions=[
                    {"name": "big_fn", "complexity": 30, "classname": None},
                    {"name": "small_fn", "complexity": 12, "classname": None},
                ],
            )
        ],
        "dependency_nodes": [_node("mixed", "mixed.py")],
        "cycles": [],
    }

    smells = detect_smells(run)
    hotspots = [s for s in smells if s["type"] == "complexity_hotspot"]

    assert hotspots[0]["target"] == "mixed::big_fn"
    assert hotspots[0]["severity"] > hotspots[1]["severity"]
