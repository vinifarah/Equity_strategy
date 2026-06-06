# Case 1 — Earnings Call Intelligence Tracker

Ferramenta em Python + Streamlit que ingere transcrições de earnings calls de empresas do Ibovespa e extrai análise estruturada via IA: tom do management, mudanças de guidance, red flags linguísticos, surprise score e comparação entre trimestres.

> **Nota sobre uso de IA:** Este projeto foi desenvolvido com auxílio do Claude (Anthropic) como ferramenta de pair programming — geração de código, iteração de prompts e estruturação da interface. Todas as decisões arquiteturais, escolhas de prompt engineering e raciocínio sobre o domínio financeiro foram feitas e validadas pelo candidato. Na entrevista técnica, posso defender cada linha.

---

## Como Usar a Interface — Guia Rápido

### Antes de começar

```bash
cd case_1
pip install -r requirements.txt
cp .env.example .env
# Abrir o arquivo .env e inserir a chave ANTHROPIC_API_KEY
```

### Abrindo a interface

```bash
streamlit run app.py
```

O navegador abrirá automaticamente em `http://localhost:8501`.

---

### Passo a passo

**1. Carregue uma transcrição**

- **Exemplo pronto:** clique em **"Carregar Petrobras 4T24"** na barra lateral. A transcrição da Petrobras é carregada automaticamente.
- **Sua empresa:** arraste um `.txt` ou cole o texto no campo.

**2. (Opcional) Compare com o trimestre anterior**

Ative o toggle **"Comparação Temporal"** na barra lateral. Depois:
- Clique em **"Carregar Petrobras 3T24 (anterior)"** para usar o exemplo incluso, ou
- Arraste um `.json` de uma análise anterior salvo em `outputs/`.

**3. Clique em "Analisar Transcrição"**

O modelo processa em até 60 segundos (+ ~20s se Comparação Temporal estiver ativa).

**4. Explore os resultados pelas abas**

| Aba | O que mostra |
|-----|-------------|
| **Tom** | Sentimento geral do management com trechos verbatim da transcrição |
| **Guidance** | O que mudou: metas aumentadas, reduzidas, novas ou removidas |
| **Perguntas** | Top 3 perguntas dos analistas e qualidade das respostas (adequada, evasiva, deflexão…) |
| **Red Flags** | Trechos que sinalizam hesitação, evasão ou mudança de assunto |
| **Surpresas** | O que provavelmente não estava no consenso pré-call |
| **Self-Critique** | O modelo avalia a confiabilidade da própria análise |
| **Evolução Temporal** | Diff Q/Q: tom, guidance e red flags entre dois trimestres |

**5. Baixe os resultados**

- **Relatório Executivo (.md)** — ≤400 palavras, pronto para enviar
- **Análise Completa (.json)** — estrutura completa; reutilizável como "análise anterior"

Outputs também salvos automaticamente em `outputs/` com timestamp.

---

## Arquitetura da Solução

```
case_1/
├── main.py                    # Entrypoint de linha de comando
├── app.py                     # Interface Streamlit
├── transcripts/
│   ├── petrobras_4t24.txt                # Transcrição de exemplo — Petrobras 4T24
│   └── petrobras_3t24_analysis.json      # Fixture análise 3T24 (para testar Q/Q)
├── outputs/                   # JSONs e relatórios gerados (criado em runtime)
└── src/
    ├── models.py              # Schemas Pydantic v2
    ├── ingestion.py           # Carregamento e limpeza da transcrição
    ├── analyzer.py            # Pipeline LLM: 3 passes
    └── reporter.py            # Relatório executivo em markdown
```

**Fluxo de dados:**

```
transcript.txt
    → ingestion.py  (carrega, limpa, divide em chunks se necessário)
    → Pass 1 — extração estruturada em JSON (LLM)
    → Pass 2 — self-critique: revisa quotes, calibração e red flags (LLM)
    → Pass 3 — comparação Q/Q com trimestre anterior [opcional]
    → reporter.py — relatório executivo ≤400 palavras
    → outputs/{ticker}_{timestamp}.json + .md
```

**Por que passes separados?** Um único prompt que extrai e auto-avalia ao mesmo tempo produz análise de menor qualidade — o modelo prioriza consistência interna em vez de verificação real. Separar os passes permite que o Pass 2 receba a transcrição original e o JSON gerado para verificação cruzada genuína.

