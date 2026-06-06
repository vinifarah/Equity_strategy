# Case 2 — Macro Scenario Engine

Ferramenta em Python + Streamlit que recebe um cenário macroeconômico em linguagem natural e retorna recomendações setoriais e de tickers para a bolsa brasileira, com confidence scoring, self-critique, análise de sensibilidade e comparação de cenários.

> **Nota sobre uso de IA:** Este projeto foi desenvolvido com auxílio do Claude (Anthropic) como ferramenta de pair programming — geração de código, iteração de prompts e estruturação da interface. Todas as decisões arquiteturais, escolhas de prompt engineering e raciocínio sobre o domínio de macro/equity foram feitas e validadas pelo candidato. Na entrevista técnica, posso defender cada linha.

---

## Como Usar a Interface

### Instalação

```bash
cd case_2
pip install -r requirements.txt
cp .env.example .env
# Editar .env e inserir ANTHROPIC_API_KEY
```

### Interface Streamlit

```bash
streamlit run app.py
```

Acesse `http://localhost:8501`. A interface tem três seções:

**1. Análise de cenário único**
- Selecione um dos 4 cenários de exemplo no menu lateral, ou escreva o seu no campo de texto
- Clique em **"Analisar Cenário"**
- Resultados aparecem em: variáveis macro identificadas → setores beneficiados/prejudicados → tickers → riscos da tese → self-critique
- Download do relatório (.md) e análise completa (.json) disponíveis

**2. Análise de sensibilidade** (aparece após rodar um cenário)
- Clique em **"Rodar Análise de Sensibilidade"**
- O modelo gera automaticamente 3 variantes (pessimista / base / otimista) e compara como as recomendações divergem
- Tabela de robustez setorial mostra quais setores mantêm direção nos 3 cenários

**3. Comparação de dois cenários**
- Escreva dois cenários nos campos lado a lado
- Clique em **"Comparar Cenários"** para ver quais setores e tickers divergem entre eles

### CLI

```bash
python main.py "Selic cai para 10%, câmbio em 5,50, minério de ferro em alta 15%"
python main.py --file meu_cenario.txt
```

---

## Arquitetura da Solução

```
case_2/
├── main.py                    # CLI entrypoint
├── app.py                     # Interface Streamlit
├── outputs/                   # JSONs e relatórios gerados (criado em runtime)
└── src/
    ├── models.py              # Pydantic v2: schemas de output
    ├── analyzer.py            # Pipeline LLM: análise macro + self-critique + sensibilidade
    └── reporter.py            # Gerador de relatório markdown executivo
```

**Fluxo de dados:**

```
Cenário em linguagem natural
    → Pass 1: LLM — CoT 5 passos: variáveis → canais → setores → tickers → riscos
    → Pass 2: LLM self-critique — verifica consistência interna e conflitos lógicos
    → Pydantic validation (MacroScenarioAnalysis)
    → reporter.py — markdown ≤500 palavras
    → outputs/scenario_{timestamp}.json + .md

[Análise de Sensibilidade — opcional]
    → LLM gera 3 variantes (pessimista/base/otimista)
    → Pass 1 em cada variante (sem self-critique para reduzir custo: 4 chamadas no total)
    → Comparação de robustez setorial

[Comparação de Cenários — opcional]
    → Pass 1 em Cenário A + Pass 1 em Cenário B (2 chamadas)
    → Tabela de consenso/divergência setorial
```

**Decisão arquitetural central: Chain-of-Thought explícito em 5 passos**

Em vez de pedir "me dê setores e tickers", o prompt instrui o modelo a executar 5 passos em sequência antes de gerar o JSON:

```
STEP 1 — Parse macro variables: Identify each distinct macroeconomic variable
         (Selic, BRL/USD, Brent, etc.), its direction, and magnitude.

STEP 2 — Map transmission channels: For each variable, list which sectors it affects
         and through what mechanism (e.g., "Rising Selic → higher funding costs →
         compresses retail credit margins → negative for consumer discretionary").

STEP 3 — Net sector impacts: For each sector, net out positive and negative forces
         from multiple macro variables. Rank top 5 positive and top 5 negative.

STEP 4 — Ticker selection: Within the most impacted sectors, identify 3 stocks with
         maximum positive exposure and 3 with maximum negative.

STEP 5 — Risk assessment: Identify top 3 risks that would cause this thesis to fail.
```

