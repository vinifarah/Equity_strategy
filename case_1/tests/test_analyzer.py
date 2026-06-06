"""Integration tests for src/analyzer.py — all API calls are mocked."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import anthropic
import pytest

from src.analyzer import _call_llm, _get_client, _parse_json_from_response, analyze_transcript
from src.models import EarningsCallAnalysis


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_response(text: str) -> MagicMock:
    """Build a mock that mimics client.messages.create() return value."""
    block = MagicMock()
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


def _minimal_analysis_json() -> str:
    """Return the minimal valid JSON that analyze_transcript expects from the LLM."""
    data = {
        "company": "Petrobras",
        "ticker": "PETR4",
        "quarter": "4T24",
        "call_date": "2025-02-19",
        "management_tone": {
            "overall_sentiment": "cautious",
            "confidence_score": 7,
            "justification": "Management is cautious on dividends.",
            "supporting_excerpts": [
                {"quote": "We remain committed to 45%.", "speaker": "CFO", "interpretation": "Defensive."},
                {"quote": "Production was record-breaking.", "speaker": "CEO", "interpretation": "Confident."},
            ],
        },
        "guidance_changes": {
            "summary": "Capex raised from R$89B to R$104B.",
            "items": [
                {
                    "metric": "Capex",
                    "previous": "R$89B",
                    "current": "R$104B",
                    "direction": "increase",
                    "significance": "high",
                    "excerpt": "Our 2025 capital program is R$104B.",
                }
            ],
        },
        "top_analyst_questions": [
            {
                "rank": 1,
                "analyst_name": "Gabriel Barra",
                "institution": "Itaú BBA",
                "question_summary": "Dividend sustainability question.",
                "question_excerpt": "Can the 68% payout be repeated?",
                "response_summary": "CFO deflected.",
                "response_quality": "evasive",
                "response_excerpt": "We follow our 45% minimum policy.",
            },
            {
                "rank": 2,
                "analyst_name": "Regis Cardoso",
                "institution": "XP Investimentos",
                "question_summary": "RNEST cost overrun question.",
                "question_excerpt": "Is RNEST within contingency?",
                "response_summary": "CEO self-interrupted.",
                "response_quality": "deflected",
                "response_excerpt": "The RNEST situation is — very complex.",
            },
            {
                "rank": 3,
                "analyst_name": "Bruno Amorim",
                "institution": "Goldman Sachs",
                "question_summary": "FCF breakeven Brent question.",
                "question_excerpt": "What is the FCF breakeven Brent?",
                "response_summary": "CFO declined the specific number.",
                "response_quality": "incomplete",
                "response_excerpt": "Dividends are sustainable at USD 65 Brent.",
            },
        ],
        "red_flags": [
            {
                "flag_type": "evasion",
                "speaker": "CEO",
                "excerpt": "Let's move forward.",
                "analysis": "Closes topic without answering.",
                "severity": "high",
            }
        ],
        "surprise_score": {
            "score": 7,
            "rationale": "Rota 3 program and capex revision surprised.",
            "items": [
                {
                    "element": "Rota 3 R$8.7B",
                    "why_surprising": "Not in strategic plan.",
                    "expected_consensus": "Flat capex.",
                    "actual_statement": "R$8.7B announced.",
                    "excerpt": "We announce the Rota 3 program.",
                    "market_impact_assessment": "mixed",
                }
            ],
        },
    }
    return json.dumps(data)


def _minimal_critique_json() -> str:
    data = {
        "overall_quality": "high",
        "reliability_score": 8,
        "items": [
            {
                "section": "management_tone",
                "issue_found": False,
                "critique": "Well-supported.",
                "confidence_after_review": "high",
            }
        ],
        "caveats": ["Score based on model knowledge, not Bloomberg estimates."],
    }
    return json.dumps(data)


# ---------------------------------------------------------------------------
# _get_client
# ---------------------------------------------------------------------------


class TestGetClient:
    def test_raises_when_key_missing(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(EnvironmentError, match="ANTHROPIC_API_KEY"):
            _get_client()

    def test_returns_client_when_key_set(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
        client = _get_client()
        assert isinstance(client, anthropic.Anthropic)


# ---------------------------------------------------------------------------
# _parse_json_from_response
# ---------------------------------------------------------------------------


class TestParseJson:
    def test_parses_plain_json(self):
        raw = '{"key": "value"}'
        result = _parse_json_from_response(raw)
        assert result == {"key": "value"}

    def test_strips_markdown_fences(self):
        raw = "```json\n{\"key\": \"value\"}\n```"
        result = _parse_json_from_response(raw)
        assert result == {"key": "value"}

    def test_strips_bare_fences(self):
        raw = "```\n{\"key\": \"value\"}\n```"
        result = _parse_json_from_response(raw)
        assert result == {"key": "value"}

    def test_raises_on_invalid_json(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_json_from_response("not json at all")


# ---------------------------------------------------------------------------
# _call_llm
# ---------------------------------------------------------------------------


class TestCallLlm:
    def test_returns_text_on_success(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        client = MagicMock()
        client.messages.create.return_value = _make_mock_response("Hello from Claude")
        result = _call_llm(client, system="sys", user="user msg")
        assert result == "Hello from Claude"

    def test_retries_on_rate_limit(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        client = MagicMock()
        client.messages.create.side_effect = [
            anthropic.RateLimitError(
                message="rate limited", response=MagicMock(headers={}), body={}
            ),
            _make_mock_response("Success after retry"),
        ]
        with patch("src.analyzer.time.sleep"):
            result = _call_llm(client, system="sys", user="user msg")
        assert result == "Success after retry"
        assert client.messages.create.call_count == 2

    def test_raises_after_three_rate_limit_errors(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        client = MagicMock()
        client.messages.create.side_effect = anthropic.RateLimitError(
            message="rate limited", response=MagicMock(headers={}), body={}
        )
        with patch("src.analyzer.time.sleep"):
            with pytest.raises(anthropic.RateLimitError):
                _call_llm(client, system="sys", user="user msg")
        assert client.messages.create.call_count == 3

    def test_retries_on_internal_server_error(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        client = MagicMock()
        client.messages.create.side_effect = [
            anthropic.InternalServerError(
                message="server error", response=MagicMock(headers={}), body={}
            ),
            _make_mock_response("Success after server error retry"),
        ]
        with patch("src.analyzer.time.sleep"):
            result = _call_llm(client, system="sys", user="user msg")
        assert result == "Success after server error retry"

    def test_uses_cache_control_on_system_prompt(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        client = MagicMock()
        client.messages.create.return_value = _make_mock_response("ok")
        _call_llm(client, system="My system prompt", user="user msg")
        call_kwargs = client.messages.create.call_args
        system_arg = call_kwargs.kwargs.get("system") or call_kwargs.args[0] if call_kwargs.args else None
        # system is passed as keyword argument
        system_arg = client.messages.create.call_args.kwargs["system"]
        assert isinstance(system_arg, list)
        assert system_arg[0]["cache_control"] == {"type": "ephemeral"}


# ---------------------------------------------------------------------------
# analyze_transcript
# ---------------------------------------------------------------------------


class TestAnalyzeTranscript:
    @patch("src.analyzer._get_client")
    def test_returns_earnings_call_analysis(self, mock_get_client, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        client = MagicMock()
        mock_get_client.return_value = client
        client.messages.create.side_effect = [
            _make_mock_response(_minimal_analysis_json()),   # pass 1
            _make_mock_response(_minimal_critique_json()),   # pass 2
        ]
        result = analyze_transcript("Transcript text here.", enable_self_critique=True)
        assert isinstance(result, EarningsCallAnalysis)
        assert result.ticker == "PETR4"

    @patch("src.analyzer._get_client")
    def test_self_critique_disabled_makes_one_call(self, mock_get_client, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        client = MagicMock()
        mock_get_client.return_value = client
        client.messages.create.return_value = _make_mock_response(_minimal_analysis_json())
        analyze_transcript("Transcript text.", enable_self_critique=False)
        assert client.messages.create.call_count == 1

    @patch("src.analyzer._get_client")
    def test_self_critique_enabled_makes_two_calls(self, mock_get_client, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        client = MagicMock()
        mock_get_client.return_value = client
        client.messages.create.side_effect = [
            _make_mock_response(_minimal_analysis_json()),
            _make_mock_response(_minimal_critique_json()),
        ]
        analyze_transcript("Transcript text.", enable_self_critique=True)
        assert client.messages.create.call_count == 2

    @patch("src.analyzer._get_client")
    def test_self_critique_populated_on_result(self, mock_get_client, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        client = MagicMock()
        mock_get_client.return_value = client
        client.messages.create.side_effect = [
            _make_mock_response(_minimal_analysis_json()),
            _make_mock_response(_minimal_critique_json()),
        ]
        result = analyze_transcript("Transcript.", enable_self_critique=True)
        assert result.self_critique is not None
        assert result.self_critique.reliability_score == 8

    @patch("src.analyzer._get_client")
    def test_self_critique_none_when_disabled(self, mock_get_client, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        client = MagicMock()
        mock_get_client.return_value = client
        client.messages.create.return_value = _make_mock_response(_minimal_analysis_json())
        result = analyze_transcript("Transcript.", enable_self_critique=False)
        assert result.self_critique is None

    @patch("src.analyzer._get_client")
    def test_raises_value_error_on_invalid_json(self, mock_get_client, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        client = MagicMock()
        mock_get_client.return_value = client
        client.messages.create.return_value = _make_mock_response("This is not JSON at all.")
        with pytest.raises(ValueError, match="invalid JSON"):
            analyze_transcript("Transcript.", enable_self_critique=False)

    @patch("src.analyzer._get_client")
    def test_critique_failure_is_non_fatal(self, mock_get_client, monkeypatch):
        """If the self-critique pass returns invalid JSON, analysis should still succeed."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        client = MagicMock()
        mock_get_client.return_value = client
        client.messages.create.side_effect = [
            _make_mock_response(_minimal_analysis_json()),
            _make_mock_response("invalid critique json"),
        ]
        result = analyze_transcript("Transcript.", enable_self_critique=True)
        assert isinstance(result, EarningsCallAnalysis)
        assert result.self_critique is None  # silently skipped