---

## Prompts de Desenvolvimento (exemplos enviados ao Claude)

Durante a construção, os prompts abaixo (ou variantes próximas) foram usados para iterar sobre a solução:

> **Arquitetura inicial:**
> "Quero construir uma ferramenta em Python que lê transcrições de earnings calls e extrai análise estruturada. Preciso de: tom do management, mudanças de guidance, red flags linguísticos e surprise score. O output deve ser JSON validado por Pydantic. Como estruturarias os schemas e o pipeline LLM?"

> **Anti-alucinação:**
> "O modelo está inventando citações que não existem na transcrição. Quero que cada campo de excerpt seja obrigatoriamente verbatim. Se não encontrar evidência, deve retornar 'NOT_FOUND' em vez de inventar. Como escrevo essa regra no prompt de forma que o modelo a respeite consistentemente?"

> **Self-critique:**
> "Quero um segundo pass de LLM que receba o JSON gerado pelo primeiro pass e a transcrição original, e verifique se as citações realmente aparecem no texto. O modelo deve marcar quais citações estão corretas e quais foram fabricadas. Como estruturo esse prompt de verificação cruzada?"

> **Red flags:**
> "O modelo está flagando linguagem corporativa normal como red flag (ex: 'going forward', 'as we've discussed'). Quero que ele só marque evasão genuína — quando o management desvia de uma pergunta direta, muda de assunto ou usa linguagem vaga onde uma resposta específica seria possível. Como calibro esse critério no prompt?"

> **Comparação temporal:**
> "Quero um terceiro pass que recebe a análise do trimestre atual e uma análise anterior em JSON, e identifica mudanças relevantes: shifts de tom, guidance que foi revisado, red flags que persistem ou surgiram. Foca em mudanças genuínas, não ruído. Como estruturo esse prompt de diff Q/Q?"

---

## Decisões de Prompt Engineering

### 1. Anti-alucinação via instrução verbatim explícita

Em análise financeira, citar uma frase que o CEO não disse é um erro com consequência real. A regra mais importante do prompt é:

```
CRITICAL RULES you must always follow:
1. Every "excerpt", "quote", or "question_excerpt"/"response_excerpt" field MUST contain
   text that appears VERBATIM in the transcript. Never paraphrase, summarize, or invent quotes.
2. If evidence for a field is not present in the transcript, write "NOT_FOUND" — never fabricate.
3. Red flags require high standards: only flag genuine linguistic evasion signals,
   not normal corporate hedging language.
```

`NOT_FOUND` é um sinal de qualidade, não de falha — cria uma saída auditável.

### 2. Schema JSON completo no prompt

O schema inteiro está inline no prompt com comentários explicativos em cada campo. Isso elimina o passo de parsing e âncora o modelo na estrutura esperada:

```
"red_flags": [
  {
    "flag_type": "<hesitation|topic_change|evasion|defensive_language|vague_answer|deflected>",
    "speaker": "<name or role>",
    "excerpt": "<VERBATIM quote showing the red flag>",
    "analysis": "<what a confident management would have said instead, and why this is a signal>",
    "severity": "<high|medium|low>"
  }
]
```

### 3. System prompt com persona financeira

```
You are a senior sell-side equity research analyst at a top-tier investment bank
with 20 years of experience covering Brazilian publicly traded companies. Your specialty
is extracting investment-relevant signals from earnings call transcripts — tone, guidance
shifts, red flags, and surprises that the consensus may have missed.
```

O papel é definido antes de qualquer instrução de tarefa. Isso muda o registro e o nível de especificidade das respostas.

### 4. Chain-of-Thought implícito via instrução de passos

O prompt de extração instrui o modelo a "think carefully before writing each field" antes de cada seção. O de comparação temporal usa instrução explícita: "Focus on genuine narrative shifts, not noise."

### 5. Self-critique com acesso à fonte original

O Pass 2 recebe tanto o JSON gerado quanto a transcrição original. O prompt instrui:

```
"Be honest. Flag any quote that does not appear verbatim in the transcript.
Flag any red flag that may be overblown. Flag any surprise score that seems miscalibrated."
```

Isso cria verificação cruzada real — não só coerência interna.

---

## Extensões Implementadas e Escolha de Priorização

