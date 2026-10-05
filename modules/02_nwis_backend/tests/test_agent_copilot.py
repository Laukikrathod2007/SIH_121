"""
Unit and integration tests for the Agentic Knowledge Copilot:
  - Tool schemas & dispatch layer (parity, shape validation, error handling)
  - Tool implementations against real in-memory store
  - Keyword search fallback (deterministic degradation when every Gemini key is offline)
  - Gemini key rotation (3-key fallback on rate-limit/auth/server errors)
  - Endpoint contract and SSE streaming response for POST /api/v2/agent/chat
"""
import pytest
from app.core import auth
from app.modules.nwis.agent.tools import (
    TOOL_SCHEMAS,
    TOOL_IMPLEMENTATIONS,
    execute_tool,
)
from app.modules.nwis.agent import orchestrator
from app.modules.nwis.agent.orchestrator import (
    run_keyword_fallback,
    check_gemini_reachable,
    _configured_keys,
    _is_retryable_on_another_key,
    GeminiUnavailable,
)
from app.modules.physics.db import service as physics_db_service
import app.modules.nwis.server as nwis_server


@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    """Ensure in-memory store is loaded, auth is bypassed for direct tests,
    and DB is unconfigured for fast in-memory execution."""
    monkeypatch.setattr(auth, "API_KEY", "")
    monkeypatch.setattr(nwis_server, "db_is_configured", lambda: False)
    monkeypatch.setattr(physics_db_service, "db_is_configured", lambda: False)
    if not nwis_server.store._loaded:
        nwis_server.store.load()


def test_tool_schemas_integrity():
    """Verify all expected tools are properly declared with schemas."""
    expected_tools = {
        "search_events",
        "get_well",
        "get_offset_ranking",
        "get_risk_corridors",
        "get_stratigraphic_alignment",
        "get_live_alerts",
        "get_alert_history",
    }
    schema_names = {s["function"]["name"] for s in TOOL_SCHEMAS}
    assert expected_tools == schema_names, f"Schema mismatch: {expected_tools ^ schema_names}"
    assert expected_tools == set(TOOL_IMPLEMENTATIONS.keys())

    for s in TOOL_SCHEMAS:
        fn = s["function"]
        assert "description" in fn and len(fn["description"]) > 10
        assert "parameters" in fn
        assert fn["parameters"]["type"] == "object"
        assert "properties" in fn["parameters"]


@pytest.mark.asyncio
async def test_execute_unknown_tool():
    """Unknown tool name returns clean error dictionary, never raises."""
    res = await execute_tool("nonexistent_tool_123", {"foo": "bar"})
    assert res.get("error") == "unknown_tool"
    assert "detail" in res


@pytest.mark.asyncio
async def test_execute_bad_arguments():
    """Calling tool with invalid arguments returns clean error dictionary."""
    res = await execute_tool("get_offset_ranking", {"wrong_arg": 123})
    assert res.get("error") == "bad_arguments"
    assert "detail" in res


@pytest.mark.asyncio
async def test_tool_search_events():
    """search_events returns trimmed results with all citation fields."""
    res = await execute_tool("search_events", {"query": "mud loss"})
    assert "results" in res
    assert "search_mode" in res
    assert "data_source" in res
    assert isinstance(res["results"], list)
    if res["results"]:
        first = res["results"][0]
        assert "event_id" in first
        assert "well_id" in first
        assert "event_type" in first
        assert "source_document" in first
        assert "source_page" in first
        assert "relevance_score" in first


@pytest.mark.asyncio
async def test_tool_get_well():
    """get_well returns well identity and metadata."""
    res = await execute_tool("get_well", {"well_id": "WELL-HGJ-012"})
    assert res.get("well_id") == "WELL-HGJ-012"
    assert "operator" in res
    assert "total_depth_md_m" in res
    assert "trajectory_stations" in res
    assert "formation_tops_count" in res
    assert "data_source" in res


@pytest.mark.asyncio
async def test_tool_get_well_not_found():
    """get_well with missing well returns honest not_found error."""
    res = await execute_tool("get_well", {"well_id": "NONEXISTENT-WELL-999"})
    assert res.get("error") == "not_found"


