"""
Comprehensive Test Suite for Centralized Silent AI Gateway (Production Grade).
Tests:
1. Scenario 1: Primary provider succeeds immediately.
2. Scenario 2: Primary provider returns 429 -> silent failover + health score decrease.
3. Scenario 3: Cooldown skips degraded provider.
4. Scenario 4: Triple cascade failover across providers.
5. Scenario 5: All providers exhausted -> AIServiceUnavailable.
6. Scenario 6: Health score load sorting.
7. Scenario 7: Intra-provider model fallback.
8. Scenario 8: Request ID tracing & Idempotency Key injection.
9. Scenario 9: In-memory telemetry metrics.
"""

from unittest.mock import MagicMock, patch

import pytest
from app.core.ai_gateway import AIGateway, AIServiceUnavailable, Provider


@pytest.fixture
def mock_gateway():
    """Creates an isolated AIGateway instance for testing."""
    gw = AIGateway(default_cooldown_seconds=60.0)
    return gw


@pytest.mark.asyncio
async def test_scenario_1_primary_key_succeeds(mock_gateway):
    """Scenario 1: Groq#1 works. Expected: Uses Groq#1 only."""
    mock_providers = [
        Provider("Groq", "gsk_key1", "llama-3.3-70b-versatile", ["llama-3.3-70b-versatile"], "https://api.groq.com/test", "Groq#1", 1),
        Provider("Groq", "gsk_key2", "llama-3.3-70b-versatile", ["llama-3.3-70b-versatile"], "https://api.groq.com/test", "Groq#2", 2),
    ]

    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "{\"is_interview_mail\": true}"}}],
        "model": "llama-3.3-70b-versatile",
    }

    with patch.object(mock_gateway, "get_available_providers", return_value=mock_providers):
        with patch("httpx.AsyncClient.post", return_value=mock_resp) as mock_post:
            result = await mock_gateway.chat_completion(
                messages=[{"role": "user", "content": "Test prompt"}]
            )

            assert result["choices"][0]["message"]["content"] == "{\"is_interview_mail\": true}"
            assert mock_post.call_count == 1
            call_headers = mock_post.call_args[1]["headers"]
            assert call_headers["Authorization"] == "Bearer gsk_key1"
            assert "Idempotency-Key" in call_headers
            assert "X-Request-ID" in call_headers
            assert not mock_gateway.is_cooling(mock_providers[0])
            assert mock_gateway.get_health_score(mock_providers[0]) == 100


@pytest.mark.asyncio
async def test_scenario_2_silent_failover_on_429(mock_gateway):
    """Scenario 2: Groq#1 -> 429. Expected: Groq#2 succeeds silently; Groq#1 health score drops to 70."""
    mock_providers = [
        Provider("Groq", "gsk_key1", "llama-3.3-70b-versatile", ["llama-3.3-70b-versatile"], "https://api.groq.com/test", "Groq#1", 1),
        Provider("Groq", "gsk_key2", "llama-3.3-70b-versatile", ["llama-3.3-70b-versatile"], "https://api.groq.com/test", "Groq#2", 2),
    ]

    resp_429 = MagicMock(status_code=429, text="Rate limit reached")
    resp_200 = MagicMock(status_code=200, json=lambda: {
        "choices": [{"message": {"content": "{\"status\": \"Shortlisted\"}"}}],
        "model": "llama-3.3-70b-versatile",
    })

    with patch.object(mock_gateway, "get_available_providers", return_value=mock_providers):
        with patch("httpx.AsyncClient.post", side_effect=[resp_429, resp_200]) as mock_post:
            result = await mock_gateway.chat_completion(
                messages=[{"role": "user", "content": "Test prompt"}]
            )

            assert result["choices"][0]["message"]["content"] == "{\"status\": \"Shortlisted\"}"
            assert mock_post.call_count == 2
            # Groq#1 must be placed in cooldown and health score reduced by 30
            assert mock_gateway.is_cooling(mock_providers[0])
            assert mock_gateway.get_health_score(mock_providers[0]) == 70
            # Groq#2 must NOT be in cooldown
            assert not mock_gateway.is_cooling(mock_providers[1])
            assert mock_gateway.get_health_score(mock_providers[1]) == 100


