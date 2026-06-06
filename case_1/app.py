"""
Earnings Call Intelligence Tracker — Streamlit Interface
Run with: streamlit run app.py
"""
from __future__ import annotations

import html as _html
import json
import os
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src.ingestion import load_transcript, split_into_chunks
from src.analyzer import analyze_transcript, compare_with_previous
from src.reporter import generate_report

load_dotenv()

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="BBI | Earnings Intelligence",
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
    /* Toggle e selectbox na sidebar */
    [data-testid="stSidebar"] [data-testid="stToggle"] > div {
        background: rgba(255,255,255,0.15) !important;
        border-radius: 20px;
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
    .stTabs [data-baseweb="tab-list"] button[role="tab"] {
        flex: 1 1 0% !important;
        justify-content: center !important;
    }
    .stTabs [data-baseweb="tab"] {
        color: #666 !important;
        font-weight: 600 !important;
        flex: 1 1 0% !important;
        justify-content: center !important;
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

    /* ── ALERTS ── */
    [data-testid="stAlert"] {
        border-left: 4px solid #CC0000 !important;
    }

    /* ── COMPONENTES FINANCEIROS ── */
    .quote-block {
        border-left: 3px solid #CC0000;
        padding: 10px 16px;
        background: #FFF5F5;
        border-radius: 0 6px 6px 0;
        font-style: italic;
        font-size: 0.9rem;
        color: #2A2A2A;
        margin: 8px 0;
    }
    .flag-high   { border-left-color: #CC0000 !important; background: #FFF0F0 !important; }
    .flag-medium { border-left-color: #E67E22 !important; background: #FFF8F0 !important; }
    .flag-low    { border-left-color: #999999 !important; background: #F7F7F7 !important; }

    .badge {
        display: inline-block; border-radius: 4px;
        padding: 2px 10px; font-size: 0.78rem; font-weight: 600;
        font-family: monospace; margin-left: 6px;
    }
    .badge-red    { background:#FFEBEB; color:#CC0000; }
    .badge-yellow { background:#FEF9E7; color:#B7770D; }
    .badge-orange { background:#FEF0E6; color:#D35400; }
    .badge-green  { background:#EAFAF1; color:#1E8449; }

    /* Badges de direção de guidance */
    .dir-badge {
        display: inline-block; border-radius: 3px;
        padding: 1px 8px; font-size: 0.74rem; font-weight: 700;
        letter-spacing: 0.04em; font-family: monospace;
    }
    .dir-up   { background:#FFF0F0; color:#CC0000; }
    .dir-down { background:#F5F5F5; color:#555555; }
    .dir-same { background:#F0F0F0; color:#999999; }
    .dir-new  { background:#FFF0F0; color:#990000; }
    .dir-rem  { background:#F0F0F0; color:#888888; }

    /* Seção opcional Q/Q */
    .optional-section {
        border: 1px solid #E8D0D0;
        border-left: 3px solid #CC0000;
        border-radius: 0 6px 6px 0;
        padding: 14px 18px 10px 18px;
        background: #FDFAFA;
        margin: 16px 0;
    }
    .optional-label {
        font-size: 0.65rem; font-weight: 800; text-transform: uppercase;
        letter-spacing: 0.14em; color: #CC0000; margin-bottom: 2px;
    }
    .optional-title {
        font-size: 0.95rem; font-weight: 700; color: #1A1A1A; margin-bottom: 4px;
    }
    .optional-desc {
        font-size: 0.8rem; color: #666666;
    }
    .loaded-badge {
        background: #F8F2F2; border: 1px solid #E8D0D0;
        border-radius: 4px; padding: 8px 12px;
        font-size: 0.82rem; color: #1A1A1A;
    }

    /* Bloco de excerpt com fundo diferenciado (Tom — trechos de suporte) */
    .excerpt-section {
        background: #F8F2F2;
        border-radius: 6px;
        padding: 16px 18px;
        margin-top: 16px;
    }
    .excerpt-section-label {
        font-size: 0.68rem; font-weight: 800; text-transform: uppercase;
        letter-spacing: 0.12em; color: #CC0000; margin-bottom: 12px;
    }
    .excerpt-item {
        border-left: 3px solid #CC0000;
        padding: 8px 14px; background: #FFFFFF;
        border-radius: 0 4px 4px 0; margin-bottom: 10px;
        font-style: italic; font-size: 0.88rem; color: #2A2A2A;
    }
    .excerpt-speaker {
        font-style: normal; font-size: 0.78rem;
        color: #888888; font-weight: 600; margin-top: 4px;
    }
    .excerpt-interp {
        font-style: normal; font-size: 0.8rem;
        color: #666666; margin-top: 6px; padding-left: 14px;
    }

    /* Severity tags (sem emojis) */
    .sev-tag {
        display: inline-block; border-radius: 3px;
        padding: 1px 8px; font-size: 0.72rem; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.06em;
    }
    .sev-high   { background:#FFEBEB; color:#CC0000; }
    .sev-medium { background:#FEF0E6; color:#D35400; }
    .sev-low    { background:#F5F5F5; color:#888888; }

    /* Impact tags (Surprise Score) */
    .impact-pos { background:#F0FFF4; color:#1E7A3C; }
    .impact-neg { background:#FFEBEB; color:#CC0000; }
    .impact-neu { background:#F5F5F5; color:#666666; }
    .impact-mix { background:#FEF9E7; color:#B7770D; }

    .score-ring {
        font-size: 2.4rem; font-weight: 900;
        text-align: center; line-height: 1;
        color: #CC0000;
    }
    .section-header {
        font-size: 1.05rem; font-weight: 800;
        border-bottom: 2px solid #CC0000;
        padding-bottom: 6px; margin-bottom: 14px;
        color: #1A1A1A;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .sentiment-pill {
        display: inline-block; padding: 4px 14px;
        border-radius: 20px; font-weight: 700;
        font-size: 0.85rem; letter-spacing: 0.05em;
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
# Constants
# ---------------------------------------------------------------------------
_SENTIMENT_COLOR = {
    "bullish":   ("#1A6B3C", "#EBF7F0"),
    "cautious":  ("#B7770D", "#FEF9E7"),
    "neutral":   ("#2471A3", "#EAF4FB"),
    "defensive": ("#7D3C98", "#F5EEF8"),
    "bearish":   ("#CC0000", "#FFF0F0"),
}
_SENTIMENT_LABEL = {
    "bullish": "Otimista", "cautious": "Cauteloso",
    "neutral": "Neutro", "defensive": "Defensivo", "bearish": "Pessimista",
}
_QUALITY_COLOR = {
    "excellent": "badge-green", "good": "badge-green",
    "evasive": "badge-yellow", "incomplete": "badge-orange",
    "deflected": "badge-red",
}
_QUALITY_LABEL = {
    "excellent": "Excelente", "good": "Adequada",
    "evasive": "Evasiva", "incomplete": "Incompleta", "deflected": "Deflexão",
}
_FLAG_PT = {
    "hesitation": "Hesitação", "topic_change": "Mudança de assunto",
    "evasion": "Evasão", "defensive_language": "Linguagem defensiva",
    "vague_answer": "Resposta vaga", "deflected": "Deflexão",
}
_SEV_CLASS = {"high": "flag-high", "medium": "flag-medium", "low": "flag-low"}
_SEV_TAG   = {"high": "sev-high", "medium": "sev-medium", "low": "sev-low"}
_SEV_LABEL = {"high": "Alta", "medium": "Média", "low": "Baixa"}
_IMPACT_TAG   = {"positive": "impact-pos", "negative": "impact-neg",
                 "neutral": "impact-neu", "mixed": "impact-mix"}
_IMPACT_LABEL = {"positive": "Positivo", "negative": "Negativo",
                 "neutral": "Neutro", "mixed": "Misto"}
_DIR_TAG   = {"increase": "dir-up", "new_guidance": "dir-new",
              "decrease": "dir-down", "removed": "dir-rem", "maintained": "dir-same"}
_DIR_LABEL = {"increase": "Aumento", "decrease": "Redução", "maintained": "Mantido",
              "new_guidance": "Novo", "removed": "Removido"}


def _safe_text(text: str) -> str:
    """Strip zero-width unicode chars that cause character-by-character line-break rendering."""
    _bad = {'​', '‌', '‍', '‎', '‏', '﻿', '⁠', '­'}
    return ''.join(c for c in text if c not in _bad)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
# "transcript_text" é a única fonte de verdade. O key da text_area aponta
# direto para ela — sem variável intermediária, sem dessincronização.
if "transcript_text" not in st.session_state:
    st.session_state.transcript_text = ""
if "previous_analysis" not in st.session_state:
    st.session_state.previous_analysis = None

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
    st.markdown("## Configurações")
    show_json = st.toggle("Mostrar JSON bruto", value=False)
    enable_temporal = st.toggle("Comparação Temporal", value=False,
        help="Ativa a seção de upload de análise anterior e gera o diff Q/Q via LLM (Pass 3).")

    st.markdown("---")
    st.markdown("### Transcrição de exemplo")
    st.caption("Análise principal:")
    if st.button("Carregar Petrobras 4T24", use_container_width=True):
        example_path = Path("transcripts/petrobras_4t24.txt")
        if example_path.exists():
            st.session_state.transcript_text = example_path.read_text(encoding="utf-8")
        st.rerun()

    if enable_temporal:
        st.markdown("&nbsp;")
        st.caption("Análise anterior (para comparação Q/Q):")
        if st.button("Carregar Petrobras 3T24 (anterior)", use_container_width=True):
            fixture_path = Path("transcripts/petrobras_3t24_analysis.json")
            if fixture_path.exists():
                st.session_state.previous_analysis = json.loads(
                    fixture_path.read_text(encoding="utf-8")
                )
            st.rerun()

    st.markdown("---")
    st.markdown("### Como usar")
    st.caption("1. Cole a transcrição ou faça upload do .txt")
    st.caption("2. Clique em **Analisar**")
    st.caption("3. Explore os resultados nas seções abaixo")
    st.caption("4. Baixe o JSON ou o relatório em MD")


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown("""
<div style="background:linear-gradient(135deg,#CC0000 0%,#8B0000 100%);
            border-radius:8px;padding:24px 32px;margin-bottom:24px;">
    <div style="color:rgba(255,255,255,0.7);font-size:0.7rem;text-transform:uppercase;
                letter-spacing:0.2em;font-weight:700;">BRADESCO BBI — EQUITY STRATEGY</div>
    <div style="color:#FFFFFF;font-size:1.7rem;font-weight:900;margin-top:6px;
                letter-spacing:-0.01em;line-height:1.2;">
        Earnings Call Intelligence
    </div>
    <div style="color:rgba(255,255,255,0.8);font-size:0.88rem;margin-top:6px;
                font-weight:400;">
        Extração automatizada de sinal de transcrições de earnings calls
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------
col_input, col_cfg = st.columns([3, 1])

with col_input:
    # Upload de arquivo
    uploaded = st.file_uploader("Faça upload de um arquivo .txt", type=["txt"])
    if uploaded:
        st.session_state.transcript_text = uploaded.read().decode("utf-8")
        st.rerun()

    # text_area com key="transcript_text" — o Streamlit lê e escreve
    # diretamente em st.session_state.transcript_text, sem intermediário.
    st.text_area(
        "Ou cole a transcrição aqui:",
        height=220,
        placeholder="Petrobras (PETR4) — Earnings Call 4T24\n\nCEO: Good morning. Our Q4 results...",
        help="Aceita transcrições em inglês ou português.",
        key="transcript_text",
    )

with col_cfg:
    st.markdown("&nbsp;")
    content = st.session_state.transcript_text or ""
    st.metric("Caracteres", f"{len(content):,}")
    st.metric("Palavras", f"{len(content.split()):,}")
    if len(content) > 90_000:
        st.warning("Transcrição longa — será analisado o primeiro chunk.")
    if content:
        st.success("Pronto para analisar")

# ---------------------------------------------------------------------------
# Comparação Temporal Q/Q — seção opcional (aparece só se o toggle estiver ligado)
# ---------------------------------------------------------------------------
if enable_temporal:
    st.markdown("""
    <div class="optional-section">
        <div class="optional-label">Opcional · Comparação Temporal</div>
        <div class="optional-title">Análise anterior (.json)</div>
        <div class="optional-desc">
            Carregue o JSON de uma análise anterior para gerar automaticamente
            um diff entre trimestres: evolução de tom, guidance e red flags.
            Ou use o botão na barra lateral para carregar o exemplo da Petrobras 3T24.
        </div>
    </div>
    """, unsafe_allow_html=True)

    qq_col1, qq_col2 = st.columns([2, 1])

    with qq_col1:
        prev_file = st.file_uploader(
            "Análise anterior (.json)",
            type=["json"],
            key="prev_analysis_file",
            help="Arquivo JSON salvo de uma análise anterior desta mesma empresa.",
        )
        if prev_file is not None:
            try:
                prev_data = json.loads(prev_file.read().decode("utf-8"))
                st.session_state.previous_analysis = prev_data
            except Exception:
                st.error("Arquivo JSON inválido ou corrompido.")

    with qq_col2:
        if st.session_state.previous_analysis:
            q_loaded   = st.session_state.previous_analysis.get("quarter", "—")
            tkr_loaded = st.session_state.previous_analysis.get("ticker", "—")
            st.markdown(
                f'<div class="loaded-badge">'
                f'<div style="font-size:0.68rem;color:#CC0000;font-weight:700;'
                f'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px">Carregado</div>'
                f'<div style="font-weight:700">{tkr_loaded} — {q_loaded}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="padding-top:28px;font-size:0.8rem;color:#AAAAAA">'
                'Nenhuma análise anterior carregada</div>',
                unsafe_allow_html=True,
            )

run = st.button("Analisar Transcrição", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
if run:
    transcript_input = st.session_state.transcript_text

    if not transcript_input or not transcript_input.strip():
        st.error("Cole ou faça upload de uma transcrição antes de analisar.")
        st.stop()

    if not os.getenv("ANTHROPIC_API_KEY"):
        st.error("ANTHROPIC_API_KEY não configurada. Crie um arquivo .env com a chave.")
        st.stop()

    # Chunking se necessário
    chunks = split_into_chunks(transcript_input.strip())
    transcript_to_analyze = chunks[0]
    if len(chunks) > 1:
        st.info(f"Transcrição longa dividida em {len(chunks)} chunks — analisando o primeiro ({len(chunks[0]):,} chars).")

    with st.spinner("Analisando transcrição — Pass 1: extração... Pass 2: self-critique..."):
        try:
            analysis = analyze_transcript(transcript_to_analyze, enable_self_critique=True)
        except Exception as e:
            st.error(f"Erro na análise: {e}")
            st.stop()

    # --- Extensão: Comparação Temporal Q/Q ---
    if enable_temporal and st.session_state.previous_analysis is not None:
        with st.spinner("Gerando comparação temporal (LLM Pass 3)..."):
            try:
                analysis.temporal_comparison = compare_with_previous(
                    analysis, st.session_state.previous_analysis
                )
            except Exception as e:
                st.warning(f"Comparação temporal não gerada: {e}")

    # Salvar outputs (após extensões para incluir todos os dados no JSON)
    out_dir = Path("outputs")
    out_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ticker_slug = (analysis.ticker or "unknown").replace(".", "_")
    json_path = out_dir / f"{ticker_slug}_{ts}.json"
    md_path   = out_dir / f"{ticker_slug}_{ts}.md"
    json_path.write_text(analysis.model_dump_json(indent=2), encoding="utf-8")
    md_path.write_text(generate_report(analysis), encoding="utf-8")
    st.success(f"Outputs salvos em `outputs/{ticker_slug}_{ts}.[json|md]`")

    st.markdown("---")

    # -----------------------------------------------------------------------
    # Resultados
    # -----------------------------------------------------------------------

    # --- Cabeçalho da empresa ---
    tone      = analysis.management_tone
    sentiment = tone.overall_sentiment
    color_fg, color_bg = _SENTIMENT_COLOR.get(sentiment, ("#333333", "#EEEEEE"))
    sent_label = _SENTIMENT_LABEL.get(sentiment, sentiment.upper())

    h1, h2 = st.columns([3, 1])
    with h1:
        st.markdown(f"### {analysis.company}")
        st.caption(f"{analysis.ticker}  ·  {analysis.quarter}  ·  {analysis.call_date}")
    with h2:
        st.markdown(
            f'<div style="background:{color_bg};border-left:4px solid {color_fg};'
            f'border-radius:4px;padding:10px 14px;margin-top:8px;">'
            f'<div style="color:{color_fg};font-weight:800;font-size:1rem;'
            f'text-transform:uppercase;letter-spacing:0.06em">{sent_label}</div>'
            f'<div style="color:{color_fg};font-size:0.78rem;opacity:0.75;margin-top:2px">'
            f'Confiança {tone.confidence_score}/10</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # -----------------------------------------------------------------------
    # Barra de resumo compacta — não repete o conteúdo das abas
    # -----------------------------------------------------------------------
    g_items = analysis.guidance_changes.items
    flags   = analysis.red_flags
    n_high  = sum(1 for f in flags if f.severity == "high")
    n_med   = sum(1 for f in flags if f.severity == "medium")
    ss      = analysis.surprise_score

    _q_rank = {"excellent": 0, "good": 1, "incomplete": 2, "evasive": 3, "deflected": 4}
    qs      = analysis.top_analyst_questions
    worst_q = max(qs, key=lambda q: _q_rank.get(q.response_quality, 0))

    st.markdown("---")

    # --- Tabs principais ---
    tab_tone, tab_guidance, tab_qa, tab_flags, tab_surprise, tab_critique, tab_temporal, tab_transcript = st.tabs([
        "Tom", "Guidance", "Perguntas", "Red Flags", "Surpresas",
        "Self-Critique", "Evolução Temporal", "Transcrição",
    ])

    # ===== TOM =====
    with tab_tone:
        st.markdown('<p class="section-header">Tom do Management</p>', unsafe_allow_html=True)
        st.markdown(_safe_text(tone.justification))

        # Trechos de suporte — bloco visualmente separado
        excerpts_html = '<div class="excerpt-section"><div class="excerpt-section-label">Trechos de suporte</div>'
        for ex in tone.supporting_excerpts:
            excerpts_html += (
                f'<div class="excerpt-item">"{ex.quote}"'
                f'<div class="excerpt-speaker">— {ex.speaker}</div>'
                f'</div>'
                f'<div class="excerpt-interp">{ex.interpretation}</div>'
            )
        excerpts_html += '</div>'
        st.markdown(excerpts_html, unsafe_allow_html=True)

    # ===== GUIDANCE =====
    with tab_guidance:
        st.markdown('<p class="section-header">Mudanças de Guidance</p>', unsafe_allow_html=True)
        st.info(_safe_text(analysis.guidance_changes.summary))

        sig_bg_map = {"high": "#FFF0F0", "medium": "#FFF8F0", "low": "#F8F8F8"}
        sig_color_map = {"high": "#CC0000", "medium": "#D35400", "low": "#888888"}

        for item in analysis.guidance_changes.items:
            sig_bg  = sig_bg_map.get(item.significance, "#F5F5F5")
            sig_col = sig_color_map.get(item.significance, "#999999")
            dir_tag   = _DIR_TAG.get(item.direction, "dir-same")
            dir_label = _DIR_LABEL.get(item.direction, item.direction)
            prev = item.previous if item.previous and item.previous != "NOT_FOUND" else "—"

            st.markdown(
                f'<div style="background:{sig_bg};border-left:3px solid {sig_col};'
                f'border-radius:0 4px 4px 0;padding:10px 14px;margin-bottom:6px;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                f'<span style="font-weight:700;color:#1A1A1A;font-size:0.92rem">{item.metric}</span>'
                f'<span class="dir-badge {dir_tag}">{dir_label}</span>'
                f'</div>'
                f'<div style="font-size:0.82rem;color:#555;margin-top:4px">'
                f'{prev} &rarr; {item.current}'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            with st.expander("Ver trecho na transcrição"):
                st.markdown(
                    f'<div class="quote-block">"{item.excerpt}"</div>',
                    unsafe_allow_html=True,
                )

    # ===== PERGUNTAS =====
    with tab_qa:
        st.markdown('<p class="section-header">Top 3 Perguntas de Analistas</p>', unsafe_allow_html=True)

        for q in sorted(analysis.top_analyst_questions, key=lambda x: x.rank):
            quality_cls   = _QUALITY_COLOR.get(q.response_quality, "badge-green")
            quality_label = _QUALITY_LABEL.get(q.response_quality, q.response_quality)
            badge_html = f'<span class="badge {quality_cls}">{quality_label}</span>'

            # Limpa campos NOT_FOUND/vazios no título do expander
            _name = q.analyst_name if q.analyst_name not in ("NOT_FOUND", "—", "") else "Analista"
            _inst = q.institution  if q.institution  not in ("NOT_FOUND", "—", "") else ""
            expander_title = f"#{q.rank}  ·  {_name}" + (f"  —  {_inst}" if _inst else "")

            with st.expander(expander_title, expanded=(q.rank == 1)):
                st.markdown(
                    f'<div style="margin-bottom:14px">Qualidade da resposta: {badge_html}</div>',
                    unsafe_allow_html=True,
                )

                st.markdown(
                    '<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
                    'letter-spacing:0.1em;color:#CC0000;margin-bottom:4px">Pergunta</p>',
                    unsafe_allow_html=True,
                )
                _qe = q.question_excerpt if q.question_excerpt != "NOT_FOUND" else "(não disponível)"
                st.markdown(f'<div class="quote-block">"{_qe}"</div>', unsafe_allow_html=True)
                if q.question_summary:
                    st.caption(q.question_summary)

                st.markdown(
                    '<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
                    'letter-spacing:0.1em;color:#555555;margin-top:12px;margin-bottom:4px">Resposta do management</p>',
                    unsafe_allow_html=True,
                )
                _re = q.response_excerpt if q.response_excerpt != "NOT_FOUND" else "(não disponível)"
                st.markdown(f'<div class="quote-block">"{_re}"</div>', unsafe_allow_html=True)
                if q.response_summary:
                    st.caption(q.response_summary)

    # ===== RED FLAGS =====
    with tab_flags:
        st.markdown('<p class="section-header">Red Flags Linguísticos</p>', unsafe_allow_html=True)

        if not analysis.red_flags:
            st.info("Nenhum red flag significativo identificado.")
        else:
            priority = {"high": 0, "medium": 1, "low": 2}
            flags_sorted = sorted(analysis.red_flags, key=lambda f: priority.get(f.severity, 3))

            for rf in flags_sorted:
                sev_class = _SEV_CLASS.get(rf.severity, "")
                sev_tag   = _SEV_TAG.get(rf.severity, "sev-low")
                sev_label = _SEV_LABEL.get(rf.severity, rf.severity)
                flag_label = _FLAG_PT.get(rf.flag_type, rf.flag_type)

                st.markdown(
                    f'<div style="margin-bottom:2px">'
                    f'<span style="font-weight:700;color:#1A1A1A">{flag_label}</span>'
                    f'<span class="sev-tag {sev_tag}" style="margin-left:8px">{sev_label}</span>'
                    f'<span style="color:#888;font-size:0.85rem;margin-left:10px">{rf.speaker}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="quote-block {sev_class}">"{rf.excerpt}"</div>',
                    unsafe_allow_html=True,
                )
                st.caption(_safe_text(rf.analysis))
                st.markdown("")

    # ===== SURPRISE SCORE =====
    with tab_surprise:
        st.markdown('<p class="section-header">Surprise Score</p>', unsafe_allow_html=True)

        ss = analysis.surprise_score
        score = ss.score

        # Score visual
        if score >= 8:
            score_color = "#c0392b"
        elif score >= 5:
            score_color = "#e67e22"
        else:
            score_color = "#27ae60"

        sc1, sc2 = st.columns([1, 3])
        with sc1:
            st.markdown(
                f'<div style="background:#f8f9fa;border:2px solid {score_color};'
                f'border-radius:12px;padding:16px;text-align:center;">'
                f'<div class="score-ring" style="color:{score_color}">{score}</div>'
                f'<div style="font-size:0.75rem;color:#888;margin-top:4px">/ 10</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with sc2:
            st.markdown(_safe_text(ss.rationale))

        st.markdown(
            '<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
            'letter-spacing:0.1em;color:#CC0000;margin:16px 0 8px 0">Itens de surpresa</p>',
            unsafe_allow_html=True,
        )
        for item in ss.items:
            impact_tag   = _IMPACT_TAG.get(item.market_impact_assessment, "impact-neu")
            impact_label = _IMPACT_LABEL.get(item.market_impact_assessment, "")
            with st.expander(item.element):
                col_a, col_b = st.columns(2)
                st.markdown(
                    f'<span class="sev-tag {impact_tag}">{impact_label}</span>',
                    unsafe_allow_html=True,
                )
                col_a.markdown(
                    '<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
                    'letter-spacing:0.08em;color:#999">Consenso esperava</p>',
                    unsafe_allow_html=True,
                )
                col_a.markdown(
                    f'<div class="quote-block" style="font-style:normal">'
                    f'{_html.escape(item.expected_consensus)}</div>',
                    unsafe_allow_html=True,
                )
                col_b.markdown(
                    '<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
                    'letter-spacing:0.08em;color:#CC0000">O que foi dito</p>',
                    unsafe_allow_html=True,
                )
                col_b.markdown(
                    f'<div class="quote-block" style="font-style:normal;border-left-color:#CC0000">'
                    f'{_html.escape(item.actual_statement)}</div>',
                    unsafe_allow_html=True,
                )
                st.caption(_safe_text(f"Por que surpreendeu: {item.why_surprising}"))
                st.markdown(
                    f'<div class="quote-block">"{item.excerpt}"</div>',
                    unsafe_allow_html=True,
                )

    # ===== SELF-CRITIQUE =====
    with tab_critique:
        if not analysis.self_critique:
            st.info("Self-critique desligado. Ative no painel lateral e rode novamente.")
        else:
            sc = analysis.self_critique
            st.markdown('<p class="section-header">Revisão de Qualidade da Análise</p>', unsafe_allow_html=True)

            m1, m2 = st.columns(2)
            m1.metric("Qualidade geral", sc.overall_quality.upper())
            m2.metric("Confiabilidade", f"{sc.reliability_score}/10")

            st.markdown(
                '<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
                'letter-spacing:0.1em;color:#CC0000;margin:16px 0 8px 0">Avaliação por seção</p>',
                unsafe_allow_html=True,
            )
            for item in sc.items:
                issue_tag = (
                    '<span class="sev-tag sev-high" style="margin-right:8px">Problema</span>'
                    if item.issue_found else
                    '<span class="sev-tag sev-low" style="margin-right:8px">OK</span>'
                )
                conf_map = {"high": "sev-low", "medium": "sev-medium", "low": "sev-high"}
                conf_tag = conf_map.get(item.confidence_after_review, "sev-low")
                with st.expander(item.section):
                    st.markdown(issue_tag, unsafe_allow_html=True)
                    st.markdown(_safe_text(item.critique))
                    st.markdown(
                        f'Confiança após revisão: <span class="sev-tag {conf_tag}">'
                        f'{item.confidence_after_review}</span>',
                        unsafe_allow_html=True,
                    )

            if sc.caveats:
                st.markdown(
                    '<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
                    'letter-spacing:0.1em;color:#D35400;margin:16px 0 8px 0">Caveats para o analista</p>',
                    unsafe_allow_html=True,
                )
                for caveat in sc.caveats:
                    st.warning(caveat)

    # ===== EVOLUÇÃO Q/Q =====
    with tab_temporal:
        tc = analysis.temporal_comparison
        if not enable_temporal:
            st.info(
                "Ative o toggle **Comparação Temporal** na barra lateral para habilitar esta funcionalidade."
            )
        elif tc is None:
            st.info(
                "Carregue uma análise de trimestre anterior (.json) — ou use o botão "
                "**Carregar Petrobras 3T24 (anterior)** na barra lateral — e clique em Analisar novamente."
            )
        else:
            st.markdown(
                f'<p class="section-header">Evolução: {tc.previous_quarter} → {tc.current_quarter}</p>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div style="background:#EAF4FB;border-left:4px solid #2980B9;'
                f'border-radius:0 6px 6px 0;padding:12px 16px;font-size:0.9rem;'
                f'color:#1A1A1A;line-height:1.6;margin-bottom:8px;">'
                f'{_html.escape(_safe_text(tc.analyst_summary))}</div>',
                unsafe_allow_html=True,
            )

            # Tom
            st.markdown("---")
            _dir_color_qq = {"improved": "#1A6B3C", "deteriorated": "#CC0000", "stable": "#555555"}
            _dir_text_qq  = {"improved": "Melhora", "deteriorated": "Deterioração", "stable": "Estável"}
            dir_col = _dir_color_qq.get(tc.tone_evolution.direction, "#555")
            dir_txt = _dir_text_qq.get(tc.tone_evolution.direction, "")
            st.markdown(
                '<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
                'letter-spacing:0.1em;color:#CC0000;margin-bottom:10px">Tom do Management</p>',
                unsafe_allow_html=True,
            )
            c1, c2, c3 = st.columns([3, 1, 3])
            with c1:
                st.metric(tc.previous_quarter, tc.tone_evolution.previous_sentiment)
            with c2:
                st.markdown(
                    f'<div style="text-align:center;margin-top:22px;">'
                    f'<span style="display:inline-block;padding:4px 10px;border-radius:4px;'
                    f'background:{dir_col}22;color:{dir_col};font-size:0.72rem;font-weight:800;'
                    f'text-transform:uppercase;letter-spacing:0.06em">{dir_txt}</span></div>',
                    unsafe_allow_html=True,
                )
            with c3:
                st.metric(tc.current_quarter, tc.tone_evolution.current_sentiment)
            for change in tc.tone_evolution.key_changes:
                st.caption(_safe_text(change))

            # Surprise score delta
            st.markdown("---")
            delta = tc.surprise_score_delta
            delta_color = "#CC0000" if delta > 0 else "#1A6B3C" if delta < 0 else "#555555"
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:4px">'
                f'<span style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
                f'letter-spacing:0.1em;color:#999">Variação Surprise Score</span>'
                f'<span style="font-size:1.1rem;font-weight:900;color:{delta_color}">'
                f'{"+"+str(delta) if delta > 0 else str(delta)}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Guidance
            st.markdown("---")
            st.markdown(
                '<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
                'letter-spacing:0.1em;color:#CC0000;margin-bottom:10px">Guidance</p>',
                unsafe_allow_html=True,
            )
            ge = tc.guidance_evolution
            _guid_sections = [
                (ge.upgraded,      "dir-up",   "Aumento"),
                (ge.downgraded,    "dir-down",  "Redução"),
                (ge.new_items,     "dir-new",   "Novo"),
                (ge.reiterated,    "dir-same",  "Mantido"),
                (ge.removed_items, "dir-rem",   "Removido"),
            ]
            for items, tag, label in _guid_sections:
                if items:
                    st.markdown(
                        f'<span class="dir-badge {tag}" style="margin-bottom:6px;display:inline-block">{label}</span>',
                        unsafe_allow_html=True,
                    )
                    for item in items:
                        st.markdown(
                            f'<div style="padding:3px 0 3px 16px;font-size:0.88rem;color:#333">'
                            f'{_html.escape(_safe_text(item))}</div>',
                            unsafe_allow_html=True,
                        )
            if not any(g[0] for g in _guid_sections):
                st.caption("Sem mudanças de guidance mapeadas.")

            # Red Flags
            st.markdown("---")
            st.markdown(
                '<p style="font-size:0.72rem;font-weight:700;text-transform:uppercase;'
                'letter-spacing:0.1em;color:#CC0000;margin-bottom:10px">Red Flags</p>',
                unsafe_allow_html=True,
            )
            rf = tc.red_flag_evolution
            if rf.new_flags:
                st.markdown('<span class="sev-tag sev-high" style="margin-bottom:6px;display:inline-block">Novos</span>', unsafe_allow_html=True)
                for f in rf.new_flags:
                    st.markdown(
                        f'<div style="padding:3px 0 3px 16px;font-size:0.88rem;color:#333">'
                        f'{_html.escape(_safe_text(f))}</div>', unsafe_allow_html=True)
            if rf.persistent:
                st.markdown('<span class="sev-tag sev-medium" style="margin-bottom:6px;display:inline-block">Persistentes</span>', unsafe_allow_html=True)
                for f in rf.persistent:
                    st.markdown(
                        f'<div style="padding:3px 0 3px 16px;font-size:0.88rem;color:#333">'
                        f'{_html.escape(_safe_text(f))}</div>', unsafe_allow_html=True)
            if rf.resolved:
                st.markdown('<span class="sev-tag sev-low" style="margin-bottom:6px;display:inline-block">Resolvidos</span>', unsafe_allow_html=True)
                for f in rf.resolved:
                    st.markdown(
                        f'<div style="padding:3px 0 3px 16px;font-size:0.88rem;color:#333">'
                        f'{_html.escape(_safe_text(f))}</div>', unsafe_allow_html=True)
            if not rf.new_flags and not rf.persistent and not rf.resolved:
                st.info("Nenhuma red flag comparável mapeada.")

    # ===== TRANSCRIÇÃO =====
    with tab_transcript:
        st.markdown('<p class="section-header">Transcrição Analisada</p>', unsafe_allow_html=True)
        if len(chunks) > 1:
            st.info(f"Exibindo apenas o primeiro chunk analisado ({len(transcript_to_analyze):,} de {len(transcript_input):,} chars totais).")
        st.text_area(
            "Texto completo:",
            value=transcript_to_analyze,
            height=500,
            disabled=True,
            label_visibility="collapsed",
        )

    # -----------------------------------------------------------------------
    # Downloads
    # -----------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### Downloads")
    dl1, dl2 = st.columns(2)

    report_md = generate_report(analysis)
    dl1.download_button(
        "Relatório Executivo (.md)",
        data=report_md,
        file_name=f"{analysis.ticker}_{datetime.now().strftime('%Y%m%d')}.md",
        mime="text/markdown",
        use_container_width=True,
    )
    dl2.download_button(
        "Análise Completa (.json)",
        data=analysis.model_dump_json(indent=2),
        file_name=f"{analysis.ticker}_{datetime.now().strftime('%Y%m%d')}.json",
        mime="application/json",
        use_container_width=True,
    )

    if show_json:
        with st.expander("JSON bruto completo"):
            st.json(json.loads(analysis.model_dump_json()))
