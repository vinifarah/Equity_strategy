from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


class TranscriptExcerpt(BaseModel):
    quote: str = Field(description="Verbatim quote from transcript — never paraphrased")
    speaker: str = Field(description="Name/role of the speaker")
    interpretation: str = Field(description="Why this excerpt supports the classification")


class ManagementTone(BaseModel):
    overall_sentiment: Literal["bullish", "cautious", "neutral", "defensive", "bearish"]
    confidence_score: int = Field(ge=1, le=10, description="Analyst confidence in tone assessment")
    justification: str = Field(description="One-paragraph explanation of tone classification")
    supporting_excerpts: list[TranscriptExcerpt] = Field(
        min_length=2, max_length=5, description="2-5 verbatim excerpts supporting the tone"
    )


class GuidanceItem(BaseModel):
    metric: str = Field(description="Financial metric being guided (e.g. EBITDA, Capex, Production)")
    previous: Optional[str] = Field(default=None, description="Previous quarter guidance or NOT_FOUND")
    current: str = Field(description="New/current guidance as stated in the call")
    direction: Literal["increase", "decrease", "maintained", "new_guidance", "removed"]
    significance: Literal["high", "medium", "low"]
    excerpt: str = Field(description="Verbatim excerpt containing this guidance")


class GuidanceChanges(BaseModel):
    summary: str = Field(description="2-3 sentence synthesis of guidance evolution vs prior quarter")
    items: list[GuidanceItem]


class AnalystQuestion(BaseModel):
    rank: int = Field(ge=1, le=3)
    analyst_name: str
    institution: str
    question_summary: str = Field(description="1-2 sentence summary of the question's thrust")
    question_excerpt: str = Field(description="Verbatim excerpt of the key part of the question")
    response_summary: str = Field(description="How management responded — what was said and what was avoided")
    response_quality: Literal["excellent", "good", "evasive", "incomplete", "deflected"]
    response_excerpt: str = Field(description="Verbatim excerpt of the key part of management's response")


class RedFlag(BaseModel):
    flag_type: Literal["hesitation", "topic_change", "evasion", "defensive_language", "vague_answer", "deflected"]
    speaker: str
    excerpt: str = Field(description="Verbatim quote showing the red flag — must be literal")
    analysis: str = Field(
        description="Why this is a red flag: what would a confident management say instead?"
    )
    severity: Literal["high", "medium", "low"]


class SurpriseItem(BaseModel):
    element: str = Field(description="What was surprising (e.g. 'Dividend cut', 'New capex program')")
    why_surprising: str = Field(description="Why market consensus did NOT expect this")
    expected_consensus: str = Field(description="What the market expected before the call")
    actual_statement: str = Field(description="What management actually said/announced")
    excerpt: str = Field(description="Verbatim quote from transcript")
    market_impact_assessment: Literal["positive", "negative", "neutral", "mixed"]


class SurpriseScore(BaseModel):
    score: int = Field(ge=1, le=10, description="1=no surprises, 10=major unexpected announcements")
    rationale: str = Field(description="Why this score was assigned")
    items: list[SurpriseItem]


class SelfCritiqueItem(BaseModel):
    section: str = Field(description="Which section of the analysis is being critiqued")
    issue_found: bool
    critique: str = Field(description="What the model found problematic or affirmed as solid")
    confidence_after_review: Literal["high", "medium", "low"]


class SelfCritique(BaseModel):
    overall_quality: Literal["high", "medium", "low"]
    reliability_score: int = Field(ge=1, le=10, description="How much to trust this analysis")
    items: list[SelfCritiqueItem]
    caveats: list[str] = Field(description="Important caveats an analyst should keep in mind")


# ---------------------------------------------------------------------------
# Extension: Market Reaction
# ---------------------------------------------------------------------------

class MarketReaction(BaseModel):
    """Price reaction around the earnings call date, fetched from Yahoo Finance."""
    call_date: str
    data_available: bool = False
    price_d_minus_1: Optional[float] = None
    price_d_close: Optional[float] = None
    price_d_plus_1: Optional[float] = None
    price_d_plus_5: Optional[float] = None
    return_d1_pct: Optional[float] = None
    return_d5_pct: Optional[float] = None
    ibov_return_d1_pct: Optional[float] = None
    ibov_return_d5_pct: Optional[float] = None
    alpha_d1_pct: Optional[float] = None
    alpha_d5_pct: Optional[float] = None
    interpretation: str = ""


# ---------------------------------------------------------------------------
# Extension: Temporal Comparison (Q/Q)
# ---------------------------------------------------------------------------

class ToneEvolution(BaseModel):
    previous_sentiment: str
    current_sentiment: str
    direction: Literal["improved", "deteriorated", "stable"]
    key_changes: list[str] = Field(min_length=1, max_length=4)


class GuidanceEvolution(BaseModel):
    reiterated: list[str] = Field(default_factory=list)
    upgraded: list[str] = Field(default_factory=list)
    downgraded: list[str] = Field(default_factory=list)
    new_items: list[str] = Field(default_factory=list)
    removed_items: list[str] = Field(default_factory=list)


class RedFlagEvolution(BaseModel):
    persistent: list[str] = Field(default_factory=list, description="Red flag themes in both quarters")
    new_flags: list[str] = Field(default_factory=list, description="New red flags not seen previously")
    resolved: list[str] = Field(default_factory=list, description="Previous red flags that disappeared")


class TemporalComparison(BaseModel):
    previous_quarter: str
    current_quarter: str
    tone_evolution: ToneEvolution
    guidance_evolution: GuidanceEvolution
    red_flag_evolution: RedFlagEvolution
    surprise_score_delta: int = Field(ge=-9, le=9, description="Current score minus previous score")
    analyst_summary: str = Field(description="2-3 sentence synthesis of narrative shift between quarters")


# ---------------------------------------------------------------------------
# Root model
# ---------------------------------------------------------------------------

class EarningsCallAnalysis(BaseModel):
    company: str
    ticker: str
    quarter: str
    call_date: str
    management_tone: ManagementTone
    guidance_changes: GuidanceChanges
    top_analyst_questions: list[AnalystQuestion] = Field(min_length=3, max_length=3)
    red_flags: list[RedFlag]
    surprise_score: SurpriseScore
    self_critique: Optional[SelfCritique] = None
    market_reaction: Optional[MarketReaction] = None
    temporal_comparison: Optional[TemporalComparison] = None
