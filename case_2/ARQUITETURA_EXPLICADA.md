# Macro Scenario Engine — Arquitetura Explicada

> Documento didático: como o sistema funciona por dentro, passo a passo,
> aplicando um exemplo concreto em cada etapa.

---

## O Cenário de Exemplo

Usaremos **este cenário** do início ao fim do documento:

> *"O governo anuncia um déficit fiscal maior que o esperado.
> O mercado precifica alta da Selic de volta para 15%.
> O câmbio dispara para R$ 6,50. As curvas de juros longos
> abrem 150bps. Há fuga de capital estrangeiro da bolsa brasileira."*

É um cenário de **crise fiscal** — simples, realista, e com impactos claros
em setores distintos do Ibovespa.

---

## Visão Geral do Fluxo

```
[1] Usuário digita o cenário
        ↓
[2] Código injeta contexto do Ibovespa
        ↓
[3] Modelo pensa em 5 passos (Chain-of-Thought)
        ↓
[4] JSON retornado e validado pelo Pydantic
        ↓
[5] Self-critique: segunda passagem do modelo
        ↓
[6] Reporter gera relatório ≤ 500 palavras
        ↓
[7] Streamlit exibe tudo + extensões avançadas
```

---

## Etapa 1 — Entrada do Usuário

O analista abre o Streamlit e digita o cenário em **linguagem natural**.
Sem formulários, sem campos estruturados. Texto livre.

**No código (`app.py`):**

```python
scenario_input = st.text_area(
    "Descreva o cenário macroeconômico em linguagem natural:",
    height=140,
)
```

**O que entra:**

```
"O governo anuncia um déficit fiscal maior que o esperado.
O mercado precifica alta da Selic de volta para 15%.
O câmbio dispara para R$ 6,50. As curvas de juros longos
abrem 150bps. Há fuga de capital estrangeiro da bolsa brasileira."
```

**Por que texto livre?**
Porque um analista de equity pensa em cenários como narrativas, não como
formulários. Forçar campos estruturados ("qual o valor da Selic?") perderia
nuances como "fuga de capital" ou "curvas de juros longas abertas" que
afetam setores específicos de formas que uma caixa de seleção não captura.

---

## Etapa 2 — Injeção de Contexto do Ibovespa

Antes de enviar qualquer coisa ao modelo, o código cola automaticamente
um bloco de conhecimento de mercado brasileiro. Este bloco **não é gerado
pelo modelo** — ele vem do próprio código, é estático e controlado.

**No código (`analyzer.py`):**

```python
BRAZIL_MARKET_CONTEXT = """
BRAZILIAN EQUITY MARKET CONTEXT (Ibovespa, June 2025):

Financeiro/Bancos (~22%): ITUB4, BBDC4, BBAS3
  → Sensível à Selic: Selic alta = spread bancário maior = lucro maior
  → Sensível ao crédito: inadimplência sobe com juros altos

Energia/Petróleo (~15%): PETR4, PETR3
  → Sensível ao Brent e ao câmbio (receita em USD)

Mineração (~12%): VALE3, CMIN3
  → Sensível ao preço do minério de ferro e ao câmbio
  → Receita em USD, custos em BRL = câmbio alto = margem maior

Varejo (~7%): MGLU3, LREN3, ASAI3
  → Sensível à Selic: crédito ao consumidor fica mais caro = vendas caem
  → Sensível ao câmbio: produtos importados encarecem

Construção Civil (~5%): MRVE3, CYRE3
  → Altamente sensível à Selic: hipoteca encarece, demanda cai
...
"""
```

**O que é adicionado ao nosso exemplo:**

```
[CONTEXTO INJETADO]

Financeiro (~22%): ITUB4, BBDC4
  → Selic alta = spread bancário maior = lucro sobe

Varejo (~7%): MGLU3, LREN3
  → Selic alta = crédito ao consumidor caro = vendas caem

Mineração (~12%): VALE3
  → Câmbio alto = receita USD converte em mais reais = margem explode

Construção (~5%): MRVE3, CYRE3
  → Selic alta = hipoteca inacessível = demanda desaba
```

