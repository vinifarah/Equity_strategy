"""Unit tests for Pydantic model validation in src/models.py."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.models import (
    AnalystQuestion,
    EarningsCallAnalysis,
    GuidanceChanges,
    GuidanceItem,
    ManagementTone,
    RedFlag,
    SurpriseScore,
    TranscriptExcerpt,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_excerpt(**kwargs):
    defaults = dict(
        quote="Verbatim quote here.",
        speaker="CEO",
        interpretation="Supports the tone.",
    )
    return TranscriptExcerpt(**{**defaults, **kwargs})


def _make_tone(**kwargs):
    defaults = dict(
        overall_sentiment="cautious",
        confidence_score=7,
        justification="Management is cautious.",
        supporting_excerpts=[_make_excerpt(), _make_excerpt()],
    )
    return ManagementTone(**{**defaults, **kwargs})


def _make_guidance_item(**kwargs):
    defaults = dict(
        metric="Capex",
        previous="R$89B",
        current="R$104B",
        direction="increase",
        significance="high",
        excerpt="Our capex is R$104B.",
    )
    return GuidanceItem(**{**defaults, **kwargs})


def _make_analyst_question(rank: int = 1, **kwargs):
    defaults = dict(
        rank=rank,
        analyst_name="John Doe",
        institution="Goldman",
        question_summary="Asked about dividends.",
        question_excerpt="What is the dividend policy?",
        response_summary="CFO deflected.",
        response_quality="evasive",
        response_excerpt="We follow our minimum policy.",
    )
    return AnalystQuestion(**{**defaults, **kwargs})


def _make_surprise_score(**kwargs):
    from src.models import SurpriseItem
    defaults = dict(
        score=5,
        rationale="Moderate surprises.",
        items=[
            SurpriseItem(
                element="New capex",
                why_surprising="Not expected.",
                expected_consensus="Flat capex.",
                actual_statement="R$8.7B new program.",
                excerpt="We announce the Rota 3 program.",
                market_impact_assessment="mixed",
            )
        ],
    )
    return SurpriseScore(**{**defaults, **kwargs})


def _make_full_analysis(**overrides) -> dict:
    base = dict(
        company="Petrobras",
        ticker="PETR4",
        quarter="4T24",
        call_date="2025-02-19",
        management_tone=_make_tone(),
        guidance_changes=GuidanceChanges(
            summary="Capex raised.", items=[_make_guidance_item()]
        ),
        top_analyst_questions=[
            _make_analyst_question(1),
            _make_analyst_question(2),
            _make_analyst_question(3),
        ],
        red_flags=[],
        surprise_score=_make_surprise_score(),
    )
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# ManagementTone
# ---------------------------------------------------------------------------


class TestManagementTone:
    def test_valid_sentiments(self):
        for sentiment in ("bullish", "cautious", "neutral", "defensive", "bearish"):
            t = _make_tone(overall_sentiment=sentiment)
            assert t.overall_sentiment == sentiment

    def test_invalid_sentiment_raises(self):
        with pytest.raises(ValidationError):
            _make_tone(overall_sentiment="optimistic")

    def test_confidence_score_bounds(self):
        _make_tone(confidence_score=1)
        _make_tone(confidence_score=10)

    def test_confidence_score_below_min_raises(self):
        with pytest.raises(ValidationError):
            _make_tone(confidence_score=0)

    def test_confidence_score_above_max_raises(self):
        with pytest.raises(ValidationError):
            _make_tone(confidence_score=11)

    def test_requires_at_least_two_excerpts(self):
        with pytest.raises(ValidationError):
            _make_tone(supporting_excerpts=[_make_excerpt()])

    def test_allows_up_to_five_excerpts(self):
        excerpts = [_make_excerpt() for _ in range(5)]
        t = _make_tone(supporting_excerpts=excerpts)
        assert len(t.supporting_excerpts) == 5

    def test_more_than_five_excerpts_raises(self):
        excerpts = [_make_excerpt() for _ in range(6)]
        with pytest.raises(ValidationError):
            _make_tone(supporting_excerpts=excerpts)


# ---------------------------------------------------------------------------
# GuidanceItem
# ---------------------------------------------------------------------------


class TestGuidanceItem:
    def test_valid_directions(self):
        for direction in ("increase", "decrease", "maintained", "new_guidance", "removed"):
            item = _make_guidance_item(direction=direction)
            assert item.direction == direction

    def test_invalid_direction_raises(self):
        with pytest.raises(ValidationError):
            _make_guidance_item(direction="sideways")

    def test_valid_significance_levels(self):
        for sig in ("high", "medium", "low"):
            item = _make_guidance_item(significance=sig)
            assert item.significance == sig

    def test_previous_is_optional(self):
        item = _make_guidance_item(previous=None)
        assert item.previous is None


# ---------------------------------------------------------------------------
# AnalystQuestion
# ---------------------------------------------------------------------------


class TestAnalystQuestion:
    def test_valid_response_qualities(self):
        for quality in ("excellent", "good", "evasive", "incomplete", "deflected"):
            q = _make_analyst_question(response_quality=quality)
            assert q.response_quality == quality

    def test_invalid_quality_raises(self):
        with pytest.raises(ValidationError):
            _make_analyst_question(response_quality="bad")

    def test_rank_bounds(self):
        _make_analyst_question(rank=1)
        _make_analyst_question(rank=3)

    def test_rank_zero_raises(self):
        with pytest.raises(ValidationError):
            _make_analyst_question(rank=0)

    def test_rank_above_three_raises(self):
        with pytest.raises(ValidationError):
            _make_analyst_question(rank=4)


# ---------------------------------------------------------------------------
# RedFlag
# ---------------------------------------------------------------------------


class TestRedFlag:
    def test_valid_flag_types(self):
        for ft in ("hesitation", "topic_change", "evasion", "defensive_language", "vague_answer"):
            rf = RedFlag(
                flag_type=ft,
                speaker="CEO",
                excerpt="Some quote.",
                analysis="This is evasive.",
                severity="high",
            )
            assert rf.flag_type == ft

    def test_invalid_flag_type_raises(self):
        with pytest.raises(ValidationError):
            RedFlag(
                flag_type="lie",
                speaker="CEO",
                excerpt="Quote.",
                analysis="Reason.",
                severity="high",
            )

    def test_valid_severities(self):
        for sev in ("high", "medium", "low"):
            rf = RedFlag(
                flag_type="evasion",
                speaker="CEO",
                excerpt="Quote.",
                analysis="Reason.",
                severity=sev,
            )
            assert rf.severity == sev


# ---------------------------------------------------------------------------
# SurpriseScore
# ---------------------------------------------------------------------------


class TestSurpriseScore:
    def test_score_bounds(self):
        _make_surprise_score(score=1)
        _make_surprise_score(score=10)

    def test_score_below_min_raises(self):
        with pytest.raises(ValidationError):
            _make_surprise_score(score=0)

    def test_score_above_max_raises(self):
        with pytest.raises(ValidationError):
            _make_surprise_score(score=11)


# ---------------------------------------------------------------------------
# EarningsCallAnalysis (top-level)
# ---------------------------------------------------------------------------


class TestEarningsCallAnalysis:
    def test_valid_construction(self):
        a = EarningsCallAnalysis(**_make_full_analysis())
        assert a.ticker == "PETR4"
        assert a.self_critique is None

    def test_requires_exactly_three_questions(self):
        data = _make_full_analysis(
            top_analyst_questions=[_make_analyst_question(1), _make_analyst_question(2)]
        )
        with pytest.raises(ValidationError):
            EarningsCallAnalysis(**data)

    def test_more_than_three_questions_raises(self):
        # Use valid rank values (1-3) repeated — the point is to test list length, not rank
        data = _make_full_analysis(
            top_analyst_questions=[_make_analyst_question(i) for i in [1, 2, 3, 1]]
        )
        with pytest.raises(ValidationError):
            EarningsCallAnalysis(**data)

    def test_empty_red_flags_is_valid(self):
        a = EarningsCallAnalysis(**_make_full_analysis(red_flags=[]))
        assert a.red_flags == []

    def test_self_critique_defaults_to_none(self):
        a = EarningsCallAnalysis(**_make_full_analysis())
        assert a.self_critique is None

    def test_model_dump_roundtrip(self, sample_analysis):
        dumped = sample_analysis.model_dump()
        restored = EarningsCallAnalysis.model_validate(dumped)
        assert restored.ticker == sample_analysis.ticker
        assert restored.management_tone.overall_sentiment == sample_analysis.management_tone.overall_sentiment
