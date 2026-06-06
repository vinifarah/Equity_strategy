from __future__ import annotations

import json
import os
import time

import anthropic
from dotenv import load_dotenv

from .models import MacroScenarioAnalysis, SelfCritique

load_dotenv()

# ---------------------------------------------------------------------------
# Brazilian market context injected into all prompts
# ---------------------------------------------------------------------------

BRAZIL_MARKET_CONTEXT = """
BRAZILIAN EQUITY MARKET CONTEXT (Ibovespa composition, June 2025):
- Financeiro/Bancos (~22%): Itaú Unibanco (ITUB4), Bradesco (BBDC4), Banco do Brasil (BBAS3), XP (XPBR31)
  → Sensitive to Selic rate, credit spreads, NIM, loan growth, default rates
- Energia/Petróleo (~15%): Petrobras (PETR4/PETR3), Ultrapar (UGPA3)
  → Sensitive to Brent, BRL/USD exchange rate, refinery margins, government intervention risk
- Mineração (~12%): Vale (VALE3), CSN Mineração (CMIN3)
  → Sensitive to China iron ore demand, steel prices, BRL/USD
- Utilities (~8%): Eletrobras (ELET3/ELET6), Engie Brasil (EGIE3), CPFL (CPFE3), Equatorial (EQTL3)
  → Sensitive to energy tariffs, hydrological risk, regulatory environment, interest rates (DCF sensitivity)
- Varejo (~7%): Magazine Luiza (MGLU3), Renner (LREN3), Assaí (ASAI3), Grupo Mateus (GMAT3)
  → Sensitive to Selic rate (consumer credit), employment, real wages, consumer confidence
- Construção Civil/Real Estate (~5%): MRV (MRVE3), Cyrela (CYRE3), Cury (CURY3), EZTec (EZTC3)
  → Highly sensitive to Selic (mortgage rates), FGTS, Minha Casa Minha Vida program, inflation
- Agronegócio (~6%): JBS (JBSS3), BRF (BRFS3), Marfrig (MRFG3), SLC Agrícola (SLCE3)
  → Sensitive to commodity prices, BRL/USD (export revenue), feed costs, global protein demand
- Telecomunicações (~4%): TIM Brasil (TIMS3), Claro (private), Vivo/Telefônica (VIVT3)
  → Relatively defensive, sensitive to consumer spending, interest rates (capex financing)
- Saúde (~5%): Hapvida (HAPV3), Rede D'Or (RDOR3), Fleury (FLRY3)
  → Defensive sector, sensitive to regulatory changes, claims inflation, M&A dynamics
- Siderurgia/Metalurgia (~4%): Gerdau (GGBR4), CSN (CSNA3), Usiminas (USIM5)
  → Sensitive to steel demand (construction + auto), BRL/USD, energy costs, China competition
- Logística/Transporte (~3%): Rumo (RAIL3), Santos Brasil (STBP3), Localiza (RENT3)
  → Sensitive to agro volumes, industrial activity, consumer mobility, fuel costs
- Educação (~2%): Cogna (COGN3), Yduqs (YDUQ3), Ânima (ANIM3)
  → Sensitive to FIES/ProUni policies, Selic (student loans), middle-class income
"""

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a senior equity strategist at a major Brazilian investment bank with \
15+ years of experience translating macroeconomic scenarios into actionable stock recommendations. \
You have deep expertise in:
1. Brazilian macroeconomic transmission mechanisms (monetary policy, fiscal, FX, commodities)
2. Ibovespa sector composition, weights, and sensitivities
3. Individual company fundamentals, leverage, revenue exposure, and operational characteristics
4. Historical patterns of how Brazilian sectors respond to macro cycles

You think rigorously, identify nuance, and are honest about uncertainty. You never confabulate \
company characteristics — if you are uncertain about a specific company metric, you focus on \
directional reasoning rather than false precision.
"""

ANALYSIS_PROMPT_TEMPLATE = """A portfolio manager has described the following macroeconomic scenario \
for Brazil. Analyze it step by step and produce structured investment recommendations.

SCENARIO:
---
{scenario}
---

{market_context}

INSTRUCTIONS — think through each step before writing the final JSON:

