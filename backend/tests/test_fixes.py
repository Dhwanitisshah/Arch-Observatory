from datetime import datetime, timezone

import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.config import settings
from app.routers.fixes import FixRequest, suggest_fix
from app.services.fix_context import build_fix_context, compute_smell_key

HOTSPOT_SMELL = {
    "type": "complexity_hotspot",
    "severity": 80,
    "target": "pkg.mod::MyClass.big_fn",
    "path": "pkg/mod.py",
    "title": "Complexity hotspot: MyClass.big_fn",
    "detail": "cyclomatic complexity 15 — hard to test, many branches.",
    "metrics": {"complexity": 15, "mi": 40},
}


class FakeCollection:
    def __init__(self):
        self._docs = []

    async def find_one(self, query):
        for doc in self._docs:
            if all(doc.get(k) == v for k, v in query.items()):
                return doc
        return None

    async def update_one(self, query, update, upsert=False):
        for doc in self._docs:
            if all(doc.get(k) == v for k, v in query.items()):
                doc.update(update.get("$set", {}))
                return
        if upsert:
            self._docs.append({**query, **update.get("$set", {})})

    def insert(self, doc):
        self._docs.append(doc)


class FakeDB:
    def __init__(self):
        self._collections = {}

    def __getitem__(self, name):
        return self._collections.setdefault(name, FakeCollection())


def _make_run(smells):
    return {
        "_id": ObjectId(),
        "smells": smells,
        "dependency_edges": [],
        "created_at": datetime.now(timezone.utc),
    }


@pytest.fixture
def fake_db(monkeypatch):
    fake = FakeDB()
    monkeypatch.setattr("app.routers.fixes.db", fake)
    monkeypatch.setattr("app.services.fix_context.db", fake)
    return fake


def test_smell_key_is_stable_for_same_smell():
    a = compute_smell_key(HOTSPOT_SMELL)
    b = compute_smell_key(dict(HOTSPOT_SMELL))
    assert a == b


def test_smell_key_differs_for_different_smells():
    other = {**HOTSPOT_SMELL, "target": "pkg.mod::MyClass.other_fn"}
    assert compute_smell_key(HOTSPOT_SMELL) != compute_smell_key(other)


@pytest.mark.asyncio
async def test_fix_disabled_without_api_key(fake_db, monkeypatch):
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")
    run = _make_run([HOTSPOT_SMELL])
    fake_db["analysis_runs"].insert(run)

    body = FixRequest(type="complexity_hotspot", target=HOTSPOT_SMELL["target"], path=HOTSPOT_SMELL["path"])

    with pytest.raises(HTTPException) as exc:
        await suggest_fix(str(run["_id"]), body)
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_fix_cache_hit_does_not_call_llm_twice(fake_db, monkeypatch):
    monkeypatch.setattr(settings, "GROQ_API_KEY", "fake-key")

    calls = []

    def fake_generate_fix(smell, context):
        calls.append((smell, context))
        return "Extract the branching logic into a strategy object."

    monkeypatch.setattr("app.routers.fixes.generate_fix", fake_generate_fix)

    run = _make_run([HOTSPOT_SMELL])
    fake_db["analysis_runs"].insert(run)

    body = FixRequest(type="complexity_hotspot", target=HOTSPOT_SMELL["target"], path=HOTSPOT_SMELL["path"])

    res1 = await suggest_fix(str(run["_id"]), body)
    assert res1["cached"] is False

    res2 = await suggest_fix(str(run["_id"]), body)
    assert res2["cached"] is True
    assert res2["suggestion"] == res1["suggestion"]

    assert len(calls) == 1


@pytest.mark.asyncio
async def test_fix_not_found_returns_404(fake_db, monkeypatch):
    monkeypatch.setattr(settings, "GROQ_API_KEY", "fake-key")
    run = _make_run([HOTSPOT_SMELL])
    fake_db["analysis_runs"].insert(run)

    body = FixRequest(type="god_class", target="nope", path="nope.py")

    with pytest.raises(HTTPException) as exc:
        await suggest_fix(str(run["_id"]), body)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_build_fix_context_stays_within_line_cap(fake_db):
    run = _make_run([HOTSPOT_SMELL])
    run["_id"] = str(run["_id"])
    huge_source = "\n".join(f"line {i}" for i in range(500))

    fake_db["code_spans"].insert(
        {
            "run_id": run["_id"],
            "function_spans": [
                {
                    "path": HOTSPOT_SMELL["path"],
                    "name": "big_fn",
                    "classname": "MyClass",
                    "lineno": 1,
                    "endline": 500,
                    "source": huge_source,
                }
            ],
            "file_spans": [],
        }
    )

    context = await build_fix_context(run, HOTSPOT_SMELL)

    code_lines = [line for line in context.splitlines() if line.startswith("line ")]
    assert len(code_lines) <= settings.FIX_MAX_SPAN_LINES
    assert len(code_lines) > 0