@pytest.mark.asyncio
async def test_scenario_3_cooldown_skips_failed_key(mock_gateway):
    """Scenario 3: Groq#1 cooling. Expected: Skip directly to Groq#2."""
    mock_providers = [
        Provider("Groq", "gsk_key1", "llama-3.3-70b-versatile", ["llama-3.3-70b-versatile"], "https://api.groq.com/test", "Groq#1", 1),
        Provider("Groq", "gsk_key2", "llama-3.3-70b-versatile", ["llama-3.3-70b-versatile"], "https://api.groq.com/test", "Groq#2", 2),
    ]

    # Put Groq#1 in cooldown
    mock_gateway.record_cooldown(mock_providers[0], reason="Previous 429", delta_score=-30)
    assert mock_gateway.is_cooling(mock_providers[0])

    resp_200 = MagicMock(status_code=200, json=lambda: {
        "choices": [{"message": {"content": "Success on Groq#2"}}],
    })

    with patch.object(mock_gateway, "get_available_providers", return_value=mock_providers):
        with patch("httpx.AsyncClient.post", return_value=resp_200) as mock_post:
            result = await mock_gateway.chat_completion(
                messages=[{"role": "user", "content": "Test prompt"}]
            )

            assert result["choices"][0]["message"]["content"] == "Success on Groq#2"
            assert mock_post.call_count == 1
            call_headers = mock_post.call_args[1]["headers"]
            assert call_headers["Authorization"] == "Bearer gsk_key2"


@pytest.mark.asyncio
async def test_scenario_4_triple_cascade_failover(mock_gateway):
    """Scenario 4: Groq#1 -> 429, Groq#2 -> 503, OpenAI#1 -> Success."""
    mock_providers = [
        Provider("Groq", "gsk_key1", "llama-3.3-70b-versatile", ["llama-3.3-70b-versatile"], "https://api.groq.com/test", "Groq#1", 1),
        Provider("Groq", "gsk_key2", "llama-3.3-70b-versatile", ["llama-3.3-70b-versatile"], "https://api.groq.com/test", "Groq#2", 2),
        Provider("OpenAI", "sk_openai", "gpt-4o-mini", ["gpt-4o-mini"], "https://api.openai.com/test", "OpenAI#1", 3),
    ]

    resp_429 = MagicMock(status_code=429, text="Rate limit")
    resp_503 = MagicMock(status_code=503, text="Service unavailable")
    resp_200 = MagicMock(status_code=200, json=lambda: {"choices": [{"message": {"content": "OpenAI Succeeded"}}]})

    with patch.object(mock_gateway, "get_available_providers", return_value=mock_providers):
        with patch("httpx.AsyncClient.post", side_effect=[resp_429, resp_503, resp_200]) as mock_post:
            result = await mock_gateway.chat_completion(
                messages=[{"role": "user", "content": "Cascade test"}]
            )

            assert result["choices"][0]["message"]["content"] == "OpenAI Succeeded"
            assert mock_post.call_count == 3
            assert mock_gateway.is_cooling(mock_providers[0])
            assert mock_gateway.is_cooling(mock_providers[1])
            assert not mock_gateway.is_cooling(mock_providers[2])