**Por que isso existe?**
O modelo de linguagem tem conhecimento geral de economia, mas não sabe
especificamente que a VALE3 tem receita 100% em USD ou que a MGLU3 depende
de crédito ao consumidor. Sem essa injeção, o modelo daria respostas genéricas
do tipo "bancos se beneficiam de juros altos" sem conectar ao ticker correto
com a justificativa certa.

---

## Etapa 3 — Chain-of-Thought: 5 Passos Obrigatórios

Esta é a decisão técnica mais importante do projeto.

Em vez de perguntar direto *"quais setores ganham e perdem?"*, o prompt
força o modelo a **construir o raciocínio em 5 etapas** antes de gerar
qualquer resposta. Isso é chamado de **Chain-of-Thought prompting**.

**No código (prompt em `analyzer.py`):**

```
INSTRUCTIONS — think through each step before writing the final JSON:

STEP 1 — Parse macro variables
STEP 2 — Map transmission channels
STEP 3 — Net sector impacts
STEP 4 — Ticker selection
STEP 5 — Risk assessment
```

**Aplicando ao nosso exemplo:**

---

### Step 1 — Parse de Variáveis Macro

O modelo identifica cada variável econômica presente no texto:

```
Variável 1: Taxa Selic
  direção: subindo (rising)
  magnitude: grande (large)
  evidência: "precifica alta da Selic de volta para 15%"

Variável 2: Câmbio BRL/USD
  direção: subindo (rising)
  magnitude: grande (large)
  evidência: "câmbio dispara para R$ 6,50"

Variável 3: Risco Fiscal
  direção: piorando
  magnitude: grande
  evidência: "déficit fiscal maior que o esperado"

Variável 4: Fluxo de Capital Estrangeiro
  direção: saindo
  magnitude: grande
  evidência: "fuga de capital estrangeiro da bolsa"
```

---

### Step 2 — Canais de Transmissão

Para cada variável identificada, o modelo mapeia **como ela afeta cada setor**
e através de qual mecanismo específico:

```
Selic ↑ → Financeiro:
  mecanismo: "Spread bancário aumenta — banco capta a taxas
              menores e empresta a taxas mais altas → NIM expande"
  direção: POSITIVO

Selic ↑ → Varejo:
  mecanismo: "Crédito ao consumidor encarece → parcelamentos
              com juros altos → consumidor compra menos ou adia"
  direção: NEGATIVO

Selic ↑ → Construção Civil:
  mecanismo: "Financiamento imobiliário atrelado à Selic
              → parcela mensal sobe → compradores saem do mercado"
  direção: NEGATIVO FORTE

Câmbio ↑ → Mineração (VALE3):
  mecanismo: "VALE3 vende minério em USD. Com câmbio em R$6,50,
              cada dólar recebido converte em mais reais,
              enquanto os custos operacionais (em BRL) ficam fixos
              → margem EBITDA em BRL se expande automaticamente"
  direção: POSITIVO FORTE

Câmbio ↑ → Varejo (MGLU3):
  mecanismo: "Produtos eletrônicos são importados em USD.
              Com câmbio em R$6,50, o custo do produto sobe
              mas o consumidor já está com crédito caro → duplo negativo"
  direção: NEGATIVO MUITO FORTE
```

---

### Step 3 — Netting por Setor

O modelo soma os efeitos positivos e negativos de todas as variáveis
para chegar a um **impacto líquido** por setor:

```
Financeiro:
  Selic ↑ = +forte
  Câmbio ↑ = neutro (funding e ativos ambos sobem)
  → SALDO: POSITIVO, score 9/10, confidence: high

Mineração:
  Câmbio ↑ = +forte (receita USD)
  Fuga de capital = -leve (pressão no preço da ação)
  → SALDO: POSITIVO, score 8/10, confidence: high

Varejo:
  Selic ↑ = -forte (crédito caro)
  Câmbio ↑ = -forte (produto importado caro)
  → SALDO: NEGATIVO FORTE, score 9/10, confidence: high

Construção Civil:
  Selic ↑ = -muito forte (hipoteca inacessível)
  → SALDO: NEGATIVO FORTE, score 8/10, confidence: high

Utilities (Eletrobras):
  Selic ↑ = -moderado (DCF: taxa de desconto sobe → valuation cai)
  → SALDO: NEGATIVO, score 6/10, confidence: medium
```