@pytest.mark.asyncio
async def test_tool_get_offset_ranking():
    """get_offset_ranking returns ranked offset wells with DORS scores."""
    res = await execute_tool("get_offset_ranking", {"well_id": "15/9-F-12", "depth": 2500.0})
    assert res.get("active_well_id") == "15/9-F-12"
    assert "dors_formula" in res
    assert "data_source" in res
    assert "rankings" in res
    assert len(res["rankings"]) > 0
    top = res["rankings"][0]
    assert "well_id" in top
    assert "dors_score" in top
    assert "distance_km" in top
    assert "component_scores" in top


@pytest.mark.asyncio
async def test_tool_get_risk_corridors():
    """get_risk_corridors returns depth corridors ahead of bit."""
    res = await execute_tool("get_risk_corridors", {"well_id": "15/9-F-12", "depth": 2500.0})
    assert res.get("well_id") == "15/9-F-12"
    assert "corridors" in res
    assert "total_corridors" in res
    assert "data_source" in res


@pytest.mark.asyncio
async def test_tool_get_stratigraphic_alignment():
    """get_stratigraphic_alignment returns flattened list of aligned wells."""
    res = await execute_tool("get_stratigraphic_alignment", {"well_id": "15/9-F-12", "depth": 2500.0})
    assert res.get("active_well_id") == "15/9-F-12"
    assert "alignment" in res
    assert isinstance(res["alignment"], list)
    if res["alignment"]:
        first = res["alignment"][0]
        assert "well_id" in first
        assert "formation" in first or "md_m" in first


@pytest.mark.asyncio
async def test_tool_get_live_alerts():
    """get_live_alerts returns live advisory status."""
    res = await execute_tool("get_live_alerts", {"well_id": "WELL-NHK-001"})
    assert res.get("well_id") == "WELL-NHK-001"
    assert "active_alert_count" in res
    assert "alerts" in res


@pytest.mark.asyncio
async def test_tool_get_alert_history():
    """get_alert_history returns tri-state status."""
    res = await execute_tool("get_alert_history", {"well_id": "WELL-NHK-001"})
    assert "status" in res


@pytest.mark.asyncio
async def test_run_keyword_fallback():
    """run_keyword_fallback yields tool events and grounded answer with citations."""
    events = []
    async for ev in run_keyword_fallback("kick in Barail", active_well_id="WELL-HGJ-012", active_depth=2450.0):
        events.append(ev)

    types = [e["type"] for e in events]
    assert "tool_call" in types
    assert "tool_result" in types
    assert "answer" in types

    answer = next(e for e in events if e["type"] == "answer")
    text = answer["text"]
    assert "Keyword Search" in text
    assert len(text) > 50


@pytest.mark.asyncio
async def test_check_gemini_reachable_returns_bool_with_no_keys_configured(monkeypatch):
    """No GEMINIKEY* env vars set -> reachable probe must return False, not raise."""
    monkeypatch.delenv("GEMINIKEY1", raising=False)
    monkeypatch.delenv("GEMINIKEY2", raising=False)
    monkeypatch.delenv("GEMINIKEY3", raising=False)
    reachable = await check_gemini_reachable()
    assert reachable is False


def test_configured_keys_reads_all_three_env_vars_and_skips_blank(monkeypatch):
    monkeypatch.setenv("GEMINIKEY1", "key-one")
    monkeypatch.delenv("GEMINIKEY2", raising=False)
    monkeypatch.setenv("GEMINIKEY3", "  ")  # blank/whitespace-only must be skipped, not sent as a key
    assert _configured_keys() == ["key-one"]


def test_configured_keys_empty_when_none_set(monkeypatch):
    for name in ("GEMINIKEY1", "GEMINIKEY2", "GEMINIKEY3"):
        monkeypatch.delenv(name, raising=False)
    assert _configured_keys() == []


class _FakeAPIError(Exception):
    """Stands in for google.genai.errors.APIError without needing a real
    HTTP response object -- only .code is read by _is_retryable_on_another_key."""
    def __init__(self, code: int):
        self.code = code
        super().__init__(f"fake API error {code}")


