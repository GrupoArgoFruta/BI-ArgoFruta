# BI-ArgoFruta

Codebase e instruções do usuário abaixo. IMPORTANTE: estas instruções SOBRESCREVEM qualquer comportamento padrão e devem ser seguidas exatamente como escritas.

## O que é este projeto

Documentação e governança da **stack de Business Intelligence de margem** do Grupo Argofruta (exportadora de frutas — manga, uva, avocado, limão), rodando hoje sobre o ERP **Sankhya** (Oracle). Qualquer mudança aqui tem **impacto real em dado de negócio usado pra decisão** (margem por fruta/semana que alimenta o painel de BI) — trate este repositório com o mesmo rigor de um sistema em produção, não como um repositório de rascunho.

Não é o único projeto do usuário: para o padrão de outro sistema (EasyBiz, Spring Boot), ver `CLAUDE.md` daquele repo — **não misturar convenções**. Este projeto é da empresa Argofruta, commitado com conta corporativa (não a pessoal).

## Stack atual (em produção)

- **ERP:** Sankhya, banco Oracle.
- **Carga:** `SANKHYA.STP_BMC_CARGA_MRG_BI_BASE` (procedure) materializa a view de margem numa tabela física (`AD_NOTASITEMPROMARGEMBI`), publicada via flag `ATIVO = 'S'`.
- **Cálculo:** `SANKHYA.VW_BMC_BI_BASE_ITENS_V9` (view, ~130 colunas, pirâmide de 3 níveis de subconsulta) lê `SANKHYA.VW_NOTAS_31` (view base, 13 CTEs, ~40 joins) que lê as tabelas transacionais Sankhya (`TGFCAB`, `AD_TGFITECOMPL`, `TGFITE`, ...).
- **Consumo:** pipeline Pentaho (Oracle → PostgreSQL) alimenta **Looker Studio**, onde o time lê o painel de margem.
- **Domínio de negócio:** margem de contribuição por item de nota de venda = receita líquida − custos (matéria-prima/ficha de custo, embalagem, frete marítimo/rodoviário/aéreo conforme incoterm, despesas portuárias, seguro, royalties, comissões, provisões de fornecedor), com regras específicas por fruta (MANGA, UVA, AVOCADO, LIMÃO, "demais").

## Stack futura (proposta, ainda não contratada)

Existe uma proposta comercial da **Multiedro** (vendor terceiro) para migrar/expandir isso para GCP: ingestão → **Dataflow** (Apache Beam/Python) → **Cloud Storage** (Data Lake) → **BigQuery** (Data Warehouse) → **Looker Studio Pro** (BI), com **Cloud VPN** para acessar a origem. Escopo explicitamente **exclui** governança de dados e IA. Isso é plano, não código — não assumir que existe até o usuário confirmar que foi contratado. O PDF da proposta fica só local (não versionado — ver `.gitignore`, tem preço/dado de fornecedor).

## Estrutura do repositório

```
CLAUDE.md
docs/
  STACK_MARGEM_BI.md                    — doc técnica objeto a objeto da stack atual
  REVISAO_TECNICA_STACK_MARGEM_BI.md    — revisão de performance/otimização + log de progresso
sql/
  procedures/*.sql   — corpo real (CREATE OR REPLACE) de cada procedure Sankhya
  views/*.sql        — corpo real de cada view Sankhya
.claude/skills/
  bi-impact-check/   — checklist obrigatório antes de mexer em algo que alimenta o BI
```

Arquivo `.sql` em `sql/` sem a seção correspondente em `docs/` (ou vice-versa) é considerado documentação desatualizada — ver regra obrigatória abaixo.

## Convenção de nomenclatura Sankhya

- `STP_` = procedure · `VW_` = view · `FU_`/`FUN_` = function · `AD_` = tabela/coluna customizada Argofruta/Sankhya · `TGF*`/`TSI*`/`TCS*` = tabelas padrão do ERP Sankhya (estrutura conhecida, baixa prioridade documentar a menos que uma coluna específica esteja em uso).

## Tags usadas na documentação (manter consistência)

- `[EXTERNO]` — dependência citada mas cujo corpo ainda não foi trazido para `sql/`. Lista consolidada de pendências no final de `docs/STACK_MARGEM_BI.md`.
- `[VALIDAR]` — mudança proposta cuja equivalência funcional **não é garantível só pelo texto**. Descreva o risco em vez de recomendar às cegas.
- `✅ Confirmado` vs `⚠️ Pendência` — usado no log de progresso (`docs/REVISAO_TECNICA_STACK_MARGEM_BI.md`) para distinguir o que foi **medido/evidenciado** do que ainda não foi. Nunca promover uma pendência a confirmado sem medição real.