Das extensões valorizadas pelo brief, o Case 1 foi escolhido como **case de aprofundamento principal**. As extensões foram selecionadas por valor prático para um analista de Equity Strategy:

| Extensão | Status | Justificativa da escolha |
|----------|--------|--------------------------|
| **Self-critique loop** | ✅ Implementado | Reduz alucinações diretamente — a extensão de maior impacto em confiabilidade |
| **Comparação temporal** | ✅ Implementado | Analistas acompanham empresas trimestre a trimestre; diff Q/Q automático é de uso imediato |
| **Avaliação de consistência** | ✅ Implementado | Parte do self-critique — verifica se citações aparecem literalmente na transcrição |
| **Interface Streamlit** | ✅ Implementado | Torna a ferramenta utilizável por analistas sem execução via terminal |
| **Citation tracking** | Parcial | Quotes verbatim são extraídas e exibidas, mas não há link de volta ao parágrafo de origem |
| **Reação de mercado** | Removido | Implementado via yfinance; removido porque a API é bloqueada em redes corporativas |
| **Análise comparativa setorial** | Não implementado | Requereria pipeline multi-transcrição (várias empresas); não prioritário sem dados reais de consenso |
| **Comparação multi-modelo** | Não implementado | Tecnicamente simples, mas de valor marginal para avaliação da qualidade da análise |

**Por que Case 1 como aprofundamento:** o risco de erro aqui tem consequência real (citar algo que o CEO não disse é um erro de credibilidade imediato). Isso exigiu mais iteração de prompt e mais extensões de verificação do que o Case 2, onde o modelo tem mais liberdade editorial.

---

## Exemplo de Execução

**Input:** `transcripts/petrobras_4t24.txt`

**Output JSON (trecho representativo):**
```json
{
  "company": "Petróleo Brasileiro S.A. - Petrobras",
  "ticker": "PETR4",
  "quarter": "4T24",
  "management_tone": {
    "overall_sentiment": "cautious",
    "confidence_score": 7,
    "justification": "Management demonstrates operational confidence on production and costs, but adopts notably defensive language when pressed on dividends above the floor and RNEST cost overruns. Multiple pivots to pre-approved talking points when cornered on specific numbers."
  },
  "guidance_changes": {
    "summary": "Capex guidance revised upward to R$104B for 2025, absorbing RNEST overruns without explicit acknowledgment. Production maintained at 2.1 mboe/d. No forward guidance on extraordinary dividends despite strong FCF.",
    "items": [
      {
        "metric": "Capex 2025",
        "previous": "R$89B (2024 guidance)",
        "current": "R$104B",
        "direction": "increase",
        "significance": "high",
        "excerpt": "Our 2025 capital expenditure plan of R$104 billion reflects our updated portfolio priorities and fully contemplates all currently identified projects."
      }
    ]
  },
  "red_flags": [
    {
      "flag_type": "evasion",
      "speaker": "Magda Chambriard (CEO)",
      "excerpt": "What we can confirm is that the overall 2025 capex guidance of R$104 billion fully contemplates our current expectation for RNEST expenditures.",
      "analysis": "When directly asked whether RNEST is within contingency or represents a cost overrun, the CEO pivots to total capex guidance rather than answering the binary question. A confident answer would be: 'RNEST requires R$X billion above original budget, absorbed within the R$104B envelope.'",
      "severity": "high"
    }
  ],
  "surprise_score": {
    "score": 7,
    "rationale": "Higher-than-expected capex revision (+R$15B vs prior guidance) and implicit confirmation of RNEST overruns were not fully priced in. Dividend floor maintained but no extraordinary distribution signaled despite record FCF.",
    "items": [
      {
        "element": "Capex revision para R$104B — R$15B acima do guidance anterior",
        "expected_consensus": "Capex de R$89-92B em linha com plano estratégico anterior",
        "actual_statement": "R$104B para 2025, absorvendo RNEST e novos projetos",
        "market_impact_assessment": "negative"
      }
    ]
  }
}
```

**Relatório executivo gerado (≤400 palavras):** salvo em `outputs/PETR4_*.md` após cada execução.

---

## Log de Tempo Gasto

