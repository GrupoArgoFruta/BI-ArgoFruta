# 0002 — Refatorar VW_NOTAS_31 (rev. 3) com MATERIALIZE e novas CTEs de devolução

## Status

Aceito, com pendência de reconciliação (ver `CHANGELOG.md`, 05/07/2026).

## Contexto

A carga completa (`STP_BMC_CARGA_MRG_BI_BASE`) leva ~30 min, dos quais a `VW_BMC_BI_BASE_ITENS_V9` já é o maior gargalo (~57%). Ao investigar `VW_NOTAS_31` (fonte base da V9), foi identificado spill de TEMP de 150–270 MB quando o hint `/*+ MATERIALIZE */` era removido de suas CTEs — o otimizador perdia um plano estável. Paralelamente, a lógica de desconto contratual (`PERCDESCCONTRATUAL`) e de desconto financeiro líquido de devolução precisava ser revisada.

## Decisão

Repor `/*+ MATERIALIZE */` em 17 CTEs de `VW_NOTAS_31` (versão `_2`) para estabilizar o plano de execução, e adicionar duas CTEs novas: `DEV_ITEM` (devolução por item) e `DEV_NOTA` (devolução por nota), ambas filtrando `TIPMOV='D' AND STATUSNOTA='L'` (só notas de devolução liquidadas). Como parte dessa mudança, `PERCDESCCONTRATUAL` passou a vir da nova CTE `PDESC` (baseada em `AD_CTRLDESCOM`) em vez da fonte anterior, e uma nova coluna `VLR_DESC_FIN_SDEV` foi adicionada.

## Consequências

- **Positivo (confirmado):** plano de execução estabilizado — sem spill de TEMP.
- **Positivo, não medido ainda:** ganho de tempo de execução da carga completa — só foi medido em queries de `COUNT(*)` (poda colunas/joins), que não refletem a carga real.
- **Mudança funcional (não é só performance) — reconciliação obrigatória antes de considerar concluído:** `PERCDESCCONTRATUAL` pode divergir da fonte anterior; `VLR_DESC_FIN_SDEV` é coluna nova. Ação pendente: reconciliar por ANO/SEMANA/FRUTA (nova × produção) `QTDNEGNOTA`, `VLRTOTNOTA`, `QTDDEVVENDA`, `PERCDESCCONTRATUAL` e o total de `VLR_DESC_COM`. Como `PERCDESCCONTRATUAL` alimenta desconto → alimenta margem, essa reconciliação não é opcional (regra de ouro do `CONTRIBUTING.md`).
- **Pendência maior ainda não atacada:** a reescrita da própria `VW_BMC_BI_BASE_ITENS_V9` (onde estão os ~17 min do gargalo real) depende de ambiente de homologação ou deploy paralelo (`_V10`) — não iniciada.