Isso força o modelo a construir a cadeia de raciocínio antes de concluir — reduzindo respostas superficiais e aumentando consistência.

---

## Prompts de Desenvolvimento (exemplos enviados ao Claude)

Durante a construção, os prompts abaixo (ou variantes próximas) foram usados para iterar sobre a solução:

> **Arquitetura inicial:**
> "Quero uma ferramenta que recebe um cenário macroeconômico em linguagem natural e retorna recomendações setoriais e de tickers para a bolsa brasileira. O modelo precisa raciocinar explicitamente sobre canais de transmissão antes de concluir. Output em JSON validado por Pydantic. Como estruturo o schema e o prompt?"

> **Chain-of-Thought forçado:**
> "O modelo está retornando recomendações genéricas sem explicar o mecanismo. Quero forçá-lo a executar 5 passos em sequência antes de gerar o JSON: (1) identificar variáveis macro, (2) mapear canais de transmissão por setor, (3) calcular impacto líquido, (4) selecionar tickers, (5) identificar riscos da tese. Como escrevo esse prompt de forma que os passos sejam respeitados?"

> **Context injection de mercado:**
> "O modelo está usando conhecimento genérico de bolsa americana. Quero injetar um bloco de contexto com composição do Ibovespa, pesos aproximados por setor e sensibilidades macro conhecidas para cada setor. Como incluo isso no prompt sem ultrapassar o context window e sem prejudicar a qualidade da resposta?"

> **Análise de sensibilidade:**
> "Dado um cenário base, quero que o modelo gere automaticamente 3 variantes — pessimista, base e otimista — mudando os parâmetros-chave do cenário. Depois rodo a análise nas 3 variantes e comparo quais setores mantêm a direção. Como estruturo o prompt de geração de variantes e como comparo os outputs?"

> **Self-critique para consistência lógica:**
> "Às vezes o modelo recomenda um setor como beneficiado mas escolhe um ticker negativo do mesmo setor sem explicar. Quero um segundo pass que verifique contradições internas: setor positivo com ticker negativo, confidence levels mal calibrados, mecanismos genéricos. Como escrevo o prompt de verificação de consistência?"

---

## Decisões de Prompt Engineering

### 1. Brazilian Market Context como Knowledge Injection

LLMs têm conhecimento limitado e desatualizado sobre composição setorial do Ibovespa. A solução é injetar explicitamente no prompt um bloco de contexto com pesos aproximados do Ibovespa e sensibilidades macro conhecidas por setor:

```
BRAZILIAN EQUITY MARKET CONTEXT (Ibovespa composition, June 2025):
- Financeiro/Bancos (~22%): Itaú (ITUB4), Bradesco (BBDC4), BB (BBAS3)
  → Sensitive to Selic rate, credit spreads, NIM, loan growth, default rates
- Energia/Petróleo (~15%): Petrobras (PETR4), Ultrapar (UGPA3)
  → Sensitive to Brent, BRL/USD exchange rate, refinery margins, government risk
- Mineração (~12%): Vale (VALE3), CSN Mineração (CMIN3)
  → Sensitive to China iron ore demand, steel prices, BRL/USD
...
```

Isso ancora o modelo em conhecimento de mercado real em vez de generalizações.

### 2. Transmission channels como campo explícito obrigatório

Além do `rationale` textual, pedimos `transmission_channels: [...]` — lista de mecanismos específicos por setor. Isso força granularidade:

```json
"transmission_channels": [
  "NIM expansion via faster repricing of floating-rate assets",
  "Higher return on equity as cost of capital rises for borrowers",
  "Credit spread widening benefits fixed income portfolio"
]
```

Sem esse campo, o modelo tende a respostas genéricas como "benefited from rising rates".

### 3. Confidence Scoring diferenciado

