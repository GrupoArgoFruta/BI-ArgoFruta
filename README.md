# BI-ArgoFruta

Documentação e governança da stack de Business Intelligence de margem do Grupo Argofruta (exportadora de frutas — manga, uva, avocado, limão).

## O que é isso

Este repositório documenta, objeto a objeto, a stack que calcula a margem de contribuição por item de nota de venda e alimenta o painel de BI que o time usa pra decisão. Hoje ela roda sobre o ERP **Sankhya** (Oracle):

```
STP_BMC_CARGA_MRG_BI_BASE   (procedure de carga)
        ↓ lê
VW_BMC_BI_BASE_ITENS_V9     (view de margem — camada de cálculo)
        ↓ lê
VW_NOTAS_31                 (view base — camada de coleta de notas/itens)
        ↓ lê
TGFCAB / TGFITE / ...       (dados transacionais Sankhya)
```

Existe também uma proposta (ainda não contratada) de migração para GCP (Dataflow → BigQuery → Looker Studio Pro) — ver `ARCHITECTURE.md`.

## Estrutura

```
README.md          — este arquivo
ARCHITECTURE.md     — visão técnica da stack (atual + futura), domínio de negócio, pontos críticos
CONTRIBUTING.md      — regra de ouro, tags, regra obrigatória de documentação, convenção de commit
CHANGELOG.md         — log de progresso datado (✅ Confirmado / ⚠️ Pendência)
docs/
  STACK_MARGEM_BI.md                 — doc técnica objeto a objeto (Resumo, Fluxo, Entradas, Saídas, Regras de negócio, Cálculos, Dependências...)
  REVISAO_TECNICA_STACK_MARGEM_BI.md — revisão de performance/otimização
  FLUXOS.md                          — diagramas (Mermaid): linhagem de dados, execução da carga, grafo de dependências, CTEs da VW_NOTAS_31, arquitetura futura GCP, fluxos de trabalho
  RISCOS_ABERTOS.md                  — todo [VALIDAR]/ponto crítico ativo, consolidado num só lugar (não substitui as seções originais)
  GLOSSARIO.md                       — termos/siglas de domínio, os 26 objetos em uma frase, dicionário das colunas finais do painel
  adr/                                — decisões arquiteturais registradas (Architecture Decision Records)
sql/
  procedures/*.sql   — corpo real (CREATE OR REPLACE) de cada procedure Sankhya
  views/*.sql        — corpo real de cada view Sankhya
  functions/*.sql    — corpo real de cada function Sankhya
skills/
  bi-impact-check/            — checklist obrigatório antes de mexer em algo que alimenta o BI
  trazer-documentar-objeto/   — passo a passo pra trazer um objeto novo do Sankhya e documentá-lo
scripts/
  check_docs_coverage.py — falha se um objeto novo em sql/ não tiver seção correspondente em docs/ (roda no CI, ver .github/workflows/docs-coverage.yml)
```

> Nota: os dois arquivos em `skills/` acima estão referenciados aqui e em `CONTRIBUTING.md`/`ARCHITECTURE.md`, mas **não existem hoje no working tree** — foram apagados por um commit acidental (`aa50339`, 07/07/2026). Ficam recuperáveis via `git checkout ce3f439 -- skills/`. Decisão de restaurar ou não é do time — ver `docs/FLUXOS.md`, seção "Achados desta rodada de revisão".

## Regra de ouro

Toda proposta de mudança num objeto que alimenta o BI de margem mira **resultado idêntico** para qualquer conjunto de dados, a menos que seja uma correção funcional explícita. Onde a equivalência não é garantível só pelo texto, a mudança é marcada `[VALIDAR]` com o risco descrito — nunca recomendada às cegas. Antes de qualquer mudança ir para produção, ela é reconciliada contra produção. Detalhes completos em `CONTRIBUTING.md`.