| Atividade | Tempo (aprox.) |
|-----------|----------------|
| Leitura do brief e planejamento de arquitetura | 1h |
| Modelagem Pydantic e ingestion pipeline | 1h |
| Design e iteração dos prompts de extração | 2h |
| Design do self-critique prompt | 1h |
| Reporter e CLI | 1h |
| Interface Streamlit (tema BBI) | 1.5h |
| Extensão: Comparação Temporal (prompt + UI) | 1.5h |
| Extensão: Reação de Mercado (implementada e depois removida por bloqueio de rede) | 1h |
| Transcrição de exemplo, fixture 3T24 e testes | 1h |
| README | 0.5h |
| **Total** | **~9.5h** |

---

## Por que me Aprofundar no Case 1

Escolhi o **Case 1 como case de aprofundamento principal** por três razões:

**1. O risco de erro é mais alto aqui.** Extrair citações literais de uma transcrição financeira é o problema onde uma falha tem consequência imediata de credibilidade. Um analista que cita uma frase que o CEO não disse perde credibilidade na mesma hora. Isso exigiu mais iteração de prompt (regras anti-alucinação, critério elevado para red flags, `NOT_FOUND` como saída explícita) do que o Case 2, onde o modelo tem mais liberdade para raciocinar qualitativamente.

**2. As extensões de maior valor prático para Equity Strategy estão aqui.** Comparação trimestral é algo que um analista de cobertura usa toda semana — não em uma análise isolada, mas no acompanhamento contínuo de uma empresa. A ferramenta entrega isso com um JSON reutilizável como fixture para calls futuras.

**3. Demonstra pipeline de extração estruturado, não apenas geração de texto.** Com três passes de LLM, 14 modelos de dados Pydantic e saída auditável com `NOT_FOUND`, o Case 1 demonstra engenharia de dados com IA — não apenas "perguntar para o modelo e mostrar a resposta".

O Case 2 também recebeu investimento significativo — tem self-critique, confidence scoring, análise de sensibilidade e comparação de cenários. Mas as decisões de prompt mais difíceis (e os riscos de qualidade mais sérios) estão no Case 1.

---

## Três Limitações Mais Sérias

**1. Transcrições em inglês funcionam melhor**
Os prompts foram otimizados para inglês, que é o idioma padrão das earnings calls de empresas brasileiras para o mercado internacional. Calls integralmente em português produzem análise de qualidade inferior. Uma versão de produção precisaria de prompts bilíngues e testes específicos em português.

**2. O surprise score não usa dados reais de consenso**
O modelo não tem acesso às estimativas formais dos analistas de sell-side (Bloomberg, LSEG). O score é uma avaliação qualitativa baseada no conhecimento geral do modelo sobre a empresa — não uma medida objetiva de desvio vs. consenso. Isso o torna mais subjetivo do que seria aceitável em produção.

**3. O modelo não sabe o que aconteceu no trimestre anterior**
Na primeira análise de uma empresa, o modelo usa conhecimento geral (potencialmente desatualizado) para inferir mudanças de guidance. A extensão de Comparação Temporal resolve isso, mas depende do usuário já ter uma análise anterior em JSON — o que só é possível a partir da segunda análise.

---

## Com Mais 2 Semanas, Faria

1. **Conectar com dados reais de consenso** — substituir o surprise score qualitativo por desvio objetivo vs. estimativas de sell-side (Bloomberg/LSEG). Transformaria o score de "percepção do modelo" em "desvio mensurável".

2. **Citation tracking com highlight na transcrição** — criar link clicável de volta ao parágrafo de origem para cada citação. Hoje as quotes são verbatim mas isoladas do contexto visual.

3. **Pipeline multi-empresa** — comparar várias transcrições do mesmo setor em paralelo e identificar narrativas comuns vs. divergentes na temporada de resultados.

4. **Suporte a PDF** — a maioria das transcrições e press releases vem em PDF. Hoje só `.txt` é aceito.

5. **Histórico pesquisável** — banco SQLite com todas as análises feitas, com busca por tema. Ex: "todos os trimestres em que a Petrobras mencionou RNEST" ou "calls com surprise score > 7".

6. **Reação de mercado via Yahoo Finance** — a extensão foi implementada mas removida porque a API do `yfinance` é bloqueada em redes corporativas e VPNs. Com mais tempo, substituiria por uma integração mais robusta — autenticação via cookie de sessão ou uso da API oficial do Yahoo Finance — para puxar cotação intraday no dia da call e calcular retorno vs. índice nas 24h/48h seguintes.
