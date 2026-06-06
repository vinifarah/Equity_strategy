from __future__ import annotations

import json
import os
import time

import anthropic
from dotenv import load_dotenv

from .models import EarningsCallAnalysis, SelfCritique, TemporalComparison

load_dotenv()

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a senior sell-side equity research analyst at a top-tier investment bank \
with 20 years of experience covering Brazilian publicly traded companies. Your specialty is extracting \
investment-relevant signals from earnings call transcripts — tone, guidance shifts, red flags, and \
surprises that the consensus may have missed.

CRITICAL RULES you must always follow:
1. Every "excerpt", "quote", or "question_excerpt"/"response_excerpt" field MUST contain text that \
appears VERBATIM in the transcript. Never paraphrase, summarize, or invent quotes.
2. If evidence for a field is not present in the transcript, write "NOT_FOUND" — never fabricate.
3. Red flags require high standards: only flag genuine linguistic evasion signals, not normal \
corporate hedging language.
4. Surprise score must be calibrated against typical Brazilian sell-side consensus expectations \
for the company and sector.
5. Return ONLY valid JSON matching the schema. No prose before or after the JSON block.
"""

EXTRACTION_PROMPT_TEMPLATE = """Analyze the following earnings call transcript and extract structured \
intelligence. Think carefully before writing each field.

TRANSCRIPT:
---
{transcript}
---

Return a single JSON object with this exact structure. Do not add extra fields.

{{
  "company": "<full company name>",
  "ticker": "<B3 ticker e.g. PETR4>",
  "quarter": "<e.g. 4T24 or Q4 2024>",
  "call_date": "<YYYY-MM-DD or best approximation>",

  "management_tone": {{
    "overall_sentiment": "<bullish|cautious|neutral|defensive|bearish>",
    "confidence_score": <1-10>,
    "justification": "<one paragraph explaining the tone classification>",
    "supporting_excerpts": [
      {{
        "quote": "<VERBATIM quote>",
        "speaker": "<name or role>",
        "interpretation": "<why this supports the tone classification>"
      }}
    ]
  }},

  "guidance_changes": {{
    "summary": "<2-3 sentence synthesis of guidance evolution vs prior quarter>",
    "items": [
      {{
        "metric": "<e.g. Capex, EBITDA, Production volume>",
        "previous": "<previous guidance or NOT_FOUND>",
        "current": "<new guidance as stated>",
        "direction": "<increase|decrease|maintained|new_guidance|removed>",
        "significance": "<high|medium|low>",
        "excerpt": "<VERBATIM quote containing this guidance>"
      }}
    ]
  }},

  "top_analyst_questions": [
    {{
      "rank": 1,
      "analyst_name": "<name>",
      "institution": "<bank or fund name>",
      "question_summary": "<1-2 sentences on the core thrust of the question>",
      "question_excerpt": "<VERBATIM key part of the question>",
      "response_summary": "<how management responded; note what was answered vs avoided>",
      "response_quality": "<excellent|good|evasive|incomplete|deflected>",
      "response_excerpt": "<VERBATIM key part of management's response>"
    }},
    {{
      "rank": 2,
      "analyst_name": "<name>",
      "institution": "<bank or fund name>",
      "question_summary": "<1-2 sentences on the core thrust of the question>",
      "question_excerpt": "<VERBATIM key part of the question>",
      "response_summary": "<how management responded; note what was answered vs avoided>",
      "response_quality": "<excellent|good|evasive|incomplete|deflected>",
      "response_excerpt": "<VERBATIM key part of management's response>"
    }},
    {{
      "rank": 3,
      "analyst_name": "<name>",
      "institution": "<bank or fund name>",
      "question_summary": "<1-2 sentences on the core thrust of the question>",
      "question_excerpt": "<VERBATIM key part of the question>",
      "response_summary": "<how management responded; note what was answered vs avoided>",
      "response_quality": "<excellent|good|evasive|incomplete|deflected>",
      "response_excerpt": "<VERBATIM key part of management's response>"
    }}
  ],

  "red_flags": [
    {{
      "flag_type": "<hesitation|topic_change|evasion|defensive_language|vague_answer|deflected>",
      "speaker": "<name or role>",
      "excerpt": "<VERBATIM quote showing the red flag>",
      "analysis": "<what a confident management would have said instead, and why this is a signal>",
      "severity": "<high|medium|low>"
    }}
  ],

  "surprise_score": {{
    "score": <1-10>,
    "rationale": "<why this score; what was the call's overall surprise factor>",
    "items": [
      {{
        "element": "<what was surprising>",
        "why_surprising": "<why market did not expect this>",
        "expected_consensus": "<what consensus expected before the call>",
        "actual_statement": "<what management announced>",
        "excerpt": "<VERBATIM quote>",
        "market_impact_assessment": "<positive|negative|neutral|mixed>"
      }}
    ]
  }}
}}