STEP 1 — Parse macro variables: Identify each distinct macroeconomic variable in the scenario \
(Selic, BRL/USD, Brent, commodity prices, GDP growth, inflation, etc.), its direction, and magnitude.

STEP 2 — Map transmission channels: For each macro variable, list which sectors it affects and \
through what mechanism (e.g., "Rising Selic → higher funding costs → compresses retail credit margins → \
negative for consumer discretionary"). Be specific about the mechanism, not just the conclusion.

STEP 3 — Net sector impacts: For each sector, net out positive and negative forces from multiple \
macro variables. Rank the top 5 positively impacted and top 5 negatively impacted sectors.

STEP 4 — Ticker selection: Within the most impacted sectors, identify 3 stocks with maximum \
positive exposure and 3 with maximum negative exposure. Choose companies where the macro thesis \
is most concentrated (highest beta to the specific macro variable, structural position, etc.).

STEP 5 — Risk assessment: Identify the top 3 risks that would cause this thesis to fail. Be \
specific about what would need to happen and which recommendations it would invalidate.

Return ONLY the following JSON object. No prose before or after.

{{
  "scenario_input": "{scenario}",
  "scenario_summary": "<structured 2-3 sentence restatement identifying each key macro variable and direction>",

  "key_macro_variables": [
    {{
      "variable": "<e.g. Taxa Selic, Câmbio BRL/USD, Preço do Petróleo Brent>",
      "direction": "<rising|falling|stable|uncertain>",
      "magnitude": "<large|moderate|small>",
      "description": "<how this variable appears in the scenario>"
    }}
  ],

  "benefited_sectors": [
    {{
      "sector": "<sector name in Portuguese>",
      "ibovespa_weight_pct": "<approximate %>",
      "impact_score": <1-10>,
      "direction": "positive",
      "rationale": "<1-2 sentences explaining the specific transmission mechanism>",
      "transmission_channels": ["<channel 1>", "<channel 2>"],
      "confidence": "<high|medium|low>"
    }}
  ],

  "harmed_sectors": [
    {{
      "sector": "<sector name>",
      "ibovespa_weight_pct": "<approximate %>",
      "impact_score": <1-10>,
      "direction": "negative",
      "rationale": "<1-2 sentences explaining the specific transmission mechanism>",
      "transmission_channels": ["<channel 1>", "<channel 2>"],
      "confidence": "<high|medium|low>"
    }}
  ],

  "positive_tickers": [
    {{
      "ticker": "<B3 ticker>",
      "company": "<company name>",
      "sector": "<sector>",
      "direction": "positive",
      "rationale": "<why this company specifically vs sector peers>",
      "key_company_characteristics": "<revenue structure, leverage, geographic exposure driving the thesis>",
      "conviction_score": <1-10>,
      "confidence": "<high|medium|low>"
    }}
  ],

  "negative_tickers": [
    {{
      "ticker": "<B3 ticker>",
      "company": "<company name>",
      "sector": "<sector>",
      "direction": "negative",
      "rationale": "<why this company specifically vs sector peers>",
      "key_company_characteristics": "<what makes it particularly vulnerable>",
      "conviction_score": <1-10>,
      "confidence": "<high|medium|low>"
    }}
  ],

  "thesis_risks": [
    {{
      "risk": "<risk name>",
      "description": "<what would need to happen for this risk to materialize>",
      "probability": "<high|medium|low>",
      "impact": "<severe|moderate|mild>",
      "affected_tickers": ["<ticker1>", "<ticker2>"],
      "mitigation": "<how an investor could hedge or monitor for this risk>"
    }}
  ],

  "overall_market_bias": "<strongly_bullish|moderately_bullish|neutral|moderately_bearish|strongly_bearish>"
}}
"""

SELF_CRITIQUE_PROMPT_TEMPLATE = """You previously generated a macro scenario analysis. \
Now act as a critical second-opinion strategist and evaluate the quality and consistency of \
the analysis.

ORIGINAL SCENARIO:
{scenario}

PRIOR ANALYSIS:
---
{analysis_json}
---

Perform a rigorous internal consistency check:

1. Are there any logical contradictions? (e.g., recommending a sector as "benefited" while \
picking a negative ticker from that same sector without explaining why)
2. Are the transmission mechanisms specific and correct, or are they generic?
3. Are the ticker selections well-justified, or do they reflect superficial reasoning?
4. Are confidence levels appropriately calibrated (not everything should be "high")?
5. What important blind spots or alternative scenarios were not considered?

Return ONLY this JSON:
{{
  "overall_consistency": "<high|medium|low>",
  "logical_conflicts": [
    "<describe any internal contradiction found, or write NONE if analysis is consistent>"
  ],
  "blind_spots": [
    "<what the analysis missed or should have flagged>"
  ],
  "reliability_score": <1-10>,
  "items": [
    {{
      "section": "<benefited_sectors|harmed_sectors|positive_tickers|negative_tickers|thesis_risks>",
      "issue_found": <true|false>,
      "critique": "<what is solid or problematic in this section>",
      "confidence_after_review": "<high|medium|low>"
    }}
  ]
}}
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


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    return json.loads(text)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Sensitivity Analysis
# ---------------------------------------------------------------------------

SENSITIVITY_PROMPT_TEMPLATE = """You are a senior Brazilian equity strategist.

CENTRAL MACRO SCENARIO:
---
{scenario}
---

Generate 3 stress-test variants of this scenario to test the robustness of investment theses.
Each variant must be 2-3 sentences, grounded in realistic Brazilian macro dynamics.

1. OPTIMISTIC: macro conditions are meaningfully more favorable (faster rate cuts, BRL appreciation, stronger commodities, fiscal improvement)
2. BASE: essentially the same scenario — minor restatement only
3. PESSIMISTIC: macro conditions are meaningfully worse (Selic stagnates or rises, BRL depreciates further, commodities fall, fiscal deterioration)

Return ONLY this JSON:
{{
  "optimistic": "<2-3 sentences describing the optimistic variant>",
  "base": "<2-3 sentences restating the original scenario>",
  "pessimistic": "<2-3 sentences describing the pessimistic variant>"
}}
"""


def generate_scenario_variants(scenario: str) -> dict[str, str]:
    """Generate optimistic/base/pessimistic variants from a central scenario."""
    client = _get_client()
    raw = _call_llm(
        client,
        SYSTEM_PROMPT,
        SENSITIVITY_PROMPT_TEMPLATE.format(scenario=scenario),
    )
    return _parse_json(raw)


def analyze_sensitivity(scenario: str) -> dict[str, MacroScenarioAnalysis]:
    """Sensitivity analysis: run the full pipeline on 3 scenario variants.

    Self-critique disabled to reduce API calls (4 total instead of 7).
    Returns dict with keys: 'pessimistic', 'base', 'optimistic'.
    """
    variants = generate_scenario_variants(scenario)
    return {
        label: analyze_scenario(variant_scenario, enable_self_critique=False)
        for label, variant_scenario in variants.items()
    }


def analyze_scenario(scenario: str, enable_self_critique: bool = True) -> MacroScenarioAnalysis:
    """Run macro scenario → sector → ticker analysis pipeline.

    Args:
        scenario: Natural language macro scenario description.
        enable_self_critique: Run a second LLM pass to review consistency.

    Returns:
        MacroScenarioAnalysis with all structured fields populated.
    """
    client = _get_client()

    # --- Pass 1: Main analysis ---
    user_prompt = ANALYSIS_PROMPT_TEMPLATE.format(
        scenario=scenario,
        market_context=BRAZIL_MARKET_CONTEXT,
    )
    raw = _call_llm(client, SYSTEM_PROMPT, user_prompt)

    try:
        data = _parse_json(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON:\n{raw[:500]}\n\nError: {e}") from e

    analysis = MacroScenarioAnalysis.model_validate(data)

    # --- Pass 2: Self-critique ---
    if enable_self_critique:
        critique_prompt = SELF_CRITIQUE_PROMPT_TEMPLATE.format(
            scenario=scenario,
            analysis_json=json.dumps(data, ensure_ascii=False, indent=2),
        )
        raw_critique = _call_llm(client, SYSTEM_PROMPT, critique_prompt)
        try:
            critique_data = _parse_json(raw_critique)
            analysis.self_critique = SelfCritique.model_validate(critique_data)
        except Exception:
            pass

    return analysis
