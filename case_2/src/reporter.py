from __future__ import annotations

from datetime import datetime

from .models import MacroScenarioAnalysis

_BIAS_LABEL = {
    "strongly_bullish": "📈📈 FORTEMENTE POSITIVO",
    "moderately_bullish": "📈 MODERADAMENTE POSITIVO",
    "neutral": "➡️ NEUTRO",
    "moderately_bearish": "📉 MODERADAMENTE NEGATIVO",
    "strongly_bearish": "📉📉 FORTEMENTE NEGATIVO",
}
_CONF = {"high": "🟢", "medium": "🟡", "low": "🔴"}
_PROB = {"high": "🔴", "medium": "🟡", "low": "🟢"}
_DIR = {"rising": "⬆️", "falling": "⬇️", "stable": "➡️", "uncertain": "❓"}


def generate_report(analysis: MacroScenarioAnalysis, max_words: int = 500) -> str:
    """Generate executive markdown report (target: ≤500 words, readable in 3 min)."""
    lines: list[str] = []
    bias = _BIAS_LABEL.get(analysis.overall_market_bias, analysis.overall_market_bias)

    lines.append(f"**Macro Scenario Engine — Impacto para Bolsa Brasileira**")
    lines.append(f"*{datetime.now().strftime('%d/%m/%Y %H:%M')} | Viés: {bias}*\n")

    # Scenario (1-2 sentences)
    lines.append(f"**Cenário:** {analysis.scenario_summary}\n")

    # Macro variables (compact inline)
    vars_str = " | ".join(
        f"{v.variable} {_DIR.get(v.direction, '')} ({v.magnitude})"
        for v in analysis.key_macro_variables
    )
    lines.append(f"**Variáveis:** {vars_str}\n")

    # Sectors (compact table — sector + 1-sentence rationale)
    lines.append("**Setores Beneficiados**")
    lines.append("| Setor | Peso | Score | Mecanismo-chave |")
    lines.append("|-------|------|-------|-----------------|")
    for i, s in enumerate(analysis.benefited_sectors, 1):
        rationale_short = s.rationale.split(".")[0][:70]
        c = _CONF.get(s.confidence, "")
        lines.append(f"| **{i}. {s.sector}** | {s.ibovespa_weight_pct} | {s.impact_score}/10 {c} | {rationale_short} |")
    lines.append("")

    lines.append("**Setores Prejudicados**")
    lines.append("| Setor | Peso | Score | Mecanismo-chave |")
    lines.append("|-------|------|-------|-----------------|")
    for i, s in enumerate(analysis.harmed_sectors, 1):
        rationale_short = s.rationale.split(".")[0][:70]
        c = _CONF.get(s.confidence, "")
        lines.append(f"| **{i}. {s.sector}** | {s.ibovespa_weight_pct} | {s.impact_score}/10 {c} | {rationale_short} |")
    lines.append("")

    # Tickers (compact — one line each)
    lines.append("**Tickers — Comprar / Vender**")
    lines.append("| Dir | Ticker | Convicção | Tese |")
    lines.append("|-----|--------|-----------|------|")
    for t in analysis.positive_tickers:
        c = _CONF.get(t.confidence, "")
        tese = t.rationale.split(".")[0][:70]
        lines.append(f"| ↑ | **`{t.ticker}`** {c} | {t.conviction_score}/10 | {tese} |")
    for t in analysis.negative_tickers:
        c = _CONF.get(t.confidence, "")
        tese = t.rationale.split(".")[0][:70]
        lines.append(f"| ↓ | **`{t.ticker}`** {c} | {t.conviction_score}/10 | {tese} |")
    lines.append("")

    # Risks (compact)
    lines.append("**Riscos da Tese**")
    for i, r in enumerate(analysis.thesis_risks, 1):
        p = _PROB.get(r.probability, "")
        tickers = ", ".join(f"`{tk}`" for tk in r.affected_tickers[:2])
        desc_short = r.description.split(".")[0][:80]
        lines.append(f"**{i}. {r.risk}** {p} — {desc_short}. Afeta: {tickers}")
    lines.append("")

    # Self-critique (1 line)
    if analysis.self_critique:
        sc = analysis.self_critique
        lines.append(
            f"---\n*Self-critique: **{sc.overall_consistency.upper()}** — "
            f"confiabilidade {sc.reliability_score}/10*"
        )
        if sc.blind_spots:
            lines.append(f"*Ponto cego: {sc.blind_spots[0][:80]}...*")

    report = "\n".join(lines)

    # Enforce word limit
    words = report.split()
    if len(words) > max_words:
        report = " ".join(words[: max_words - 8]) + "\n\n*[truncado — 500 palavras max]*"

    return report