Remember: ALL excerpt/quote fields must be verbatim from the transcript above. \
If you cannot find a verbatim match, write NOT_FOUND for that field.
"""

TEMPORAL_COMPARISON_PROMPT_TEMPLATE = """You are a senior equity analyst. You have structured analyses \
of two consecutive earnings calls for the same company.

PREVIOUS QUARTER ANALYSIS:
---
{previous_json}
---

CURRENT QUARTER ANALYSIS:
---
{current_json}
---

Compare these two analyses and produce a structured Q-o-Q evolution report. Focus on genuine narrative \
shifts, not noise. Be specific: name the metrics, name the flag types.

Return a JSON object with this exact structure:
{{
  "previous_quarter": "<quarter string from previous analysis, e.g. 3T24>",
  "current_quarter": "<quarter string from current analysis, e.g. 4T24>",
  "tone_evolution": {{
    "previous_sentiment": "<sentiment from previous>",
    "current_sentiment": "<sentiment from current>",
    "direction": "<improved|deteriorated|stable>",
    "key_changes": ["<specific change in management communication — 2 to 4 items>"]
  }},
  "guidance_evolution": {{
    "reiterated": ["<metric: value — guidance confirmed from prior quarter>"],
    "upgraded": ["<metric: old → new — guidance that improved>"],
    "downgraded": ["<metric: old → new — guidance that worsened>"],
    "new_items": ["<metric: value — new guidance item not present before>"],
    "removed_items": ["<metric — guidance item that disappeared without explanation>"]
  }},
  "red_flag_evolution": {{
    "persistent": ["<red flag theme present in both quarters — why it is concerning>"],
    "new_flags": ["<new red flag not seen in the previous quarter>"],
    "resolved": ["<red flag from previous quarter that did not reappear — positive signal>"]
  }},
  "surprise_score_delta": <integer: current_score minus previous_score, range -9 to 9>,
  "analyst_summary": "<2-3 sentences: what is the most important narrative shift? \
Is the trajectory improving, deteriorating, or stable? What should investors watch?>"
}}
"""

SELF_CRITIQUE_PROMPT_TEMPLATE = """You previously analyzed an earnings call transcript and produced \
the following structured analysis:

PRIOR ANALYSIS:
---
{analysis_json}
---

ORIGINAL TRANSCRIPT (for verification):
---
{transcript}
---

Now act as a critical peer reviewer. Evaluate the quality and reliability of the analysis above by \
checking each section against the transcript.

Return a JSON object with this structure:
{{
  "overall_quality": "<high|medium|low>",
  "reliability_score": <1-10>,
  "items": [
    {{
      "section": "<management_tone|guidance_changes|analyst_questions|red_flags|surprise_score>",
      "issue_found": <true|false>,
      "critique": "<what is solid or problematic in this section; verify excerpts are real>",
      "confidence_after_review": "<high|medium|low>"
    }}
  ],
  "caveats": [
    "<important caveat an analyst should keep in mind when using this analysis>"
  ]
}}

