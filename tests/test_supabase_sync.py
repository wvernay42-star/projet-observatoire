import json

import httpx
import respx

from pipeline import supabase_sync

BASE = supabase_sync.SUPABASE_URL + "/rest/v1"


@respx.mock
def test_push_replaces_all_queues(tmp_path):
    for kind in supabase_sync.KINDS:
        (tmp_path / f"{kind}.json").write_text(json.dumps({"generated_at": "2026-10-27T05:00:00+00:00",
                                                           "items": [{"id": kind + "-1"}]}), encoding="utf-8")
    route = respx.post(BASE + "/obs_queues").mock(return_value=httpx.Response(201))
    with supabase_sync.client() as c:
        assert supabase_sync.push(c, tmp_path) == {k: 1 for k in supabase_sync.KINDS}
    sent = json.loads(route.calls[0].request.content)
    assert [r["kind"] for r in sent] == list(supabase_sync.KINDS)
    assert "merge-duplicates" in route.calls[0].request.headers["Prefer"]


@respx.mock
def test_apply_uses_queues_seen_by_admin_then_removes_decisions(monkeypatch):
    decisions = [{"item_id": "a-c1", "kind": "attributions", "value": "Q1", "decided_at": "2026-10-27T08:00:00+00:00"},
                 {"item_id": 'p-"x"', "kind": "parties", "value": "none", "decided_at": "2026-10-27T08:01:00+00:00"}]
    respx.get(BASE + "/obs_decisions").mock(return_value=httpx.Response(200, json=decisions))
    respx.get(BASE + "/obs_queues").mock(return_value=httpx.Response(200, json=[
        {"kind": "attributions", "items": [{"id": "a-c1", "candidates": [{"id": "Q1"}], "reviews": []}]}]))
    deleted = respx.delete(BASE + "/obs_decisions").mock(return_value=httpx.Response(204))
    seen = {}
    monkeypatch.setattr(supabase_sync, "apply", lambda d, q: seen.update(d=d, q=q) or {"skipped": 1})
    with supabase_sync.client() as c:
        result = supabase_sync.apply_decisions(c)
    assert result == {"decisions": 2, "skipped": 1}
    assert seen["q"]["attributions"]["items"][0]["id"] == "a-c1"
    assert deleted.calls[0].request.url.params["item_id"] == 'in.("a-c1","p-\\"x\\"")'


@respx.mock
def test_nothing_to_apply():
    respx.get(BASE + "/obs_decisions").mock(return_value=httpx.Response(200, json=[]))
    with supabase_sync.client() as c:
        assert supabase_sync.apply_decisions(c) == {"decisions": 0}