@pytest.mark.asyncio
async def test_scenario_5_all_keys_exhausted_raises_error(mock_gateway):
    """Scenario 5: All providers fail -> AIServiceUnavailable raised."""
    mock_providers = [
        Provider("Groq", "gsk_key1", "llama-3.3-70b-versatile", ["llama-3.3-70b-versatile"], "https://api.groq.com/test", "Groq#1", 1),
        Provider("Groq", "gsk_key2", "llama-3.3-70b-versatile", ["llama-3.3-70b-versatile"], "https://api.groq.com/test", "Groq#2", 2),
    ]

    resp_429 = MagicMock(status_code=429, text="Rate limit")
    resp_500 = MagicMock(status_code=500, text="Internal server error")

    with patch.object(mock_gateway, "get_available_providers", return_value=mock_providers):
        with patch("httpx.AsyncClient.post", side_effect=[resp_429, resp_500]):
            with pytest.raises(AIServiceUnavailable) as exc_info:
                await mock_gateway.chat_completion(
                    messages=[{"role": "user", "content": "Test fail"}]
                )

            assert "All configured AI providers failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_scenario_6_health_scoring_load_sorting(mock_gateway):
    """Scenario 6: Health scoring sorts healthier providers ahead of degraded ones."""
    p1 = Provider("Groq", "gsk_key1", "llama-3.3-70b-versatile", ["llama-3.3-70b-versatile"], "https://api.groq.com/test", "Groq#1", 1)
    p2 = Provider("Groq", "gsk_key2", "llama-3.3-70b-versatile", ["llama-3.3-70b-versatile"], "https://api.groq.com/test", "Groq#2", 2)

    # Set Groq#1 health score to 50, Groq#2 to 95 (and clear cooldowns)
    mock_gateway._health_scores["Groq#1"] = 50
    mock_gateway._health_scores["Groq#2"] = 95

    resp_200 = MagicMock(status_code=200, json=lambda: {
        "choices": [{"message": {"content": "Health score prioritized Groq#2"}}],
    })

    with patch.object(mock_gateway, "get_available_providers", return_value=[p1, p2]):
        with patch("httpx.AsyncClient.post", return_value=resp_200) as mock_post:
            result = await mock_gateway.chat_completion(
                messages=[{"role": "user", "content": "Health test"}]
            )

            assert result["choices"][0]["message"]["content"] == "Health score prioritized Groq#2"
            assert mock_post.call_count == 1
            call_headers = mock_post.call_args[1]["headers"]
            # Must have routed to Groq#2 because score 95 > 50
            assert call_headers["Authorization"] == "Bearer gsk_key2"


@pytest.mark.asyncio
async def test_scenario_7_intra_provider_model_fallback(mock_gateway):
    """Scenario 7: 70B model returns 503 -> tries 8B model on same key and succeeds."""
    p1 = Provider(
        "Groq", "gsk_key1", "llama-3.3-70b-versatile",
        ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
        "https://api.groq.com/test", "Groq#1", 1
    )

    resp_503 = MagicMock(status_code=503, text="Model overloaded")
    resp_200 = MagicMock(status_code=200, json=lambda: {
        "choices": [{"message": {"content": "8B model succeeded"}}],
    })

    with patch.object(mock_gateway, "get_available_providers", return_value=[p1]):
        with patch("httpx.AsyncClient.post", side_effect=[resp_503, resp_200]) as mock_post:
            result = await mock_gateway.chat_completion(
                messages=[{"role": "user", "content": "Model fallback test"}]
            )

            assert result["choices"][0]["message"]["content"] == "8B model succeeded"
            assert mock_post.call_count == 2
            # First call used 70B
            first_payload = mock_post.call_args_list[0][1]["json"]
            assert first_payload["model"] == "llama-3.3-70b-versatile"
            # Second call used 8B fallback on same key
            second_payload = mock_post.call_args_list[1][1]["json"]
            assert second_payload["model"] == "llama-3.1-8b-instant"


@pytest.mark.asyncio
async def test_scenario_8_telemetry_metrics(mock_gateway):
    """Scenario 8: Telemetry metrics track total requests, successes, latencies, and health scores."""
    p1 = Provider("Groq", "gsk_key1", "llama-3.3-70b-versatile", ["llama-3.3-70b-versatile"], "https://api.groq.com/test", "Groq#1", 1)

    resp_200 = MagicMock(status_code=200, json=lambda: {
        "choices": [{"message": {"content": "Metric test"}}],
    })

    with patch.object(mock_gateway, "get_available_providers", return_value=[p1]):
        with patch("httpx.AsyncClient.post", return_value=resp_200):
            await mock_gateway.chat_completion(
                messages=[{"role": "user", "content": "Metric test"}],
                request_id="trace123",
            )

    telemetry = mock_gateway.get_telemetry()
    assert telemetry["total_requests"] >= 1
    assert "Groq#1" in telemetry["provider_successes"]
    assert telemetry["health_scores"]["Groq#1"] == 100
    assert "Groq#1" in telemetry["average_latency_ms"]
