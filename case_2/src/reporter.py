from __future__ import annotations

from datetime import datetime

from .models import MacroScenarioAnalysis

_BIAS_LABEL = {
    "strongly_bullish":    "Fortemente Positivo",
    "moderately_bullish":  "Moderadamente Positivo",
    "neutral":             "Neutro",
    "moderately_bearish":  "Moderadamente Negativo",
    "strongly_bearish":    "Fortemente Negativo",
}
_CONF = {"high": "alta", "medium": "média", "low": "baixa"}
_PROB = {"high": "alta", "medium": "média", "low": "baixa"}
_DIR  = {"rising": "em alta", "falling": "em queda", "stable": "estável", "uncertain": "incerto"}


def _trunc(text: str, n: int) -> str:
    """Truncate at word boundary."""
    if len(text) <= n:
        return text
    return text[:n].rsplit(" ", 1)[0].rstrip(".,;:") + "…"


def generate_report(analysis: MacroScenarioAnalysis) -> str:
    bias  = _BIAS_LABEL.get(analysis.overall_market_bias, analysis.overall_market_bias)
    lines: list[str] = []

    # ── Cabeçalho ──────────────────────────────────────────────────────────
    lines += [
        f"**MACRO SCENARIO ENGINE — Impacto para Bolsa Brasileira**",
        f"*{datetime.now().strftime('%d/%m/%Y %H:%M')} · Viés: {bias}*",
        "",
        "---",
        "",
    ]

    # ── Cenário ────────────────────────────────────────────────────────────
    lines += [
        "**Cenário**",
        "",
        _trunc(analysis.scenario_summary, 300),
        "",
        "---",
        "",
    ]

    # ── Variáveis macro ─────────────────────────────────────────────────────
    lines.append("**Variáveis Macro Identificadas**")
    lines.append("")
    for v in analysis.key_macro_variables:
        lines.append(f"- {v.variable}: {_DIR.get(v.direction, v.direction)}, magnitude {v.magnitude}")
    lines += ["", "---", ""]

    # ── Setores beneficiados ────────────────────────────────────────────────
    lines.append("**Setores Beneficiados**")
    lines.append("")
    for i, s in enumerate(analysis.benefited_sectors, 1):
        conf = _CONF.get(s.confidence, s.confidence)
        lines.append(f"**{i}. {s.sector}** · {s.ibovespa_weight_pct} do Ibovespa · score {s.impact_score}/10 · confiança {conf}")
        lines.append(f"> {_trunc(s.rationale, 140)}")
        lines.append("")
    lines += ["---", ""]

    # ── Setores prejudicados ────────────────────────────────────────────────
    lines.append("**Setores Prejudicados**")
    lines.append("")
    for i, s in enumerate(analysis.harmed_sectors, 1):
        conf = _CONF.get(s.confidence, s.confidence)
        lines.append(f"**{i}. {s.sector}** · {s.ibovespa_weight_pct} do Ibovespa · score {s.impact_score}/10 · confiança {conf}")
        lines.append(f"> {_trunc(s.rationale, 140)}")
        lines.append("")
    lines += ["---", ""]

    # ── Tickers ─────────────────────────────────────────────────────────────
    lines.append("**Tickers**")
    lines.append("")
    lines.append("| Direção | Ticker | Convicção | Tese |")
    lines.append("|:-------:|:------:|:---------:|------|")
    for t in analysis.positive_tickers:
        lines.append(f"| Comprar | **{t.ticker}** | {t.conviction_score}/10 | {_trunc(t.rationale, 100)} |")
    for t in analysis.negative_tickers:
        lines.append(f"| Vender | **{t.ticker}** | {t.conviction_score}/10 | {_trunc(t.rationale, 100)} |")
    lines += ["", "---", ""]

    # ── Riscos ──────────────────────────────────────────────────────────────
    lines.append("**Riscos da Tese**")
    lines.append("")
    for i, r in enumerate(analysis.thesis_risks, 1):
        prob   = _PROB.get(r.probability, r.probability)
        tkrs   = ", ".join(f"`{tk}`" for tk in r.affected_tickers[:3]) if r.affected_tickers else "—"
        lines.append(f"**{i}. {r.risk}** · prob. {prob} · impacto {r.impact} · afeta {tkrs}")
        lines.append(f"> {_trunc(r.description, 120)}")
        lines.append("")

    # ── Self-critique ───────────────────────────────────────────────────────
    if analysis.self_critique:
        sc = analysis.self_critique
        lines += [
            "---",
            "",
            f"*Self-critique — consistência: {sc.overall_consistency} · confiabilidade: {sc.reliability_score}/10*",
        ]
        if sc.blind_spots:
            lines.append(f"*Ponto cego: {_trunc(sc.blind_spots[0], 110)}*")

    return "\n".join(lines)
