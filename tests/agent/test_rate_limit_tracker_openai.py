"""Tests for OpenAI-style rate limit header parsing."""

from agent.rate_limit_tracker import parse_rate_limit_headers


def test_parse_openai_reset_duration_strings():
    state = parse_rate_limit_headers(
        {
            "x-ratelimit-limit-requests": "500",
            "x-ratelimit-remaining-requests": "499",
            "x-ratelimit-reset-requests": "1s",
            "x-ratelimit-limit-tokens": "200000",
            "x-ratelimit-remaining-tokens": "123456",
            "x-ratelimit-reset-tokens": "6m0s",
            "x-ratelimit-limit-requests-1h": "10000",
            "x-ratelimit-remaining-requests-1h": "9999",
            "x-ratelimit-reset-requests-1h": "1h2m3s",
            "x-ratelimit-limit-tokens-1h": "5000000",
            "x-ratelimit-remaining-tokens-1h": "4999000",
            "x-ratelimit-reset-tokens-1h": "500ms",
        },
        provider="openai",
    )

    assert state is not None
    assert state.requests_min.reset_seconds == 1.0
    assert state.tokens_min.reset_seconds == 360.0
    assert state.requests_hour.reset_seconds == 3723.0
    assert state.tokens_hour.reset_seconds == 0.5