---

### Step 4 — Seleção de Tickers

Dentro de cada setor com impacto relevante, o modelo escolhe
a empresa com **maior concentração de exposição** ao tema macro:

```
COMPRAR — Financeiro → ITUB4
  "Itaú Unibanco é o maior banco privado do Brasil. Tem a maior
   carteira de crédito e, portanto, captura diretamente a expansão
   de spread com a Selic em 15%. Menor exposição a crédito
   imobiliário que o Bradesco reduz risco de inadimplência."
  conviction_score: 9/10

COMPRAR — Mineração → VALE3
  "Vale é o maior produtor de minério de ferro do mundo.
   Receita 100% denominada em USD. Com câmbio em R$6,50,
   cada tonelada exportada gera mais reais sem aumento de custo.
   É o ticker com maior beta ao câmbio no Ibovespa."
  conviction_score: 8/10

VENDER — Varejo → MGLU3
  "Magazine Luiza é a varejista com maior exposição a crédito
   ao consumidor (carnê, parcelamento). Com Selic em 15%,
   o custo do parcelamento para o consumidor explode.
   Adicionalmente, 60% do mix são eletrônicos importados
   — câmbio em 6,50 comprime margem bruta."
  conviction_score: 9/10

VENDER — Construção → MRVE3
  "MRV é focada em baixa renda, segmento mais sensível ao
   custo do financiamento. Com Selic em 15%, as parcelas
   mensais do Minha Casa Minha Vida excedem a capacidade
   de pagamento do público-alvo."
  conviction_score: 8/10
```

---

### Step 5 — Riscos da Tese

O modelo identifica o que poderia fazer a análise estar errada:

```
Risco 1: Banco Central reverter e cortar Selic
  "Se o BC interpretar o déficit fiscal como contracionista
   (menos gastos futuros) e cortar Selic preventivamente,
   toda a tese de financeiro inverte. Afeta: ITUB4, BBDC4"
  probabilidade: low
  impacto: severe

Risco 2: China desacelerar abruptamente
  "Vale depende do minério de ferro. Se a China entrar em
   recessão, minério cai 20-30% e neutraliza o ganho cambial.
   Afeta: VALE3, CMIN3"
  probabilidade: medium
  impacto: severe

Risco 3: Governo controlar câmbio ou intervir nos bancos
  "Com câmbio em 6,50, o governo pode impor IOF ou controles
   de capital. Se forçar bancos a emprestar a taxas subsidiadas,
   o spread esperado não se materializa. Afeta: ITUB4, BBDC4"
  probabilidade: medium
  impacto: moderate
```

---

## Etapa 4 — Validação Pydantic

O JSON gerado pelo modelo passa por **validação automática** de schema.
Se qualquer campo estiver errado, o sistema rejeita antes de mostrar
qualquer resultado.

**O que é validado:**

```python
class SectorAnalysis(BaseModel):
    sector: str
    impact_score: int = Field(ge=1, le=10)       # obrigatório: entre 1 e 10
    confidence: Literal["high", "medium", "low"] # só esses 3 valores
    rationale: str                                # obrigatório, não pode ser vazio

class TickerRecommendation(BaseModel):
    ticker: str
    conviction_score: int = Field(ge=1, le=10)
    direction: Literal["positive", "negative"]
```

**Exemplos de erros que seriam capturados:**

```python
# Modelo tenta colocar score 11 → REJEITADO
{"impact_score": 11}
# Erro: "Input should be less than or equal to 10"

# Modelo inventa uma categoria de confiança → REJEITADO
{"confidence": "muito alto"}
# Erro: "Input should be 'high', 'medium' or 'low'"

# Modelo esquece um campo obrigatório → REJEITADO
{}
# Erro: "Field required: sector"
```

