# Changelog

Log de progresso datado do trabalho neste repositório. Cada entrada distingue deliberadamente `✅ Confirmado` (medido/evidenciado) de `⚠️ Pendência` (ainda não verificado) — nunca promover uma pendência a confirmado sem medição real. Ver `CONTRIBUTING.md` (Regra de ouro) para o porquê dessa distinção ser obrigatória.

Ordem: mais recente primeiro.

## 07/07/2026 (rodada 2) — Rastreamento de dependências (views de quantidade/devolução/financeiro)

Continuação da rodada 1: trazer e documentar o grupo 🟠 (views de quantidade/devolução e financeiro) listado na Seção Final de `docs/STACK_MARGEM_BI.md`.

### ✅ Confirmado (trazido e documentado) — 9 de 10 views do grupo 🟠

`VW_BMC_GET_QTD_DEV_VENDA`, `VW_BMC_GET_QTD_DEV_VENDA_FOR`, `VW_BMC_GET_QTD_DEV_VENDA2`, `VW_ARG_DEB_CRE_ITE`, `VW_ARG_CRE_DEB`, `VW_DESCFIN`, `VW_PERCPROC_NF_V4`, `VW_TGFCAB_ITE`, `VW_TGFPARC_TGFEMP` — corpo real trazido do DBExplorer e documentado com seção completa de 13 partes (Objetos 18 a 26). Referências cruzadas em `VW_NOTAS_31` (Objeto 3) atualizadas de `[EXTERNO]` para `✔ Sim`.

### ⚠️ Pendências abertas (não tratar como concluído)

- `VW_AD_REC_COMD` — não trazida. O DBExplorer dá erro consistente ao abrir esta view especificamente ("Cannot read properties of undefined (reading 'colunas')"), reproduzido em 2 tentativas. `[VALIDAR]` confirmar no Oracle (`SELECT status FROM all_objects WHERE object_name = 'VW_AD_REC_COMD'`) se o objeto está inválido de fato, ou se é um bug pontual da ferramenta.
- `[VALIDAR]` `VW_DESCFIN` (Objeto 23) tem um corte de regra por data (`DTNEG < '2026-01-01'` vs. `>= '2026-01-01'`) que muda a fonte de rateio do desconto financeiro (de `VLRNOTA` fixo para soma viva de itens não devolvidos) — **já em vigor** para todas as notas do ano corrente, sem reconciliação registrada entre os dois braços.
- `[VALIDAR]` `VW_ARG_DEB_CRE_ITE` (Objeto 21) trata a condição de "débito válido" de forma assimétrica entre o branch por controle (CT) e o branch por calibre (CL) — não confirmado se é intencional.
- `[VALIDAR]` `VW_TGFPARC_TGFEMP` (Objeto 26) exclui um CGC específico (27185579821) hardcoded sem explicação de qual empresa é.
- Descobertas variações não previstas na lista original, ainda não trazidas: `VW_BMC_GET_QTD_DEV_VENDA_ROM`, `VW_ARG_CRE_DEB_BAIXA`, `VW_ARG_CRE_DEB_NOVA`, `VW_ARG_CRE_DEB1`, `VW_DESCFIN_V2`.

### ➡️ Próximo passo recomendado

Confirmar no Oracle o status de `VW_AD_REC_COMD`. Depois, seguir para o restante do grupo 🟠 (materialized views `VW_M_CUSTOMED_SEMANA`/`VW_M_NFVENDAS_DEVINT`/`VW_M_CONTROLE_VLRMP`) ou grupo 🟡, listados na Seção Final de `docs/STACK_MARGEM_BI.md`.

## 07/07/2026 (rodada 1) — Rastreamento de dependências (functions + views de custo)

Rodada de rastreamento de dependências (não é otimização de performance): trazer e documentar objetos `[EXTERNO]` que a V9 chama, listados na Seção Final de `docs/STACK_MARGEM_BI.md`.

### ✅ Confirmado (trazido e documentado) — grupo 🔴 completo

