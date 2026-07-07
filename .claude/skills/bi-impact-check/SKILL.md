---
name: bi-impact-check
description: This skill should be used when the user asks to "create an automation", "write a script", "add a pipeline", "change a procedure", "change a view", "optimize a query", "refactor SQL", or otherwise create/modify anything that reads from or writes to an object in the Argofruta margin BI stack (Sankhya/Oracle procedures and views under `sql/`, or a future GCP Dataflow/BigQuery pipeline). Also use before marking any such change as "done" or ready to publish to production.
---

# Checklist de impacto em dado de BI — Argofruta

Este projeto alimenta o painel de margem que o negócio usa pra decisão real (preço, venda, por fruta/semana). Um erro silencioso aqui não quebra um teste — aparece como um número errado numa reunião. Seguir este checklist sempre que a mudança tocar em algo que lê ou escreve num objeto da stack de margem BI (atual, em Oracle/Sankhya, ou futura, em GCP).

## 1. Mapear o raio de impacto antes de tocar em qualquer coisa

Antes de editar um objeto (`procedure`, `view`, `function`, tabela `AD_*`, ou um script de pipeline):

- Abrir `docs/STACK_MARGEM_BI.md` e `docs/REVISAO_TECNICA_STACK_MARGEM_BI.md` e localizar a seção do objeto (ou dos objetos que dependem dele — ver "Objetos que provavelmente dependem desta procedure/view" em cada seção).
- Se o objeto não estiver documentado ainda, tratar isso como um bloqueio: documentar primeiro (ver seção 4), só depois alterar.
- Confirmar se a mudança se propaga até `AD_NOTASITEMPROMARGEMBI` (a tabela que o BI lê) ou até uma tabela/dataset equivalente no futuro pipeline GCP. Se propaga, o raio de impacto é "o painel de margem inteiro", não só o objeto tocado.

## 2. Classificar a mudança

Toda mudança proposta cai em uma destas categorias — declarar qual é, explicitamente, antes de escrever código:

- **Correção funcional**: muda o resultado de propósito (ex.: um cálculo estava errado). Destacar isso com todas as letras — nunca disfarçar de "otimização".
- **Otimização/refatoração**: a intenção é manter o resultado idêntico e só mudar performance/legibilidade/estrutura.
- **Automação nova**: script/pipeline que ainda não existe (ex.: futuro job GCP Dataflow).

Para os dois últimos casos, a regra de ouro do `CLAUDE.md` do repositório se aplica: mirar resultado idêntico para qualquer conjunto de dados.

## 3. Provar equivalência ou marcar `[VALIDAR]`

Depois de escrever a mudança, avaliar se dá pra garantir, só olhando o código/SQL, que o resultado é idêntico ao anterior para qualquer dado de entrada.

- Se sim: explicar por quê (ex.: "só reordena joins, não muda predicado nem projeção").
- Se não (a maioria dos casos com CTEs, joins por expressão calculada, ou mudança de fonte de uma coluna): marcar `[VALIDAR]` na documentação e descrever o risco concreto — não afirmar que "deve funcionar" sem essa marcação.

Nunca pular esta etapa achando que "é só um índice" ou "só reescreveu o SQL de forma equivalente" — a V9 já tem histórico de indicadores recalculados em duas camadas com fórmulas diferentes por causa exatamente desse tipo de suposição não verificada (ver "Pontos críticos" em `docs/STACK_MARGEM_BI.md`).

## 4. Reconciliar antes de considerar "concluído"

Uma mudança só é "concluída" depois de reconciliada contra produção — não antes. Reconciliar significa comparar, na mesma granularidade de negócio (tipicamente ANO/SEMANA/FRUTA), as métricas que a mudança toca: quantidades, valores de nota, percentuais de desconto, custo total, margem.

- Registrar o resultado da reconciliação (bateu / não bateu / diferença de X%) na entrada de log da mudança — não deixar isso implícito.
- Se a reconciliação não foi rodada ainda, marcar a mudança como `⚠️ Pendência`, nunca como `✅ Confirmado`. Essa distinção existe no projeto exatamente pra impedir que suposição vire fato documentado.
- Claude não tem acesso ao Oracle/GCP deste projeto — não pode rodar a reconciliação sozinho. Pedir ao usuário os números (ou o resultado da query de reconciliação) antes de escrever "confirmado" em qualquer lugar.

## 5. Nunca corrigir silenciosamente um ponto crítico conhecido

A lista de pontos críticos conhecidos (publicação não atômica, ausência de `EXCEPTION WHEN OTHERS`, `DELETE` redundante pós-truncate, `BULK COLLECT` sem `SAVE EXCEPTIONS`) está em `CLAUDE.md` e detalhada em `docs/STACK_MARGEM_BI.md`. Se a tarefa esbarrar em um desses pontos:

- Sinalizar explicitamente que a mudança altera esse comportamento — não misturar a correção dentro de uma mudança descrita como "outra coisa".
- Descrever o que muda em caso de falha no meio da execução (ex.: hoje, se a carga falhar no meio, o painel fica sem base vigente — uma mudança que resolve isso muda esse comportamento de forma que vale a pena destacar separadamente).

## 6. Documentar e versionar

- Atualizar a seção do objeto em `docs/` usando a mesma estrutura já estabelecida (Resumo, Fluxo de execução, Entradas, Saídas, Regras de negócio, Cálculos, Dependências, Objetos chamados, Pontos críticos, Sugestões de melhoria, Resumo executivo).
- Adicionar uma entrada datada no "LOG DE PROGRESSO" (`docs/REVISAO_TECNICA_STACK_MARGEM_BI.md`) distinguindo `✅ Confirmado` de `⚠️ Pendência`.
- Colocar o `.sql` correspondente em `sql/procedures/` ou `sql/views/` com o nome exato do objeto Oracle.
- Seguir a convenção de commit do projeto: `tipo(#N): descrição`. Não commitar — quem commita é o usuário.

## 7. Automação nova (scripts/pipelines, incluindo futuro GCP)

Para automação que ainda não existe (não é mudança num objeto já documentado):

- Aplicar as seções 1–6 do mesmo jeito, tratando o novo script como se já fosse parte da stack: documentar de onde ele lê, o que escreve, e o que consome o que ele produz.
- Se for parte do futuro pipeline GCP (Dataflow/BigQuery/Looker Studio Pro da proposta Multiedro), confirmar primeiro com o usuário se o projeto já foi contratado — não assumir que a infraestrutura existe só porque está descrita no `CLAUDE.md`.
- Nunca dar uma automação como pronta pra rodar contra dado de produção sem o mesmo passo de reconciliação da seção 4.