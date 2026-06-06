from __future__ import annotations

from datetime import datetime

from .models import EarningsCallAnalysis

_SENTIMENT_ICON = {
    "bullish": "📈", "cautious": "⚠️", "neutral": "➡️",
    "defensive": "🛡️", "bearish": "📉",
}
_QUALITY_ICON = {
    "excellent": "✅", "good": "🟢", "evasive": "🟡",
    "incomplete": "🟠", "deflected": "🔴",
}
_FLAG_LABEL = {
    "hesitation": "Hesitação", "topic_change": "Mudança de assunto",
    "evasion": "Evasão", "defensive_language": "Linguagem defensiva",
    "vague_answer": "Resposta vaga",
}


def generate_report(analysis: EarningsCallAnalysis, max_words: int = 400) -> str:
    """Generate an executive markdown report (target: ≤400 words, readable in 2 min)."""
    lines: list[str] = []

    # Header (compact)
    lines.append(f"# {analysis.company} ({analysis.ticker}) — {analysis.quarter}")
    lines.append(f"*Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}*\n")

    # Tone (1 sentence justification only)
    icon = _SENTIMENT_ICON.get(analysis.management_tone.overall_sentiment, "")
    lines.append(
        f"## {icon} Tom: `{analysis.management_tone.overall_sentiment.upper()}` "
        f"({analysis.management_tone.confidence_score}/10)"
    )
    # Take first sentence of justification
    just = analysis.management_tone.justification.split(".")[0] + "."
    lines.append(just)
    if analysis.management_tone.supporting_excerpts:
        ex = analysis.management_tone.supporting_excerpts[0]
        lines.append(f'> *"{ex.quote[:120]}..."* — {ex.speaker}\n')

    # Guidance (summary only + table with high-significance items only)
    lines.append("## 📊 Guidance")
    lines.append(analysis.guidance_changes.summary)
    high_sig = [i for i in analysis.guidance_changes.items if i.significance == "high"]
    if high_sig:
        lines.append("\n| Métrica | Anterior → Atual | Impacto |")
        lines.append("|---------|-----------------|---------|")
        for item in high_sig[:3]:
            arrow = {"increase": "⬆️", "decrease": "⬇️", "maintained": "➡️",
                     "new_guidance": "🆕", "removed": "❌"}.get(item.direction, "")
            prev = item.previous or "—"
            lines.append(f"| {item.metric} | {prev} → {item.current} | {arrow} {item.significance} |")
    lines.append("")

    # Top analyst questions (compact)
    lines.append("## ❓ Top 3 Perguntas")
    for q in sorted(analysis.top_analyst_questions, key=lambda x: x.rank):
        qi = _QUALITY_ICON.get(q.response_quality, "")
        lines.append(
            f"**{q.rank}. {q.analyst_name} ({q.institution})** {qi} `{q.response_quality}` — "
            f"{q.question_summary[:80]}... *Resposta:* {q.response_summary[:80]}..."
        )
    lines.append("")

    # Red flags (top 2 highest severity only, compact)
    priority = {"high": 0, "medium": 1, "low": 2}
    top_flags = sorted(analysis.red_flags, key=lambda f: priority.get(f.severity, 3))[:2]
    if top_flags:
        lines.append("## 🚩 Red Flags")
        for rf in top_flags:
            sev = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rf.severity, "")
            label = _FLAG_LABEL.get(rf.flag_type, rf.flag_type)
            lines.append(f"{sev} **{label}** — {rf.speaker}")
            lines.append(f'> *"{rf.excerpt[:100]}..."*')
        lines.append("")

    # Surprise score
    ss = analysis.surprise_score
    lines.append(f"## ⚡ Surprise Score: {ss.score}/10")
    lines.append(ss.rationale[:150] + ("..." if len(ss.rationale) > 150 else ""))
    for item in ss.items[:2]:
        impact = {"positive": "📈", "negative": "📉", "neutral": "➡️", "mixed": "↔️"}.get(
            item.market_impact_assessment, ""
        )
        lines.append(f"- {impact} **{item.element}**: {item.why_surprising[:80]}...")

    # Self-critique badge (single line)
    if analysis.self_critique:
        sc = analysis.self_critique
        lines.append(
            f"\n---\n*Self-critique: **{sc.overall_quality.upper()}** — "
            f"confiabilidade {sc.reliability_score}/10*"
        )

    # Temporal comparison badge (single line)
    if analysis.temporal_comparison:
        tc = analysis.temporal_comparison
        _arrow = {"improved": "↗", "deteriorated": "↘", "stable": "→"}
        delta = tc.surprise_score_delta
        lines.append(
            f"*Q/Q ({tc.previous_quarter}→{tc.current_quarter}): "
            f"tom {_arrow.get(tc.tone_evolution.direction,'→')} "
            f"({tc.tone_evolution.previous_sentiment}→{tc.tone_evolution.current_sentiment}) | "
            f"surprise score {'+' if delta > 0 else ''}{delta}*"
        )

    # Market reaction badge (single line)
    if analysis.market_reaction and analysis.market_reaction.data_available:
        mr = analysis.market_reaction
        a1 = f"{mr.alpha_d1_pct:+.1f}%" if mr.alpha_d1_pct is not None else "—"
        a5 = f"{mr.alpha_d5_pct:+.1f}%" if mr.alpha_d5_pct is not None else "—"
        lines.append(f"*Mercado: alpha D+1 {a1} | D+5 {a5} vs Ibovespa*")

    report = "\n".join(lines)

    # Enforce word limit — truncate to max_words with a small buffer for the suffix
    words = report.split()
    if len(words) > max_words:
        report = " ".join(words[: max_words - 8]) + "\n\n*[truncado — 400 palavras max]*"

    return report
