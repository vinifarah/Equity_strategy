"""
Macro Scenario Engine — Streamlit Interface
Run with: streamlit run app.py
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src.analyzer import analyze_scenario, analyze_sensitivity
from src.reporter import generate_report

load_dotenv()

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="BBI | Macro Scenario Engine",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* ===== BRADESCO BBI — TEMA CLARO ===== */

    #MainMenu  { visibility: hidden; }
    footer     { visibility: hidden; }

    /* Garante texto escuro em todo o conteúdo */
    p, span, label, li, td, th, div { color: #333333; }
    h1, h2, h3, h4 { color: #1A1A1A; }

    /* Fundo geral branco-suave */
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMainBlockContainer"] {
        background: #FAFAFA !important;
    }

    /* ── SIDEBAR VERMELHA ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #CC0000 0%, #990000 100%) !important;
        border-right: none !important;
    }
    [data-testid="stSidebar"] * {
        color: rgba(255,255,255,0.9) !important;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #FFFFFF !important;
        font-weight: 800 !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.25) !important;
    }
    [data-testid="stSidebar"] [data-baseweb="select"] > div {
        background: rgba(255,255,255,0.15) !important;
        border-color: rgba(255,255,255,0.3) !important;
        color: white !important;
    }
    [data-testid="stSidebar"] .stButton > button {
        background: rgba(255,255,255,0.15) !important;
        border: 1px solid rgba(255,255,255,0.35) !important;
        color: white !important;
        font-weight: 600 !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(255,255,255,0.28) !important;
    }

    /* ── BOTÃO PRIMÁRIO ── */
    .stButton > button[kind="primary"] {
        background: #CC0000 !important;
        border: none !important;
        color: white !important;
        font-weight: 700 !important;
        letter-spacing: 0.04em !important;
        border-radius: 4px !important;
        padding: 0.5rem 1.2rem !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: #990000 !important;
        box-shadow: 0 3px 12px rgba(204,0,0,0.4) !important;
        transform: translateY(-1px);
    }

    /* ── TABS ── */
    .stTabs [data-baseweb="tab-list"] {
        background: white !important;
        border-bottom: 2px solid #CC0000 !important;
        border-radius: 4px 4px 0 0;
    }
    .stTabs [data-baseweb="tab"] {
        color: #666 !important;
        font-weight: 600 !important;
    }
    .stTabs [aria-selected="true"] {
        color: #CC0000 !important;
        border-bottom: 3px solid #CC0000 !important;
    }

    /* ── MÉTRICAS ── */
    [data-testid="stMetricLabel"] {
        font-size: 0.72rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        color: #999 !important;
        font-weight: 600 !important;
    }
    [data-testid="stMetricValue"] {
        color: #CC0000 !important;
        font-weight: 800 !important;
    }

    /* ── EXPANDERS ── */
    [data-testid="stExpander"] {
        border: 1px solid #F0E0E0 !important;
        border-radius: 6px !important;
        border-left: 3px solid #CC0000 !important;
    }

    /* ── SECTION HEADER ── */
    .section-header {
        font-size: 1.0rem; font-weight: 800;
        border-bottom: 2px solid #CC0000;
        padding-bottom: 5px; margin-bottom: 12px;
        color: #1A1A1A; text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .scenario-summary {
        font-size: 0.95rem; color: #2A2A2A;
        line-height: 1.65; margin-bottom: 10px;
    }
    .bias-pill {
        display: inline-block; padding: 4px 14px;
        border-radius: 20px; font-weight: 700;
        font-size: 0.82rem; letter-spacing: 0.04em;
    }
    .macro-card {
        background: #F8F8F8; border-radius: 5px;
        padding: 10px 12px; text-align: center;
        border-top: 3px solid #CC0000;
    }
    .macro-card-label {
        font-size: 0.68rem; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.08em;
        color: #999; margin-bottom: 6px;
    }
    .macro-card-value {
        font-size: 0.88rem; font-weight: 800;
    }
    .macro-card-mag {
        font-size: 0.7rem; color: #AAA; margin-top: 4px;
    }

    /* ── COMPONENTES ORIGINAIS ── */
    .ticker-badge {
        background: #CC0000; color: white;
        padding: 2px 8px; border-radius: 4px;
        font-family: monospace; font-weight: 700;
    }

    /* ── BARRA SUPERIOR ── */
    header[data-testid="stHeader"] {
        background: #CC0000 !important;
    }
    [data-testid="stDecoration"] {
        background: #CC0000 !important;
    }
    [data-testid="stHeader"] button svg {
        fill: white !important;
    }

    /* ── CAMPOS DE TEXTO / TEXTAREA ── */
    textarea,
    [data-testid="stTextArea"] textarea,
    [data-baseweb="textarea"] textarea,
    [data-testid="stTextInput"] input,
    [data-baseweb="input"] input {
        background: #FFFFFF !important;
        color: #1A1A1A !important;
        border: 1px solid #E0C0C0 !important;
        border-radius: 4px !important;
    }
    textarea:focus,
    [data-testid="stTextArea"] textarea:focus,
    [data-testid="stTextInput"] input:focus {
        border-color: #CC0000 !important;
        box-shadow: 0 0 0 2px rgba(204,0,0,0.15) !important;
    }
    [data-testid="stTextArea"] label,
    [data-testid="stTextInput"] label {
        color: #555 !important;
        font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
for _k, _v in [
    ("_last_scenario", ""),
    ("_sensitivity_results", None),
    ("_comp_a", None),
    ("_comp_b", None),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div style="padding:16px 0 8px 0;border-bottom:1px solid rgba(204,0,0,0.3);margin-bottom:16px;">
        <div style="color:#CC0000;font-weight:900;font-size:1.1rem;letter-spacing:0.05em;">BRADESCO BBI</div>
        <div style="color:#999;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.12em;margin-top:2px;">Equity Strategy</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("## ⚙️ Configurações")
    enable_critique = st.toggle("Self-critique loop", value=True, help="Roda uma segunda passagem do LLM para validar consistência interna da análise")
    show_json = st.toggle("Mostrar JSON bruto", value=False)
    save_outputs = st.toggle("Salvar outputs em disco", value=True)

    st.markdown("---")
    st.markdown("### 💡 Cenários de exemplo")
    example_scenarios = {
        "Queda de juros + BRL fraco": "A Selic cai para 10% ao longo de 2025, mas o câmbio permanece pressionado em torno de BRL 5,80 por dólar devido ao risco fiscal. Ao mesmo tempo, o preço do petróleo Brent se mantém em USD 80/barril e as commodities metálicas (minério de ferro) estão em alta de 15% no ano, puxadas pela recuperação da demanda chinesa.",
        "Crescimento + inflação controlada": "O PIB do Brasil cresce 3% em 2025, com inflação convergindo para a meta de 3%. O Banco Central mantém a Selic em 12% mas com perspectiva de cortes para o segundo semestre. O câmbio está estável em BRL 5,20 e há aceleração da Reforma Tributária com impacto positivo no setor industrial.",
        "Crise fiscal + Selic sobe": "O governo anuncia um déficit fiscal maior que o esperado, de 1,5% do PIB para 2025. O mercado precifica alta da Selic de volta para 15%. O câmbio dispara para BRL 6,50. As curvas de juros longa abrem 150bps. Há fuga de capital estrangeiro da bolsa brasileira.",
        "China fraca + commodities em queda": "Dados de atividade industrial chinesa decepcionam pelo terceiro mês consecutivo. O preço do minério de ferro cai 20% e o petróleo recua para USD 65/barril. No Brasil, a Selic está em 12,5% com perspectiva de manutenção. O agronegócio continua forte puxado pela soja.",
    }
    selected_example = st.selectbox("Carregar exemplo", ["(nenhum)"] + list(example_scenarios.keys()))

# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------
st.markdown("""
<div style="background:linear-gradient(135deg,#CC0000 0%,#8B0000 100%);
            border-radius:8px;padding:24px 32px;margin-bottom:24px;">
    <div style="color:rgba(255,255,255,0.7);font-size:0.7rem;text-transform:uppercase;
                letter-spacing:0.2em;font-weight:700;">BRADESCO BBI — EQUITY STRATEGY</div>
    <div style="color:#FFFFFF;font-size:1.7rem;font-weight:900;margin-top:6px;
                letter-spacing:-0.01em;line-height:1.2;">
        Macro Scenario Engine
    </div>
    <div style="color:rgba(255,255,255,0.8);font-size:0.88rem;margin-top:6px;
                font-weight:400;">
        Tradução de cenários macro em recomendações setoriais e tickers
    </div>