def test_rate_limit_and_auth_and_server_errors_are_retryable_on_another_key(monkeypatch):
    from google.genai import errors as genai_errors

    # Patch the real APIError class check target with our fake that still
    # IS a genai_errors.APIError instance for isinstance() to accept, by
    # making the fake inherit from it directly instead.
    class FakeAPIError(genai_errors.APIError):
        def __init__(self, code: int):
            self.code = code
            self.status = None
            self.message = "fake"
            Exception.__init__(self, f"fake API error {code}")

    assert _is_retryable_on_another_key(FakeAPIError(429)) is True   # rate limit / quota
    assert _is_retryable_on_another_key(FakeAPIError(401)) is True   # bad/revoked key
    assert _is_retryable_on_another_key(FakeAPIError(403)) is True   # forbidden
    assert _is_retryable_on_another_key(FakeAPIError(500)) is True   # transient server error
    assert _is_retryable_on_another_key(FakeAPIError(400)) is False  # malformed request -- same on every key
    assert _is_retryable_on_another_key(ConnectionError("down")) is True
    assert _is_retryable_on_another_key(ValueError("not a network/API error")) is False


@pytest.mark.asyncio
async def test_gemini_generate_rotates_through_all_three_keys_then_raises(monkeypatch):
    """All three keys configured, all three fail with a retryable error ->
    GeminiUnavailable, having genuinely tried all three (not just the first)."""
    monkeypatch.setenv("GEMINIKEY1", "key-1")
    monkeypatch.setenv("GEMINIKEY2", "key-2")
    monkeypatch.setenv("GEMINIKEY3", "key-3")

    attempted_keys: list[str] = []

    class _FakeModels:
        async def generate_content(self, *, model, contents, config):
            raise ConnectionError("simulated down")

    class _FakeAio:
        def __init__(self):
            self.models = _FakeModels()

    class _FakeClient:
        def __init__(self, *, api_key):
            attempted_keys.append(api_key)
            self.aio = _FakeAio()

    monkeypatch.setattr(orchestrator.genai, "Client", _FakeClient)

    with pytest.raises(GeminiUnavailable):
        await orchestrator._gemini_generate([], with_tools=False)

    assert attempted_keys == ["key-1", "key-2", "key-3"]


@pytest.mark.asyncio
async def test_gemini_generate_succeeds_on_second_key_after_first_fails(monkeypatch):
    """key 1 rate-limited, key 2 succeeds -> returns key 2's response,
    never tries key 3."""
    monkeypatch.setenv("GEMINIKEY1", "key-1")
    monkeypatch.setenv("GEMINIKEY2", "key-2")
    monkeypatch.setenv("GEMINIKEY3", "key-3")

    attempted_keys: list[str] = []
    sentinel_response = object()

    class _FakeModels:
        def __init__(self, key):
            self._key = key

        async def generate_content(self, *, model, contents, config):
            if self._key == "key-1":
                raise ConnectionError("simulated down")
            return sentinel_response

    class _FakeAio:
        def __init__(self, key):
            self.models = _FakeModels(key)

    class _FakeClient:
        def __init__(self, *, api_key):
            attempted_keys.append(api_key)
            self.aio = _FakeAio(api_key)

    monkeypatch.setattr(orchestrator.genai, "Client", _FakeClient)

    result = await orchestrator._gemini_generate([], with_tools=False)
    assert result is sentinel_response
    assert attempted_keys == ["key-1", "key-2"]  # key-3 never attempted


@pytest.mark.asyncio
async def test_gemini_generate_raises_immediately_on_non_retryable_error(monkeypatch):
    """A malformed-request-style error (not retryable) must not burn
    through all three keys -- every key would fail identically."""
    monkeypatch.setenv("GEMINIKEY1", "key-1")
    monkeypatch.setenv("GEMINIKEY2", "key-2")

    attempted_keys: list[str] = []

    class _FakeModels:
        async def generate_content(self, *, model, contents, config):
            raise ValueError("malformed request, not a network/API error")

    class _FakeAio:
        def __init__(self):
            self.models = _FakeModels()

    class _FakeClient:
        def __init__(self, *, api_key):
            attempted_keys.append(api_key)
            self.aio = _FakeAio()

    monkeypatch.setattr(orchestrator.genai, "Client", _FakeClient)

    with pytest.raises(GeminiUnavailable):
        await orchestrator._gemini_generate([], with_tools=False)

    assert attempted_keys == ["key-1"]  # fails fast, never tries key-2


def test_agent_chat_empty_message_400():
    """POST /api/v2/agent/chat rejects empty message with 400."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.post("/api/v2/agent/chat", json={"message": "   "})
    assert resp.status_code == 400
