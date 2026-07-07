# Arquitetura — Stack de Margem BI

## Domínio de negócio

O Grupo Argofruta exporta frutas (manga, uva, avocado, limão). Esta stack calcula a **margem de contribuição por item de nota de venda**:

```
margem = receita líquida − custos
```

Onde custos incluem matéria-prima (ficha de custo por pallet), embalagem, frete (marítimo/rodoviário/aéreo, conforme incoterm), despesas portuárias, seguro, royalties, comissões e provisões de fornecedor — com regras específicas por fruta (MANGA, UVA, AVOCADO, LIMÃO, "demais"). O resultado alimenta o painel de margem que o time usa para decisão comercial (preço, venda) por fruta/semana.

## Stack atual (em produção)

- **ERP:** Sankhya, banco Oracle.
- **Carga:** `SANKHYA.STP_BMC_CARGA_MRG_BI_BASE` materializa a view de margem numa tabela física (`AD_NOTASITEMPROMARGEMBI`), publicada via flag `ATIVO = 'S'`.
- **Cálculo:** `SANKHYA.VW_BMC_BI_BASE_ITENS_V9` (~130 colunas, pirâmide de 3 níveis de subconsulta) lê `SANKHYA.VW_NOTAS_31` (13 CTEs, ~40 joins) que lê as tabelas transacionais Sankhya (`TGFCAB`, `AD_TGFITECOMPL`, `TGFITE`, ...).
- **Consumo:** pipeline Pentaho (Oracle → PostgreSQL) alimenta **Looker Studio**, onde o time lê o painel de margem.

Cadeia de carga:

```
STP_BMC_CARGA_MRG_BI_BASE   (procedure de carga)
        ↓ lê
VW_BMC_BI_BASE_ITENS_V9     (view de margem — camada de cálculo)
        ↓ lê
VW_NOTAS_31                 (view base — camada de coleta de notas/itens)
        ↓ lê
TGFCAB / AD_TGFITECOMPL / TGFITE / ...  (dados transacionais Sankhya)
```

Documentação técnica completa, objeto a objeto (Resumo, Fluxo, Entradas, Saídas, Regras de negócio, Cálculos, Dependências...): `docs/STACK_MARGEM_BI.md`. Revisão de performance/otimização: `docs/REVISAO_TECNICA_STACK_MARGEM_BI.md`.

## Stack futura (proposta, ainda não contratada)

Proposta comercial da **Multiedro** (vendor terceiro) para migrar/expandir para GCP: ingestão → **Dataflow** (Apache Beam/Python) → **Cloud Storage** (Data Lake) → **BigQuery** (Data Warehouse) → **Looker Studio Pro** (BI), com **Cloud VPN** para acessar a origem Sankhya. Escopo explicitamente **exclui** governança de dados e IA.

Isso é plano, não código — não assumir que existe até confirmação de que foi contratado. O PDF da proposta fica só local (não versionado, ver `.gitignore` — tem preço/dado de fornecedor).

## Convenção de nomenclatura Sankhya

- `STP_` = procedure · `VW_` = view · `FU_`/`FUN_` = function · `AD_` = tabela/coluna customizada Argofruta/Sankhya · `TGF*`/`TSI*`/`TCS*` = tabelas padrão do ERP Sankhya (estrutura conhecida, baixa prioridade documentar a menos que uma coluna específica esteja em uso).

## Pontos críticos conhecidos da stack atual

(detalhados em `docs/STACK_MARGEM_BI.md` e `docs/REVISAO_TECNICA_STACK_MARGEM_BI.md` — resumo para não esquecer):

- **Publicação não é atômica**: a procedure trunca `AD_NOTASITEMPROMARGEMBI` antes de recarregar. Se falhar no meio do loop, o BI fica **sem nenhuma linha `ATIVO='S'`** — o painel perde a base vigente.
- `DELETE ... WHERE ATIVO='S'` é hoje um no-op redundante (roda depois do truncate, não existe mais linha 'S' pra apagar).
- Sem `EXCEPTION WHEN OTHERS` — qualquer erro aborta sem log e sem rollback controlado.
- `BULK COLLECT` de 1000 sem `SAVE EXCEPTIONS` — um erro de dado numa linha aborta o lote inteiro.
- Na view V9, vários indicadores de margem (`CUSTOTOTALGER`, `MARGEMGER`, `PERCMARGEMGER`, `PROVISAO_FORNECEDOR_GER`) são calculados em **dois níveis diferentes** (N2 e projeção externa) com fórmulas distintas — fonte recorrente de confusão sobre "qual valor é o de verdade" (é o da camada externa).
- Reescrita da V9 (maior gargalo, ~57% do tempo de carga) ainda não iniciada — depende de ambiente de homologação ou deploy paralelo (`_V10`) antes de ir pra produção.

Decisões arquiteturais registradas: `docs/adr/`.