</div>
""", unsafe_allow_html=True)

# Bias display constants (module-level so sensitivity/comparison sections can also use them)
_BIAS_FG = {
    "strongly_bullish": "#1A6B3C", "moderately_bullish": "#1A6B3C",
    "neutral": "#2471A3",
    "moderately_bearish": "#CC0000", "strongly_bearish": "#CC0000",
}
_BIAS_BG = {
    "strongly_bullish": "#EBF7F0", "moderately_bullish": "#EBF7F0",
    "neutral": "#EAF4FB",
    "moderately_bearish": "#FFF0F0", "strongly_bearish": "#FFF0F0",
}
_BIAS_LABELS = {
    "strongly_bullish": "Fortemente Positivo",
    "moderately_bullish": "Moderadamente Positivo",
    "neutral": "Neutro",
    "moderately_bearish": "Moderadamente Negativo",
    "strongly_bearish": "Fortemente Negativo",
}
_BIAS_COLORS = {
    "strongly_bullish": "green", "moderately_bullish": "green",
    "neutral": "blue",
    "moderately_bearish": "red", "strongly_bearish": "red",
}

# Scenario input
default_text = example_scenarios.get(selected_example, "") if selected_example != "(nenhum)" else ""
scenario_input = st.text_area(
    "Descreva o cenário macroeconômico em linguagem natural:",
    value=default_text,
    height=140,
    placeholder="Ex: A Selic cai para 10%, o câmbio está em 5,50, commodities metálicas em alta puxadas pela China...",
    help="Inclua variáveis como Selic, câmbio, commodities, crescimento do PIB, inflação, ambiente fiscal.",
)

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    run_button = st.button("🚀 Analisar Cenário", type="primary", use_container_width=True)
with col2:
    word_count = len(scenario_input.split()) if scenario_input else 0
    st.metric("Palavras no cenário", word_count)
with col3:
    st.metric("Self-critique", "Ativo" if enable_critique else "Inativo")

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
if run_button:
    if not scenario_input.strip():
        st.error("Por favor, insira um cenário macroeconômico.")
        st.stop()

    if len(scenario_input.strip()) < 20:
        st.warning("Cenário muito curto. Adicione mais detalhes para uma análise mais precisa.")

    if not os.getenv("ANTHROPIC_API_KEY"):
        st.error("ANTHROPIC_API_KEY não configurada. Crie um arquivo .env com a chave.")
        st.stop()

    with st.spinner("Analisando cenário macro → impacto setorial → tickers... (pode levar 30-60s)"):
        try:
            analysis = analyze_scenario(scenario_input, enable_self_critique=enable_critique)
        except Exception as e:
            st.error(f"Erro na análise: {e}")
            st.stop()

    # Save to disk
    if save_outputs:
        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        (output_dir / f"scenario_{ts}.json").write_text(
            analysis.model_dump_json(indent=2), encoding="utf-8"
        )
        report_md = generate_report(analysis)
        (output_dir / f"scenario_{ts}.md").write_text(report_md, encoding="utf-8")
        st.success(f"Outputs salvos em `outputs/scenario_{ts}.[json|md]`")

    # --- Render results ---
    st.markdown("---")

    # Scenario summary + bias
    b_fg = _BIAS_FG.get(analysis.overall_market_bias, "#555")
    b_bg = _BIAS_BG.get(analysis.overall_market_bias, "#F5F5F5")
    b_label = _BIAS_LABELS.get(analysis.overall_market_bias, analysis.overall_market_bias)

    st.markdown(
        f'<div style="margin-bottom:4px">'
        f'<span style="font-size:0.65rem;font-weight:800;text-transform:uppercase;'
        f'letter-spacing:0.14em;color:#CC0000;">Síntese do Cenário</span></div>'
        f'<div class="scenario-summary">{analysis.scenario_summary}</div>'
        f'<div style="margin-bottom:16px">'
        f'<span style="font-size:0.68rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:0.1em;color:#999;margin-right:8px">Viés de mercado</span>'
        f'<span class="bias-pill" style="background:{b_bg};color:{b_fg}">{b_label}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    with st.expander("📝 Cenário inserido", expanded=False):
        st.markdown(
            f'<div style="background:#f8f9fa;border-left:3px solid #CC0000;padding:12px 16px;'
            f'border-radius:0 6px 6px 0;font-size:0.95rem;color:#333;white-space:pre-wrap;">'
            f'{scenario_input}</div>',
            unsafe_allow_html=True,
        )

    # Macro variables
    with st.expander("Variáveis Macro Identificadas", expanded=True):
        _dir_color = {"rising": "#CC0000", "falling": "#1A6B3C", "stable": "#555555", "uncertain": "#B7770D"}
        _dir_label = {"rising": "Em Alta", "falling": "Em Queda", "stable": "Estável", "uncertain": "Incerto"}
        _mag_label = {"large": "Magnitude Alta", "moderate": "Magnitude Moderada", "small": "Magnitude Pequena"}
        cols = st.columns(len(analysis.key_macro_variables))
        for col, var in zip(cols, analysis.key_macro_variables):
            with col:
                c = _dir_color.get(var.direction, "#555")
                st.markdown(
                    f'<div class="macro-card" style="border-top-color:{c}">'
                    f'<div class="macro-card-label">{var.variable}</div>'
                    f'<div class="macro-card-value" style="color:{c}">'
                    f'{_dir_label.get(var.direction, var.direction)}</div>'
                    f'<div class="macro-card-mag">{_mag_label.get(var.magnitude, var.magnitude)}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    st.markdown("---")

    # Sectors side by side
    col_pos, col_neg = st.columns(2)

    with col_pos:
        st.markdown('<p class="section-header">Top 5 Setores Beneficiados</p>', unsafe_allow_html=True)
        for i, s in enumerate(analysis.benefited_sectors, 1):
            conf_color = {"high": "green", "medium": "orange", "low": "red"}.get(s.confidence, "blue")
            with st.container():
                st.markdown(f"**{i}. {s.sector}** `{s.ibovespa_weight_pct}` — Score: {s.impact_score}/10 :{conf_color}[●]")
                st.caption(s.rationale)
                with st.expander("Canais de transmissão"):
                    for ch in s.transmission_channels:
                        st.markdown(f"- {ch}")

    with col_neg:
        st.markdown('<p class="section-header">Top 5 Setores Prejudicados</p>', unsafe_allow_html=True)
        for i, s in enumerate(analysis.harmed_sectors, 1):
            conf_color = {"high": "green", "medium": "orange", "low": "red"}.get(s.confidence, "blue")
            with st.container():
                st.markdown(f"**{i}. {s.sector}** `{s.ibovespa_weight_pct}` — Score: {s.impact_score}/10 :{conf_color}[●]")
                st.caption(s.rationale)
                with st.expander("Canais de transmissão"):
                    for ch in s.transmission_channels:
                        st.markdown(f"- {ch}")

    st.markdown("---")

    # Tickers
    col_buy, col_sell = st.columns(2)

    with col_buy:
        st.markdown('<p class="section-header">Tickers com Exposição Positiva</p>', unsafe_allow_html=True)
        for t in analysis.positive_tickers:
            conf_icon = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(t.confidence, "")
            with st.expander(f"{conf_icon} `{t.ticker}` — {t.company} | Convicção: {t.conviction_score}/10"):
                st.markdown(f"**Setor:** {t.sector}")
                st.markdown(f"**Tese:** {t.rationale}")
                st.markdown(f"**Características-chave:** {t.key_company_characteristics}")
                st.markdown(f"**Confiança:** {t.confidence}")

    with col_sell:
        st.markdown('<p class="section-header">Tickers com Exposição Negativa</p>', unsafe_allow_html=True)
        for t in analysis.negative_tickers:
            conf_icon = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(t.confidence, "")
            with st.expander(f"{conf_icon} `{t.ticker}` — {t.company} | Convicção: {t.conviction_score}/10"):
                st.markdown(f"**Setor:** {t.sector}")
                st.markdown(f"**Tese:** {t.rationale}")
                st.markdown(f"**Vulnerabilidade:** {t.key_company_characteristics}")
                st.markdown(f"**Confiança:** {t.confidence}")

    st.markdown("---")

    # Risks
    st.markdown('<p class="section-header">Top 3 Riscos da Tese</p>', unsafe_allow_html=True)
    prob_colors = {"high": "red", "medium": "orange", "low": "green"}
    for i, r in enumerate(analysis.thesis_risks, 1):
        prob_color = prob_colors.get(r.probability, "blue")
        with st.expander(f"**{i}. {r.risk}** — Probabilidade: :{prob_color}[{r.probability.upper()}] | Impacto: {r.impact}"):
            st.markdown(f"**O que precisa acontecer:** {r.description}")
            tickers_affected = ", ".join(f"`{tk}`" for tk in r.affected_tickers) if r.affected_tickers else "N/A"
            st.markdown(f"**Tickers afetados:** {tickers_affected}")
            st.markdown(f"**Mitigação:** {r.mitigation}")

    # Self-critique
    if analysis.self_critique:
        sc = analysis.self_critique
        st.markdown("---")
        with st.expander(f"🔍 Self-Critique — Confiabilidade: {sc.reliability_score}/10 | Consistência: {sc.overall_consistency.upper()}"):
            if sc.logical_conflicts and sc.logical_conflicts[0].upper() != "NONE":
                st.warning("**Conflitos identificados:**")
                for conflict in sc.logical_conflicts:
                    st.markdown(f"- ⚠️ {conflict}")
            else:
                st.success("Nenhum conflito lógico interno identificado.")

            if sc.blind_spots:
                st.info("**Pontos cegos / considerações adicionais:**")
                for bs in sc.blind_spots:
                    st.markdown(f"- 💡 {bs}")

            st.markdown("**Avaliação por seção:**")
            for item in sc.items:
                icon = "❌" if item.issue_found else "✅"
                st.markdown(f"{icon} **{item.section}** — {item.critique} _(conf: {item.confidence_after_review})_")

    # Full markdown report
    st.markdown("---")
    with st.expander("📄 Relatório Executivo Completo (Markdown)"):
        report_md = generate_report(analysis)
        st.markdown(report_md)
        st.download_button(
            "⬇️ Baixar Relatório (.md)",
            data=report_md,
            file_name=f"scenario_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
        )

    # Raw JSON
    if show_json:
        with st.expander("🔧 JSON Estruturado (raw)"):
            st.json(json.loads(analysis.model_dump_json()))
            st.download_button(
                "⬇️ Baixar JSON",
                data=analysis.model_dump_json(indent=2),
                file_name=f"scenario_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
            )

    # Persist for advanced tools
    st.session_state["_last_scenario"] = scenario_input
    st.session_state["_sensitivity_results"] = None  # reset on new analysis

# ===========================================================================
# ANÁLISE DE SENSIBILIDADE
# ===========================================================================
if st.session_state["_last_scenario"]:
    st.markdown("---")
    st.markdown("## 🎯 Análise de Sensibilidade")
    st.caption("Gera 3 variantes do cenário (otimista / base / pessimista) e compara como as recomendações divergem.")

    if st.button("▶ Rodar Análise de Sensibilidade", use_container_width=True, key="btn_sensitivity"):
        if not os.getenv("ANTHROPIC_API_KEY"):
            st.error("ANTHROPIC_API_KEY não configurada.")
        else:
            with st.spinner("Gerando variantes e analisando os 3 cenários… (4 chamadas à API)"):
                try:
                    st.session_state["_sensitivity_results"] = analyze_sensitivity(
                        st.session_state["_last_scenario"]
                    )
                except Exception as e:
                    st.error(f"Erro: {e}")

    sens = st.session_state["_sensitivity_results"]
    if sens:
        _ORDER  = ["pessimistic", "base", "optimistic"]
        _LABELS = {"pessimistic": "📉 Pessimista", "base": "➡️ Base", "optimistic": "📈 Otimista"}
        _COLORS = {"pessimistic": "#c0392b",       "base": "#2471a3",  "optimistic": "#27ae60"}

        # --- 3 colunas de visão geral ---
        cols = st.columns(3)
        for col, key in zip(cols, _ORDER):
            if key not in sens:
                continue
            res   = sens[key]
            color = _COLORS[key]
            bias_label = _BIAS_LABELS.get(res.overall_market_bias, res.overall_market_bias)
            bias_color = _BIAS_COLORS.get(res.overall_market_bias, "blue")

            with col:
                st.markdown(
                    f'<div style="border-top:4px solid {color};background:#f8f9fa;'
                    f'border-radius:8px;padding:12px 10px;margin-bottom:8px;">'
                    f'<div style="color:{color};font-weight:800;font-size:1rem">{_LABELS[key]}</div>'
                    f'<div style="font-size:0.8rem;color:#555;margin-top:2px">{bias_label}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.markdown("**✅ Beneficiados:**")
                for s in res.benefited_sectors[:3]:
                    c = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(s.confidence, "")
                    st.markdown(f"- {s.sector} {c}")
                st.markdown("**❌ Prejudicados:**")
                for s in res.harmed_sectors[:3]:
                    c = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(s.confidence, "")
                    st.markdown(f"- {s.sector} {c}")
                st.markdown("**Tickers:**")
                for t in res.positive_tickers:
                    st.markdown(f"📈 `{t.ticker}`")
                for t in res.negative_tickers:
                    st.markdown(f"📉 `{t.ticker}`")

        # --- Tabela de robustez setorial ---
        st.markdown('<p class="section-header">Robustez Setorial</p>', unsafe_allow_html=True)
        st.caption("Quais setores mantêm a mesma direção independentemente do cenário?")

        sector_dirs: dict[str, dict[str, str]] = {}
        for key in _ORDER:
            if key not in sens:
                continue
            for s in sens[key].benefited_sectors:
                sector_dirs.setdefault(s.sector, {})[key] = "✅"
            for s in sens[key].harmed_sectors:
                sector_dirs.setdefault(s.sector, {})[key] = "❌"

        table_rows = []
        for sector, dirs in sorted(sector_dirs.items()):
            pess = dirs.get("pessimistic", "—")
            base = dirs.get("base", "—")
            opt  = dirs.get("optimistic", "—")
            present = [d for d in [pess, base, opt] if d != "—"]
            if len(set(present)) == 1 and len(present) >= 2:
                rob = "🟢 Robusto"
            elif "✅" in present and "❌" in present:
                rob = "🔴 Divergente"
            else:
                rob = "🟡 Condicional"
            table_rows.append(f"| {sector} | {pess} | {base} | {opt} | {rob} |")

        if table_rows:
            header = "| Setor | Pessimista | Base | Otimista | Robustez |\n|-------|-----------|------|---------|---------|"
            st.markdown(header + "\n" + "\n".join(table_rows))

# ===========================================================================
# COMPARAÇÃO DE DOIS CENÁRIOS
# ===========================================================================
st.markdown("---")
st.markdown("## 🔄 Comparar Dois Cenários")
st.caption("Identifique quais setores são consenso entre dois cenários distintos e quais divergem.")

_ca_col, _cb_col = st.columns(2)
with _ca_col:
    _scen_a = st.text_area(
        "Cenário A:",
        height=100,
        placeholder="Ex: Selic cai para 10%, câmbio estável em 5,20, crescimento do PIB em 3%...",
        key="comp_scen_a",
    )
with _cb_col:
    _scen_b = st.text_area(
        "Cenário B:",
        height=100,
        placeholder="Ex: Selic sobe para 15%, câmbio em 6,50, déficit fiscal acima do esperado...",
        key="comp_scen_b",
    )

if st.button("🔄 Comparar Cenários", type="primary", use_container_width=True, key="btn_compare"):
    if not _scen_a.strip() or not _scen_b.strip():
        st.error("Preencha os dois cenários.")
    elif not os.getenv("ANTHROPIC_API_KEY"):
        st.error("ANTHROPIC_API_KEY não configurada.")
    else:
        with st.spinner("Analisando Cenário A e Cenário B… (2 chamadas à API)"):
            try:
                st.session_state["_comp_a"] = analyze_scenario(_scen_a.strip(), enable_self_critique=False)
                st.session_state["_comp_b"] = analyze_scenario(_scen_b.strip(), enable_self_critique=False)
            except Exception as e:
                st.error(f"Erro: {e}")

_comp_a = st.session_state["_comp_a"]
_comp_b = st.session_state["_comp_b"]

if _comp_a and _comp_b:
    st.markdown("---")

    # --- Side-by-side overview ---
    _col_a, _col_b = st.columns(2)

    def _render_comp_col(col, res, label):
        bc = _BIAS_COLORS.get(res.overall_market_bias, "blue")
        bl = _BIAS_LABELS.get(res.overall_market_bias, res.overall_market_bias)
        with col:
            st.markdown(f'<p class="section-header">{label}</p>', unsafe_allow_html=True)
            st.markdown(f"Viés: :{bc}[**{bl}**]")
            st.markdown("**✅ Top 5 Beneficiados:**")
            for s in res.benefited_sectors[:5]:
                st.markdown(f"- {s.sector}")
            st.markdown("**❌ Top 5 Prejudicados:**")
            for s in res.harmed_sectors[:5]:
                st.markdown(f"- {s.sector}")
            st.markdown("**📈 Comprar:**")
            for t in res.positive_tickers:
                st.markdown(f"- `{t.ticker}` — {t.company}")
            st.markdown("**📉 Vender:**")
            for t in res.negative_tickers:
                st.markdown(f"- `{t.ticker}` — {t.company}")

    _render_comp_col(_col_a, _comp_a, "Cenário A")
    _render_comp_col(_col_b, _comp_b, "Cenário B")

    # --- Divergence table ---
    st.markdown('<p class="section-header">Divergências Setoriais</p>', unsafe_allow_html=True)

    _pos_a = {s.sector for s in _comp_a.benefited_sectors}
    _neg_a = {s.sector for s in _comp_a.harmed_sectors}
    _pos_b = {s.sector for s in _comp_b.benefited_sectors}
    _neg_b = {s.sector for s in _comp_b.harmed_sectors}
    _all   = _pos_a | _neg_a | _pos_b | _neg_b

    _div_rows, _same_rows = [], []
    for sector in sorted(_all):
        da = "✅" if sector in _pos_a else ("❌" if sector in _neg_a else "—")
        db = "✅" if sector in _pos_b else ("❌" if sector in _neg_b else "—")
        status = "🟢 Consenso" if da == db and da != "—" else ("🔴 Diverge" if da != db and "—" not in (da, db) else "🟡 Parcial")
        row = f"| {sector} | {da} | {db} | {status} |"
        (_same_rows if "Consenso" in status else _div_rows).append(row)

    _header = "| Setor | Cenário A | Cenário B | Status |\n|-------|----------|----------|--------|"
    st.markdown(_header + "\n" + "\n".join(_div_rows + _same_rows))

    # --- Ticker consensus ---
    _tpos_a = {t.ticker for t in _comp_a.positive_tickers}
    _tneg_a = {t.ticker for t in _comp_a.negative_tickers}
    _tpos_b = {t.ticker for t in _comp_b.positive_tickers}
    _tneg_b = {t.ticker for t in _comp_b.negative_tickers}

    if _tpos_a & _tpos_b:
        st.success(f"**Compra em ambos os cenários:** {', '.join(f'`{t}`' for t in sorted(_tpos_a & _tpos_b))}")
    if _tneg_a & _tneg_b:
        st.error(f"**Venda em ambos os cenários:** {', '.join(f'`{t}`' for t in sorted(_tneg_a & _tneg_b))}")
