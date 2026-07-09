from radon.complexity import cc_visit
from radon.metrics import h_visit, mi_visit
from radon.raw import analyze


def analyze_file(source: str) -> dict:
    try:
        raw = analyze(source)
        mi = mi_visit(source, multi=True)
        halstead = h_visit(source)
        blocks = cc_visit(source)

        functions = [
            {
                "name": b.name,
                "type": b.__class__.__name__,
                "lineno": b.lineno,
                "endline": getattr(b, "endline", None),
                "complexity": b.complexity,
                "classname": getattr(b, "classname", None),
            }
            for b in blocks
        ]

        return {
            "parse_ok": True,
            "loc": raw.loc,
            "lloc": raw.lloc,
            "sloc": raw.sloc,
            "comments": raw.comments,
            "blank": raw.blank,
            "mi": round(mi, 2),
            "halstead_volume": round(halstead.total.volume, 2),
            "halstead_difficulty": round(halstead.total.difficulty, 2),
            "functions": functions,
            "max_complexity": max([f["complexity"] for f in functions], default=0),
            "avg_complexity": round(
                sum(f["complexity"] for f in functions) / len(functions), 2
            )
            if functions
            else 0,
        }
    except Exception as e:
        return {
            "parse_ok": False,
            "error": str(e),
            "loc": 0,
            "functions": [],
            "max_complexity": 0,
        }