- 5 views de custo/frete/portuária/provisão: `VW_BMC_BI_CUSTOS_PROD_OTM` (a mais crítica — ficha de custo por pallet), `VW_BMC_BI_PERCA_PACK`, `VW_BMC_FRETE_MARITIMO`, `VW_BMC_DESPESAS_PORTUARIAS`, `VW_BMC_BI_PROV_FORNECEDORES` — corpo real trazido do DBExplorer (Sankhya Om) e documentado com seção completa de 13 partes em `docs/STACK_MARGEM_BI.md` (Objetos 13 a 17).
- 9 das 9 functions de cálculo documentadas com seção completa de 13 partes (Objetos 4 a 12): `FU_BMC_GETPROVFORN`, `FU_BMC_GETROYALTIES`, `FU_BMC_GETCOMVENDA`, `FU_BMC_GETPERCCOMVENDA`, `FU_BMC_GETCUSTOPREVISTO`, `FU_BMC_PRECO_CUSTO_GER`, `FU_ARG_TXADM_CUSTO_GER`, `FUN_ARG_VLRETIQSRV`, `FUN_ARG_VLRETIQ`.
- `FU_BMC_PRECO_CUSTO_GER` — corpo corrigido: o arquivo original continha, por engano, o corpo de `FU_BMC_GETCUSTOPREVISTO` (copy/paste errado ao extrair do DBExplorer). Recopiado direto do Sankhya (Functions → FU_BMC_PRECO_CUSTO_GER) e confirmado: é irmã de `FU_ARG_TXADM_CUSTO_GER`, mesma tabela de config (`AD_CUSTOGER`/`AD_CUSTOGERITE`), retorna `PRECO` em vez de `TXADM`.
- Padronizado `sql/procedures/README.md` e `sql/views/README.md` (e criado `sql/functions/README.md`) com a mesma lista de 13 seções obrigatórias, na mesma ordem — antes cada um citava uma lista diferente (ou nenhuma).
- Corrigidas referências cruzadas desatualizadas: `VW_NOTAS_31` (Objeto 3) ainda marcava `VW_BMC_BI_PROV_FORNECEDORES` como `[EXTERNO]` em 3 lugares (tabela de dependências, "Objetos chamados", diagrama) — atualizado para `✔ Sim (Objeto 17)`.
- Reestruturação de documentação para padrão de repositório: criados `README.md`, `ARCHITECTURE.md`, `CONTRIBUTING.md`, `CHANGELOG.md` (este arquivo) e `docs/adr/`. `CLAUDE.md` retirado (conteúdo redistribuído nesses arquivos) — ver `docs/adr/0003-remover-claude-md-e-mover-skills-para-raiz.md`.
- Movido `.claude/skills/bi-impact-check/` → `skills/bi-impact-check/` (raiz do repo, visível/versionado para o time).
- Criado skill `skills/trazer-documentar-objeto/` documentando o fluxo de trazer e documentar um objeto Sankhya (baseado no processo real desta rodada).

### ⚠️ Pendências abertas (não tratar como concluído)

- `obtemcusto4` (function utilitária padrão Sankhya, chamada por `FUN_ARG_VLRETIQ` e por `VW_BMC_BI_CUSTOS_PROD_OTM`) e `FU_BMC_GETPRECOENTRADA` (chamada por `VW_BMC_BI_CUSTOS_PROD_OTM`) — identificadas como dependências `[EXTERNO]` durante a documentação; corpo não trazido, comportamento é caixa-preta parcial no cálculo de custo de etiqueta e de ficha de custo.
- `[VALIDAR]` `VW_BMC_FRETE_MARITIMO` aplica o rateio de `TGFRAT` sempre (incondicional); `VW_BMC_DESPESAS_PORTUARIAS` só aplica quando o item não tem projeto próprio (condicional). Não está confirmado se essa diferença entre as duas views irmãs é intencional ou uma divergência não documentada — ver Objetos 15 e 16 de `docs/STACK_MARGEM_BI.md`, Pontos críticos.
- `[VALIDAR]` Relação entre `VW_BMC_BI_PROV_FORNECEDORES` (provisão "lançada"/contábil, lote 34 de `TCBLAN`) e `FU_BMC_GETPROVFORN` (provisão "calculada"/automática) não está clara — não é óbvio pela V9 já documentada se uma fonte substitui a outra ou se são somadas. Precisa confirmar com quem manteve a V9.
- `[VALIDAR]` Possível inconsistência de nome: `VW_BMC_GETPRECOENTRADA` (Objeto 1, tratada como view) vs. `FU_BMC_GETPRECOENTRADA` (chamada como function dentro de `VW_BMC_BI_CUSTOS_PROD_OTM`) — ver Objeto 13, Pontos críticos.

### ➡️ Próximo passo recomendado