Cada setor e ticker tem `confidence: high|medium|low`. O modelo é instruído a variar — setores com mecanismo direto e óbvio (financeiro + Selic) recebem `high`; setores com transmissão indireta recebem `medium`. Mais honesto do que apresentar tudo com igual certeza.

### 4. Self-critique com verificação de consistência cruzada

O segundo prompt procura especificamente contradições internas:

```
1. Are there any logical contradictions? (e.g., recommending a sector as "benefited"
   while picking a negative ticker from that same sector without explaining why)
2. Are the transmission mechanisms specific and correct, or generic?
3. Are confidence levels appropriately calibrated?
4. What important blind spots or alternative scenarios were not considered?
```

### 5. Anti-confabulação para características de empresas

```
You never confabulate company characteristics — if you are uncertain about a specific
company metric, you focus on directional reasoning rather than false precision.
```

Evita que o modelo invente P/L ratios ou grau de alavancagem específico.

---

## Extensões Implementadas e Escolha de Priorização

O Case 2 foi o **case secundário em termos de aprofundamento** (o Case 1 foi o principal), mas ainda recebeu investimento significativo nas extensões. As escolhas foram:

| Extensão | Status | Justificativa |
|----------|--------|---------------|
| **Self-critique loop** | ✅ Implementado | Essencial para detectar contradições lógicas internas — ex: setor beneficiado com ticker negativo sem explicação |
| **Canais de transmissão explícitos** | ✅ Implementado | Campo `transmission_channels` obrigatório — força o modelo a nomear o mecanismo, não apenas a conclusão |
| **Confidence scoring** | ✅ Implementado | `confidence` por setor/ticker + `conviction_score` por ticker — calibração honesta da incerteza |
| **Análise de sensibilidade** | ✅ Implementado | 3 variantes via LLM + tabela de robustez setorial — identifica quais recomendações dependem do cenário |
| **Comparação de cenários** | ✅ Implementado | Side-by-side com tabela de consenso/divergência — útil para debater diferentes visões de mercado |
| **Interface Streamlit** | ✅ Implementado | Interface funcional com 4 cenários de exemplo, tema BBI |
| **Backtest histórico** | Não implementado | Exigiria dados históricos de retorno setorial para validação quantitativa — não priorizei sem dados reais |
| **Comparação multi-modelo** | Não implementado | Tecnicamente simples (rodar dois modelos no mesmo cenário), mas valor marginal para demonstração |

---

## Exemplo de Execução

**Input:** `"A Selic cai para 10% ao longo de 2025, mas o câmbio permanece pressionado em torno de BRL 5,80 por dólar devido ao risco fiscal. O preço do petróleo Brent se mantém em USD 80/barril e as commodities metálicas estão em alta de 15%, puxadas pela recuperação da demanda chinesa."`

**Output JSON (trecho):**
```json
{
  "scenario_summary": "Afrouxamento monetário gradual (Selic → 10%) com pressão cambial persistente (BRL 5,80) refletindo risco fiscal. Petróleo estável em USD 80 e minério de ferro em alta 15% puxado por recuperação da demanda chinesa.",
  "overall_market_bias": "moderately_bullish",
  "benefited_sectors": [
    {
      "sector": "Mineração",
      "ibovespa_weight_pct": "12%",
      "impact_score": 9,
      "direction": "positive",
      "rationale": "Alta do minério (+15%) combinada com câmbio desvalorizado gera expansão expressiva de margens EBITDA para Vale e pares — receitas em USD, custos majoritariamente em BRL.",
      "transmission_channels": ["commodity price uplift", "FX tailwind on USD revenues", "China demand recovery signal"],
      "confidence": "high"
    },
    {
      "sector": "Varejo",
      "ibovespa_weight_pct": "7%",
      "impact_score": 7,
      "direction": "positive",
      "rationale": "Queda da Selic reduz custo do crédito ao consumidor e melhora acesso ao financiamento — principal driver de demanda para varejo de maior ticket.",
      "transmission_channels": ["consumer credit cost reduction", "improved retail financing conditions"],
      "confidence": "high"
    }
  ],
  "positive_tickers": [
    {
      "ticker": "VALE3",
      "company": "Vale S.A.",
      "conviction_score": 9,
      "rationale": "Maior produtor de minério do mundo captura duplamente: alta do preço (+15%) e BRL depreciado (receitas 100% USD, ~40% dos custos em BRL).",
      "confidence": "high"
    }
  ],
  "thesis_risks": [
    {
      "risk": "Reversão do câmbio com Selic caindo mais rápido que o esperado",
      "probability": "medium",
      "impact": "moderate",
      "affected_tickers": ["VALE3", "PETR4"],
      "mitigation": "Monitorar fluxo de capital estrangeiro e dinâmica do diferencial de juros Brasil-EUA"
    }
  ]
}
```

