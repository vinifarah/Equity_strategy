from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


class MacroVariable(BaseModel):
    variable: str = Field(description="Name of macro variable e.g. 'Taxa Selic', 'Câmbio BRL/USD'")
    direction: Literal["rising", "falling", "stable", "uncertain"]
    magnitude: Literal["large", "moderate", "small"]
    description: str = Field(description="Brief description of this variable in the scenario")


class SectorImpact(BaseModel):
    sector: str = Field(description="Sector name in Portuguese e.g. 'Financeiro', 'Energia'")
    ibovespa_weight_pct: str = Field(description="Approximate Ibovespa weight e.g. '22%'")
    impact_score: int = Field(ge=1, le=10, description="Impact magnitude: 1=minor, 10=severe/major")
    direction: Literal["positive", "negative"]
    rationale: str = Field(
        description="1-2 sentences explaining the specific transmission mechanism from scenario to sector"
    )
    transmission_channels: list[str] = Field(
        description="List of specific economic channels e.g. ['interest rate sensitivity', 'FX revenue']"
    )
    confidence: Literal["high", "medium", "low"]


class TickerRecommendation(BaseModel):
    ticker: str = Field(description="B3 ticker e.g. PETR4, VALE3")
    company: str
    sector: str
    direction: Literal["positive", "negative"]
    rationale: str = Field(
        description="Why this specific company is particularly exposed vs sector peers"
    )
    key_company_characteristics: str = Field(
        description="The financial/operational characteristics that drive the exposure"
    )
    conviction_score: int = Field(ge=1, le=10)
    confidence: Literal["high", "medium", "low"]


class ThesisRisk(BaseModel):
    risk: str = Field(description="Name of the risk")
    description: str = Field(description="What would need to happen for this risk to materialize")
    probability: Literal["high", "medium", "low"]
    impact: Literal["severe", "moderate", "mild"]
    affected_tickers: list[str] = Field(description="Which recommendations are most impacted")
    mitigation: str = Field(description="How to hedge or monitor for this risk")


class SelfCritiqueItem(BaseModel):
    section: str
    issue_found: bool
    critique: str
    confidence_after_review: Literal["high", "medium", "low"]


class SelfCritique(BaseModel):
    overall_consistency: Literal["high", "medium", "low"]
    logical_conflicts: list[str] = Field(
        description="Any internal inconsistencies found e.g. recommending a sector as positive while picking a negative ticker from it"
    )
    blind_spots: list[str] = Field(description="Important considerations the analysis may have missed")
    reliability_score: int = Field(ge=1, le=10)
    items: list[SelfCritiqueItem]


class MacroScenarioAnalysis(BaseModel):
    scenario_input: str = Field(description="Original scenario as provided by the user")
    scenario_summary: str = Field(description="Structured 2-3 sentence restatement of the key macro variables")
    key_macro_variables: list[MacroVariable]
    benefited_sectors: list[SectorImpact] = Field(min_length=5, max_length=5)
    harmed_sectors: list[SectorImpact] = Field(min_length=5, max_length=5)
    positive_tickers: list[TickerRecommendation] = Field(min_length=3, max_length=3)
    negative_tickers: list[TickerRecommendation] = Field(min_length=3, max_length=3)
    thesis_risks: list[ThesisRisk] = Field(min_length=3, max_length=3)
    overall_market_bias: Literal["strongly_bullish", "moderately_bullish", "neutral", "moderately_bearish", "strongly_bearish"]
    self_critique: Optional[SelfCritique] = None
