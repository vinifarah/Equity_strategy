"""Shared fixtures for all test modules."""
from __future__ import annotations

import pytest

from src.models import (
    AnalystQuestion,
    EarningsCallAnalysis,
    GuidanceChanges,
    GuidanceItem,
    ManagementTone,
    RedFlag,
    SelfCritique,
    SelfCritiqueItem,
    SurpriseItem,
    SurpriseScore,
    TranscriptExcerpt,
)


@pytest.fixture()
def sample_analysis() -> EarningsCallAnalysis:
    """Minimal but complete EarningsCallAnalysis for use in reporter and model tests."""
    return EarningsCallAnalysis(
        company="Petróleo Brasileiro S.A. - Petrobras",
        ticker="PETR4",
        quarter="4T24",
        call_date="2025-02-19",
        management_tone=ManagementTone(
            overall_sentiment="cautious",
            confidence_score=7,
            justification=(
                "Management projects operational confidence on production records "
                "but adopts defensive language when pressed on dividends and RNEST. "
                "The overall tone is cautious."
            ),
            supporting_excerpts=[
                TranscriptExcerpt(
                    quote="We delivered our strongest pre-salt production year on record.",
                    speaker="Magda Chambriard (CEO)",
                    interpretation="Operationally confident framing on production.",
                ),
                TranscriptExcerpt(
                    quote="What we can confirm is that the overall 2025 capex guidance fully "
                    "contemplates our current expectation for RNEST expenditures.",
                    speaker="Magda Chambriard (CEO)",
                    interpretation="Evasive non-answer on cost overrun question.",
                ),
            ],
        ),
        guidance_changes=GuidanceChanges(
            summary=(
                "Capex revised up 17% from R$89B to R$104B. Production guidance maintained "
                "at 2.8-3.0 Mboe/d. New Rota 3 pipeline program of R$8.7B announced."
            ),
            items=[
                GuidanceItem(
                    metric="2025 Capex",
                    previous="R$ 89 bilhões",
                    current="R$ 104 bilhões",
                    direction="increase",
                    significance="high",
                    excerpt="Our updated 2025 capital program stands at R$104 billion.",
                ),
                GuidanceItem(
                    metric="Lifting Cost",
                    previous="USD 6.5/bbl",
                    current="USD 6.5 per barrel",
                    direction="maintained",
                    significance="low",
                    excerpt="We maintain our lifting cost guidance below USD 7 per barrel.",
                ),
            ],
        ),
        top_analyst_questions=[
            AnalystQuestion(
                rank=1,
                analyst_name="Gabriel Barra",
                institution="Itaú BBA",
                question_summary="Pressed on whether extraordinary dividend payout can be repeated in 2025.",
                question_excerpt="Can you confirm the 68% payout can be maintained going into 2025?",
                response_summary="CFO deflected entirely, refusing to guide beyond 45% floor.",
                response_quality="evasive",
                response_excerpt="We are committed to our minimum dividend policy of 45% of operating cash flow.",
            ),
            AnalystQuestion(
                rank=2,
                analyst_name="Regis Cardoso",
                institution="XP Investimentos",
                question_summary="Sought specifics on RNEST contractor issues and cost overrun.",
                question_excerpt="Is the RNEST cost within original contingency or is this a new overrun?",
                response_summary="CEO self-interrupted and CFO refused to confirm cost containment.",
                response_quality="deflected",
                response_excerpt="The RNEST situation is — look, it's a very complex project.",
            ),
            AnalystQuestion(
                rank=3,
                analyst_name="Bruno Amorim",
                institution="Goldman Sachs",
                question_summary="Tested durability of cost structure and FCF breakeven Brent.",
                question_excerpt="What is the FCF breakeven Brent price for dividend sustainability?",
                response_summary="CFO gave directional answers but declined the specific breakeven.",
                response_quality="incomplete",
                response_excerpt="Dividends remain sustainable at USD 65 Brent through our planning horizon.",
            ),
        ],
        red_flags=[
            RedFlag(
                flag_type="evasion",
                speaker="Magda Chambriard (CEO)",
                excerpt="What we can confirm is that the overall 2025 capex guidance fully "
                "contemplates our current expectation for RNEST. Let's move forward.",
                analysis="Pivots to total capex (non-answer) and unilaterally closes topic.",
                severity="high",
            ),
            RedFlag(
                flag_type="hesitation",
                speaker="Magda Chambriard (CEO)",
                excerpt="The RNEST situation is — look, it's a very complex project.",
                analysis="Self-interruption followed by attention-redirector signals discomfort.",
                severity="high",
            ),
        ],
        surprise_score=SurpriseScore(
            score=7,
            rationale=(
                "Two elements clearly outside consensus: Rota 3 program and capex revision magnitude. "
                "RNEST situation partially anticipated but worse than expected."
            ),
            items=[
                SurpriseItem(
                    element="Rota 3 Gas Pipeline — R$8.7B new capex",
                    why_surprising="Not included in the 2024-2028 Strategic Plan.",
                    expected_consensus="Capex in line with R$89B guided in November 2024.",
                    actual_statement="R$8.7 billion Rota 3 program approved over 2025-2027.",
                    excerpt="We are pleased to announce the Rota 3 gas pipeline expansion program.",
                    market_impact_assessment="mixed",
                ),
            ],
        ),
        self_critique=SelfCritique(
            overall_quality="high",
            reliability_score=8,
            items=[
                SelfCritiqueItem(
                    section="management_tone",
                    issue_found=False,
                    critique="Tone classification well-supported by verbatim excerpts.",
                    confidence_after_review="high",
                ),
            ],
            caveats=[
                "Surprise score based on model knowledge, not actual Bloomberg sell-side estimates.",
            ],
        ),
    )


@pytest.fixture()
def sample_analysis_no_critique(sample_analysis: EarningsCallAnalysis) -> EarningsCallAnalysis:
    """Same analysis but with self_critique removed."""
    sample_analysis.self_critique = None
    return sample_analysis


MINIMAL_TRANSCRIPT = """\
Petrobras Q4 2024 Earnings Call

CEO: Good morning. Our Q4 results demonstrate strong operational execution.
We delivered production of 2.9 million barrels of oil equivalent per day.

Analyst (Itaú BBA): Can you comment on the dividend policy for 2025?

CFO: We remain committed to our minimum payout of 45% of operating cash flow.
"""