Be honest. Flag any quote that does not appear verbatim in the transcript. \
Flag any red flag that may be overblown. Flag any surprise score that seems miscalibrated.
"""

# ---------------------------------------------------------------------------
# Client helpers — Anthropic Claude
# ---------------------------------------------------------------------------


def _get_client() -> anthropic.Anthropic:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY not set. Create a .env file from .env.example."
        )
    return anthropic.Anthropic(api_key=key)


def _model() -> str:
    return os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")


def _call_llm(client: anthropic.Anthropic, system: str, user: str) -> str:
    """Single LLM call via Anthropic Claude with retry on transient errors.

    Caches the system prompt to reduce costs on repeated calls within a session.
    """
    for attempt in range(3):
        try:
            response = client.messages.create(
                model=_model(),
                max_tokens=16384,
                system=[
                    {
                        "type": "text",
                        "text": system,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user}],
            )
            return response.content[0].text
        except anthropic.RateLimitError:
            if attempt < 2:
                time.sleep(30 * (attempt + 1))
            else:
                raise
        except anthropic.InternalServerError:
            if attempt < 2:
                time.sleep(10 * (attempt + 1))
            else:
                raise


def _parse_json_from_response(raw: str) -> dict:
    """Extract and parse JSON from LLM response, stripping markdown fences if present."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    return json.loads(text)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze_transcript(transcript: str, enable_self_critique: bool = True) -> EarningsCallAnalysis:
    """Run the full earnings call analysis pipeline.

    Args:
        transcript: Cleaned transcript text.
        enable_self_critique: Whether to run the self-critique review pass.

    Returns:
        EarningsCallAnalysis with all fields populated.
    """
    client = _get_client()

    # --- Pass 1: Main extraction ---
    user_prompt = EXTRACTION_PROMPT_TEMPLATE.format(transcript=transcript)
    raw = _call_llm(client, SYSTEM_PROMPT, user_prompt)

    try:
        data = _parse_json_from_response(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON:\n{raw[:500]}\n\nError: {e}") from e

    analysis = EarningsCallAnalysis.model_validate(data)

    # --- Pass 2: Self-critique (optional) ---
    if enable_self_critique:
        critique_prompt = SELF_CRITIQUE_PROMPT_TEMPLATE.format(
            analysis_json=json.dumps(data, ensure_ascii=False, indent=2),
            transcript=transcript,
        )
        raw_critique = _call_llm(client, SYSTEM_PROMPT, critique_prompt)
        try:
            critique_data = _parse_json_from_response(raw_critique)
            analysis.self_critique = SelfCritique.model_validate(critique_data)
        except (json.JSONDecodeError, Exception):
            pass

    return analysis


def compare_with_previous(
    current: EarningsCallAnalysis,
    previous_json: dict,
) -> TemporalComparison:
    """Generate a Q-o-Q temporal comparison between two quarters via LLM.

    Args:
        current: The freshly generated analysis for the current quarter.
        previous_json: Raw dict of a previously saved EarningsCallAnalysis JSON.

    Returns:
        TemporalComparison with structured delta between the two quarters.
    """
    client = _get_client()

    def _core(d: dict) -> dict:
        return {
            k: v for k, v in d.items()
            if k not in ("self_critique", "market_reaction", "temporal_comparison")
            and v is not None
        }

    prompt = TEMPORAL_COMPARISON_PROMPT_TEMPLATE.format(
        previous_json=json.dumps(_core(previous_json), ensure_ascii=False, indent=2),
        current_json=json.dumps(_core(json.loads(current.model_dump_json())), ensure_ascii=False, indent=2),
    )

    raw = _call_llm(client, SYSTEM_PROMPT, prompt)
    try:
        data = _parse_json_from_response(raw)
        return TemporalComparison.model_validate(data)
    except Exception as e:
        raise ValueError(f"Temporal comparison parse failed: {e}") from e