**Por que isso importa?**
Sem validação, o modelo poderia retornar dados inconsistentes que
passariam silenciosamente para a UI. O Pydantic garante que **se a
análise aparecer na tela, ela está estruturalmente correta**.

---

## Etapa 5 — Self-Critique (Segunda Passagem)

Após gerar a análise, o sistema faz **uma segunda chamada ao modelo**,
desta vez pedindo que ele aja como revisor crítico da própria análise.

**O que o segundo prompt verifica:**

```
1. Há contradições internas?
   Ex: setor financeiro como "beneficiado" mas BBDC4 como "negativo"
   sem explicar por quê

2. Os mecanismos de transmissão são específicos ou genéricos?
   Ruim:  "bancos se beneficiam de juros altos"
   Bom:   "NIM expande pois reprecificação de ativos é mais rápida
           que reprecificação de passivos em ciclo de alta"

3. Os confidence scores estão bem calibrados?
   Se tudo for "high", algo está errado — há sempre incerteza

4. Quais pontos cegos a análise não considerou?
```

**Aplicando ao nosso exemplo:**

```
RESULTADO DO SELF-CRITIQUE:

✅ Financeiro como beneficiado: CONSISTENTE
   Mecanismo de NIM está bem explicado.

✅ VALE3 como compra: CONSISTENTE
   Receita USD e custos BRL bem fundamentados.

⚠️ PONTO CEGO DETECTADO:
   "A análise não considerou que bancos com alta
   exposição a crédito imobiliário podem sofrer aumento
   de inadimplência com Selic a 15%, o que afetaria
   principalmente BBDC4 (maior carteira imobiliária).
   ITUB4 seria mais seguro dentro do setor."

reliability_score: 7/10
overall_consistency: "high"
```

---

## Etapa 6 — Reporter: Relatório Executivo

O objeto JSON validado é transformado em um relatório de **no máximo
500 palavras**, formatado para ser lido em 3 minutos.

**Saída do relatório para o nosso exemplo:**

```markdown
# Macro Scenario Engine — Impacto para Bolsa Brasileira
*02/06/2026 | Viés: 📉 MODERADAMENTE NEGATIVO*

**Cenário:** Crise fiscal com Selic a 15% e câmbio a R$6,50.
Fuga de capital estrangeiro pressiona toda a bolsa.

**Variáveis:** Selic ⬆️ (large) | BRL/USD ⬆️ (large) | Fiscal ⬇️ (large)

## ✅ Setores Beneficiados
| Setor       | Peso  | Score   | Mecanismo-chave                        |
|-------------|-------|---------|----------------------------------------|
| Financeiro  | ~22%  | 9/10 🟢 | NIM expande com Selic a 15%            |
| Mineração   | ~12%  | 8/10 🟢 | Câmbio 6,50 amplifica receita em USD   |

## ❌ Setores Prejudicados
| Setor           | Peso | Score   | Mecanismo-chave                     |
|-----------------|------|---------|-------------------------------------|
| Varejo          | ~7%  | 9/10 🟢 | Crédito caro + produto importado    |
| Construção Civil| ~5%  | 8/10 🟢 | Hipoteca inacessível com Selic 15%  |

## 📈 Comprar | 📉 Vender
| Dir | Ticker  | Convicção | Tese                                      |
|-----|---------|-----------|-------------------------------------------|
| 📈  | `ITUB4` | 9/10      | Maior banco privado, captura spread total |
| 📈  | `VALE3` | 8/10      | Receita 100% USD, câmbio é vento a favor  |
| 📉  | `MGLU3` | 9/10      | Selic cara + eletronico importado         |
| 📉  | `MRVE3` | 8/10      | Baixa renda não aguenta hipoteca          |

## ⚠️ Riscos
1. **BC cortar Selic** 🟢 — inverte tese financeiro. Afeta: `ITUB4`
2. **China desacelerar** 🟡 — minério cai, neutraliza câmbio. Afeta: `VALE3`
3. **Intervenção governamental** 🟡 — controle de câmbio ou spread. Afeta: `ITUB4`

---
*Self-critique: HIGH — confiabilidade 7/10*
*Ponto cego: BBDC4 mais vulnerável que ITUB4 por exposição imobiliária*
```