Esclarecer os pontos `[VALIDAR]` acima com o time funcional (rateio condicional vs. incondicional; relação entre as duas fontes de provisão de fornecedor) antes de qualquer otimização que mexa nessas views. Para trazer mais objetos, seguir para o grupo 🟠 (views de quantidade/devolução/financeiro) listado na Seção Final de `docs/STACK_MARGEM_BI.md`.

## 05/07/2026 — Diagnóstico de gargalo + refatoração de VW_NOTAS_31

Registro do que foi diagnosticado e executado nesta rodada de otimização.

### ✅ Confirmado (medido / evidenciado)

Diagnóstico do gargalo (via `v$sql`, `elapsed_time` por SQL na carga):
- Carga completa `STP_BMC_CARGA_MRG_BI_BASE` ≈ 30 min.
- `SELECT ... FROM VW_BMC_BI_BASE_ITENS_V9` (cursor da carga) ≈ 1.008 s (~17 min ≈ 57% da carga) — é o gargalo real.
- `STP_ARG_PROCESS_AD_TGFITECOMPL` (INSERT em `AD_TGFITECOMPL`, ~69 execuções) ≈ 7 min.
- `SELECT ... FROM VW_NOTAS_31` isolada ≈ 3–3,5 min (~10% da carga).
- Índice `IX_TGFCAB_AD_NUNOTASUB` criado e em uso — confirmado nos planos de execução (anti-joins de `TGFCAB.AD_NUNOTASUB` e `AD_NOTASEXC` agora por índice, sem FULL SCAN).
- Colisão de alias Q3/Q4/Q5 — corrigida e validada contra produção (rodada anterior).
- `VW_NOTAS_31` refatorada (versão `_2`, 05/07): MATERIALIZE reposto em 17 CTEs (estabiliza o plano — havia spill de TEMP de 150–270 MB quando removido). Novas CTEs: `PDESC`, `DEV_ITEM`, `DEV_NOTA`.

### ⚠️ Pendências abertas (não tratar como concluído)

- Ganho de tempo da `VW_NOTAS_31` pós-refatoração: não medido. Falta cronometrar a carga completa. Planos coletados foram de `COUNT(*)` (poda colunas/joins) — não refletem a carga real. Sabe-se que a V9 compila mais rápido (parse), mas isso ≠ execução mais rápida.
- A versão `_2` introduziu **mudanças funcionais** (não é só performance) — reconciliação agora é obrigatória:
  - `PERCDESCCONTRATUAL` mudou de fonte: agora vem da CTE `PDESC` (`AD_CTRLDESCOM`, desconto contratual mais recente por cliente via `ROW_NUMBER`, casado por `DHALTER<=DTNEG` e `RN=1`). Valor pode diferir da fonte anterior.
  - Nova coluna `VLR_DESC_FIN_SDEV` (desconto financeiro líquido de devolução por nota) — cálculo que usa a nova CTE `DEV_NOTA` e `PARCLI.DESCFIN`.
  - `DEV_ITEM`/`DEV_NOTA` filtram devolução por `TIPMOV='D' AND STATUSNOTA='L'` (só notas de devolução liquidadas).
  - Sobre REFUGO/`TIPMOV='V'` (esclarecido antes): a `DEV_ITEM` dispensa REFUGO porque a distinção vem de `VW_BMC_GET_QTD_DEV_VENDA2` (mantida); `TIPMOV='V'` no `QTDNEG_POR_NUNOTA` é redundante com a query principal. Esses dois são neutros.
  - Ação obrigatória antes de publicar: reconciliar por ANO/SEMANA/FRUTA (nova × produção): `QTDNEGNOTA`, `VLRTOTNOTA`, `QTDDEVVENDA`, `PERCDESCCONTRATUAL` e o total de `VLR_DESC_COM` (que a V9 usa como dedução de receita). Como `PERCDESCCONTRATUAL` alimenta desconto → alimenta margem, essa não é opcional.
- Reescrita da V9 (alavanca 4.a): não iniciada. É onde estão os ~17 min. Depende de: (a) ambiente de homologação, ou (b) deploy paralelo (`_V10`).

### ➡️ Próximo passo recomendado

Congelar a `VW_NOTAS_31` (com MATERIALIZE repostos), rodar a reconciliação da pendência acima uma vez, e mover o foco para a reescrita da V9 — único item que ataca a maior fatia dos 30 min.
