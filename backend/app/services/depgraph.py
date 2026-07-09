import ast
import os

import networkx as nx


def build_module_index(py_file_paths: list[str], repo_root: str) -> dict:
    """Map each file's dotted module name to its repo-relative path.

    Handles the common "src/" layout: if a top-level "src" directory exists
    among the given files, it is treated as a source root and stripped from
    module names. Otherwise module names are repo-root-relative.
    """
    rel_paths = [os.path.relpath(p, repo_root).replace(os.sep, "/") for p in py_file_paths]

    has_src_root = any(rp == "src" or rp.startswith("src/") for rp in rel_paths)

    index = {}
    for rel_path in rel_paths:
        module_rel = rel_path[4:] if has_src_root and rel_path.startswith("src/") else rel_path

        if module_rel.endswith("/__init__.py"):
            module_rel = module_rel[: -len("/__init__.py")]
        elif module_rel == "__init__.py":
            module_rel = ""
        elif module_rel.endswith(".py"):
            module_rel = module_rel[: -len(".py")]

        module_name = module_rel.replace("/", ".")
        if module_name:
            index[module_name] = rel_path

    return index


def extract_imports(source: str) -> list[dict]:
    """Extract raw import targets from source via AST only (never exec/import)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    entries = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                entries.append({"module": alias.name, "names": [], "level": 0})
        elif isinstance(node, ast.ImportFrom):
            entries.append(
                {
                    "module": node.module,
                    "names": [alias.name for alias in node.names],
                    "level": node.level,
                }
            )

    return entries


def resolve_import(entry: dict, current_module: str, module_index: dict) -> list[str]:
    """Resolve an import entry to internal module names present in module_index."""
    candidates = []

    if entry["level"] >= 1:
        base_parts = current_module.split(".")
        base_parts = base_parts[: -entry["level"]] if len(base_parts) >= entry["level"] else []
        base = ".".join(base_parts)

        if entry["module"]:
            target = f"{base}.{entry['module']}" if base else entry["module"]
            candidates.append(target)
            for name in entry["names"]:
                candidates.append(f"{target}.{name}")
        else:
            candidates.append(base)
            for name in entry["names"]:
                candidates.append(f"{base}.{name}" if base else name)
    else:
        if entry["module"]:
            candidates.append(entry["module"])
            for name in entry["names"]:
                candidates.append(f"{entry['module']}.{name}")
        else:
            for name in entry["names"]:
                candidates.append(name)

    candidates.sort(key=len, reverse=True)

    resolved = []
    for candidate in candidates:
        if candidate in module_index and candidate not in resolved:
            resolved.append(candidate)

    return resolved


def build_dependency_graph(files_with_sources: list[dict], repo_root: str) -> dict:
    """Build the internal module dependency graph and compute coupling metrics.

    files_with_sources: list of {"path": absolute_or_relative_path, "source": str}
    """
    py_file_paths = [f["path"] for f in files_with_sources]
    module_index = build_module_index(py_file_paths, repo_root)

    path_to_module = {path: module for module, path in module_index.items()}

    graph = nx.DiGraph()
    for module, rel_path in module_index.items():
        graph.add_node(module, path=rel_path)

    for file_entry in files_with_sources:
        rel_path = os.path.relpath(file_entry["path"], repo_root).replace(os.sep, "/")
        current_module = path_to_module.get(rel_path)
        if current_module is None:
            continue

        imports = extract_imports(file_entry["source"])
        for entry in imports:
            targets = resolve_import(entry, current_module, module_index)
            for target in targets:
                if target != current_module:
                    graph.add_edge(current_module, target)

    sccs = list(nx.strongly_connected_components(graph))
    cyclic_sccs = [scc for scc in sccs if len(scc) > 1]

    cycles = []
    for scc in cyclic_sccs:
        subgraph = graph.subgraph(scc)
        concrete_cycles = list(nx.simple_cycles(subgraph))
        cycles.append({"members": sorted(scc), "concrete_cycles": concrete_cycles})

    nodes = []
    for module in graph.nodes:
        ce = graph.out_degree(module)
        ca = graph.in_degree(module)
        instability = ce / (ca + ce) if (ca + ce) > 0 else 0
        nodes.append(
            {
                "module": module,
                "path": module_index[module],
                "ca": ca,
                "ce": ce,
                "instability": round(instability, 4),
            }
        )

    edges = [{"source": source, "target": target} for source, target in graph.edges]

    return {
        "nodes": nodes,
        "edges": edges,
        "cycles": cycles,
        "scc_count": len(cyclic_sccs),
        "edge_count": graph.number_of_edges(),
    }