## Regra de ouro (não negociável)

Toda proposta de mudança num objeto que alimenta o BI de margem deve mirar **resultado idêntico** para qualquer conjunto de dados, a menos que a mudança seja explicitamente uma correção funcional (e nesse caso, isso deve estar destacado, não escondido dentro de uma "otimização").

- Se a equivalência não é 100% garantível só analisando o texto/SQL → marcar `[VALIDAR]` e descrever o risco.
- Antes de qualquer mudança ser tratada como "concluída" e ir para produção: **reconciliar** contra produção (por ANO/SEMANA/FRUTA, ou a granularidade equivalente) as métricas que a mudança toca — não é opcional quando o campo alimenta desconto/custo/margem.
- Nunca "corrigir" silenciosamente um ponto crítico conhecido (ver lista abaixo) sem sinalizar explicitamente o que mudou de comportamento — isso é produção, não refactor de brincadeira.
- Claude não tem acesso ao Oracle/GCP deste projeto. Qualquer alegação de performance ("ficou mais rápido", "gargalo é X") deve vir de medição real do usuário (`v$sql`, `EXPLAIN PLAN`, `DBA_TAB_STATISTICS`) — nunca inventar números ou percentuais.

## Pontos críticos conhecidos da stack atual

(detalhados em `docs/STACK_MARGEM_BI.md` e `docs/REVISAO_TECNICA_STACK_MARGEM_BI.md` — resumo pra não esquecer):

- **Publicação não é atômica**: a procedure trunca `AD_NOTASITEMPROMARGEMBI` antes de recarregar. Se falhar no meio do loop, o BI fica **sem nenhuma linha `ATIVO='S'`** — o painel perde a base vigente.
- `DELETE ... WHERE ATIVO='S'` é hoje um no-op redundante (roda depois do truncate, não existe mais linha 'S' pra apagar).
- Sem `EXCEPTION WHEN OTHERS` — qualquer erro aborta sem log e sem rollback controlado.
- `BULK COLLECT` de 1000 sem `SAVE EXCEPTIONS` — um erro de dado numa linha aborta o lote inteiro.
- Na view V9, vários indicadores de margem (`CUSTOTOTALGER`, `MARGEMGER`, `PERCMARGEMGER`, `PROVISAO_FORNECEDOR_GER`) são calculados em **dois níveis diferentes** (N2 e projeção externa) com fórmulas distintas — fonte recorrente de confusão sobre "qual valor é o de verdade" (é o da camada externa).
- Reescrita da V9 (maior gargalo, ~57% do tempo de carga) ainda não iniciada — depende de ambiente de homologação ou deploy paralelo (`_V10`) antes de ir pra produção.

## Convenção de commit

`tipo(#N): descrição` — mesmo padrão do EasyBiz. `N` = número real da issue em `github.com/GrupoArgoFruta/BI-ArgoFruta`. Sem issue aberta, usar `tipo: descrição`.

Tipos: `feat`, `fix`, `docs`, `refactor`, `perf`, `infra`, `tech-debt`.

## Releases

Como não existe um "número de versão" de aplicativo aqui (é uma stack de dados), usar **tags de data** (`vAAAA.MM.DD`) no GitHub quando um lote de mudanças em `sql/`+`docs/` for publicado em produção. A release note deve conter o resumo de reconciliação (o que foi comparado, resultado) — o mesmo formato que já existe informalmente no "LOG DE PROGRESSO" de `docs/REVISAO_TECNICA_STACK_MARGEM_BI.md`.

## Regra obrigatória

**Toda alteração em `sql/` → atualizar a seção correspondente em `docs/` (mesma estrutura: Resumo, Fluxo de execução, Entradas, Saídas, Regras de negócio, Cálculos, Dependências, Objetos chamados, Pontos críticos, Sugestões de melhoria, Resumo executivo) + registrar entrada datada no LOG DE PROGRESSO. Sem exceção.**

## Ownership de commit e git

- Quem commita é o usuário, sempre — Claude nunca roda `git commit` sem confirmação explícita nesta conversa.
- Claude nunca mexe em `git config` (usuário alterna entre conta pessoal e conta da empresa manualmente conforme o repositório).
- Remoto: `https://github.com/GrupoArgoFruta/BI-ArgoFruta.git` (org da empresa).

## Automação que impacta dado de BI

Antes de criar/alterar qualquer script, pipeline ou automação que leia ou escreva num objeto desta stack (atual ou futura, GCP), seguir o checklist do skill `bi-impact-check`.