---

## Log de Tempo Gasto

| Atividade | Tempo (aprox.) |
|-----------|----------------|
| Planejamento e modelagem Pydantic | 1h |
| Design do prompt de análise (CoT + market context) | 2h |
| Design do self-critique prompt | 1h |
| Reporter markdown | 0.5h |
| CLI | 0.5h |
| Interface Streamlit base | 2h |
| Extensão: Análise de Sensibilidade (prompt + UI) | 1h |
| Extensão: Comparação de Cenários (UI) | 0.5h |
| README + testes | 1h |
| **Total** | **~7h** |

---

## Por que me Aprofundar no Case 1 (e o que foi feito no Case 2)

O **Case 1 foi escolhido como case de aprofundamento principal.** A razão central: o risco de erro é mais alto lá — citar algo que o CEO não disse é um erro imediato de credibilidade, o que exigiu mais iteração de prompt e mais extensões de verificação.

O Case 2 recebeu investimento em extensões de alto valor demonstrável em menos tempo: análise de sensibilidade, comparação de cenários e confidence scoring adicionam dimensão analítica real à ferramenta básica sem exigir o mesmo grau de garantia contra alucinação que o Case 1 exige.

---

## Três Limitações Mais Sérias

**1. Conhecimento de empresas desatualizado**
O context injection tem dados de 2025, mas características específicas de empresas (alavancagem, política de dividendos, hedging cambial) mudam trimestralmente. O modelo pode aplicar premissas desatualizadas para tickers específicos. Em produção: integração com Bloomberg ou Economatica.

**2. Ausência de dados de sensibilidade quantitativos**
As recomendações são qualitativas. Um analista precisaria de betas estimados setor×variável macro e impacto em EPS por 1% de variação na Selic. Esses dados não existem no prompt — são inferidos qualitativamente pelo modelo.

**3. Cenários ambíguos geram premissas implícitas**
Se o cenário for vago ("juros sobem") sem especificar magnitude ou timeline, o modelo faz premissas sem confirmação. Um passo de clarificação/parsing antes da análise evitaria isso.

---

## Com Mais 2 Semanas, Faria

1. **Backtest histórico** — dado um cenário passado (ex: "Selic subiu de 2% para 13,75% em 2021-2022"), rodar a análise retroativamente e comparar com o retorno real dos setores recomendados. Isso criaria um mecanismo de avaliação de qualidade das recomendações.

2. **Integração com dados reais dos tickers via Yahoo Finance** — puxar cotações, P/L e EV/EBITDA dos tickers recomendados para contextualizar as recomendações com valuation atual. Hoje as recomendações são puramente qualitativas. A biblioteca `yfinance` foi testada durante o desenvolvimento, mas é bloqueada em redes corporativas; com mais tempo, implementaria a integração via API oficial do Yahoo Finance com autenticação adequada para garantir funcionamento em qualquer ambiente.

3. **Parsing e clarificação de cenários ambíguos** — um passo inicial que confirma as premissas implícitas do cenário antes de rodar a análise. Ex: "você disse 'juros sobem' — para qual patamar e em qual prazo?"

4. **Análise quantitativa de sensibilidade** — estimar betas históricos por setor vs. cada variável macro (Selic, BRL/USD, Brent) e usar isso para escalar os impactos qualitativos do modelo.

5. **Histórico de cenários com busca semântica** — persistir análises em banco SQLite e permitir busca como "cenários anteriores com Selic > 14%" ou "quando o setor financeiro foi o mais beneficiado".