---

## Etapa 7 — Extensões Avançadas

### 7a — Análise de Sensibilidade

O sistema gera automaticamente 3 versões do cenário e analisa cada uma:

```
OTIMISTA:
  "BC surpreende e mantém Selic em 12,5% sinalizando
   que o déficit é temporário. Câmbio se aprecia para R$5,80."

BASE:
  "Selic sobe para 15%, câmbio em R$6,50."   ← cenário original

PESSIMISTA:
  "Selic dispara para 17%, câmbio atinge R$7,50.
   Agências de rating colocam Brasil em perspectiva negativa."
```

**Tabela de robustez resultante:**

```
┌──────────────┬───────────┬───────┬──────────┬─────────────────┐
│ Setor        │ Pessimista│ Base  │ Otimista │ Robustez        │
├──────────────┼───────────┼───────┼──────────┼─────────────────┤
│ Financeiro   │    ✅     │  ✅   │    ✅    │ 🟢 Robusto      │
│ Mineração    │    ✅     │  ✅   │    ✅    │ 🟢 Robusto      │
│ Varejo       │    ❌     │  ❌   │    ❌    │ 🟢 Robusto      │
│ Construção   │    ❌     │  ❌   │    🟡    │ 🟡 Condicional  │
│ Utilities    │    ❌     │  ❌   │    ✅    │ 🟡 Condicional  │
└──────────────┴───────────┴───────┴──────────┴─────────────────┘

→ ITUB4 e VALE3 são compra mesmo no cenário pessimista.
→ Construção só melhora se Selic não passar de 13%.
```

---

### 7b — Comparação de Dois Cenários

O usuário digita dois cenários distintos e o sistema mostra o que diverge:

```
CENÁRIO A: "Crise fiscal — Selic 15%, câmbio R$6,50"
CENÁRIO B: "China aquece fortemente — minério +30%, Selic estável em 11%"

RESULTADO DA COMPARAÇÃO:
┌──────────────┬───────────┬───────────┬──────────────────┐
│ Setor        │ Cenário A │ Cenário B │ Status           │
├──────────────┼───────────┼───────────┼──────────────────┤
│ Mineração    │    ✅     │    ✅     │ 🟢 Consenso      │
│ Financeiro   │    ✅     │    ❌     │ 🔴 Diverge       │
│ Varejo       │    ❌     │    ✅     │ 🔴 Diverge       │
│ Construção   │    ❌     │    ✅     │ 🔴 Diverge       │
└──────────────┴───────────┴───────────┴──────────────────┘

✅ COMPRA EM AMBOS OS CENÁRIOS: VALE3
   → Robusta tanto com câmbio alto quanto com minério alto.

❌ VENDA EM AMBOS OS CENÁRIOS: nenhuma
   → Não há consenso negativo entre os dois cenários.
```

**Insight para o analista:**
VALE3 é a única posição que funciona independentemente
de qual tese macro se materializar.

---

## Resumo Técnico

| Componente | Tecnologia | Por quê |
|---|---|---|
| Interface | Streamlit | Prototipagem rápida, código Python puro |
| Schema de output | Pydantic v2 | Validação automática, rejeita alucinações |
| Raciocínio | Chain-of-Thought | Força lógica explícita antes de concluir |
| Contexto de mercado | Knowledge injection | Âncora o modelo em dados reais do Ibovespa |
| Qualidade | Self-critique (2ª passagem) | Detecta contradições internas |
| Robustez | Análise de sensibilidade | Testa tese em 3 cenários automaticamente |
| Comparação | Scenario diff | Identifica consensos entre teses distintas |

---

*Documento de apoio — Processo Seletivo Estágio Tech/AI, Bradesco BBI*
