# Riscos Abertos — Stack de Margem BI

Este documento não introduz nenhum risco novo — é uma consolidação de todo `[VALIDAR]` e ponto crítico já registrado, hoje espalhado por `ARCHITECTURE.md`, `CHANGELOG.md`, `docs/STACK_MARGEM_BI.md` (26 seções) e `docs/REVISAO_TECNICA_STACK_MARGEM_BI.md`. Objetivo: responder "o que está em aberto hoje?" sem precisar ler ~2.000 linhas.

**Não é atualizado automaticamente.** Sempre que uma linha abaixo for resolvida (reconciliada, confirmada, ou a mudança aplicada com equivalência provada), marcar aqui **e** no local de origem — e mover para "Resolvidos" no fim do arquivo, com a data e o resultado (mesma disciplina de `✅ Confirmado` do `CHANGELOG.md`).

Prioridade é **impacto se a suposição estiver errada**, não esforço de correção:

- 🔴 **Alta** — pode já estar distorcendo margem/desconto hoje, em produção, sem reconciliação registrada.
- 🟠 **Média** — valor/código mágico ou regra sem de-para; quebra **silenciosamente** se o cadastro de origem mudar.
- 🟡 **Baixa** — rastreabilidade incompleta, naming, ou robustez (não afeta o número hoje).

## A. Comportamento já em produção com ambiguidade ou divergência não confirmada

| ID | Objeto(s) | Risco | Fonte |
|---|---|---|---|
| R01 | `VW_NOTAS_31` (Objeto 3) | `ADR-0002` e `CHANGELOG` (05/07/2026) descrevem `PERCDESCCONTRATUAL` vindo de uma CTE nova `PDESC` (`AD_CTRLDESCOM`) — mas `sql/views/VW_NOTAS_31.txt` não tem `PDESC`, `DEV_NOTA`, `AD_CTRLDESCOM` nem `ROW_NUMBER`. `PERCDESCCONTRATUAL` ali ainda é `COALESCE(PARCLI.DESCFIN,0)`, a fonte pré-rev.3. Não confirmado se o `.txt` ficou desatualizado, se a mudança nunca foi aplicada no Oracle, ou se foi revertida. | `docs/FLUXOS.md` (achado #2), `ADR-0002`, `CHANGELOG.md` L.05/07 |
| R02 🔴 | `VW_DESCFIN` (Objeto 23) | Corte de regra por data (`DTNEG < '2026-01-01'` vs. `>=`) muda a fonte de rateio do desconto financeiro (de `VLRNOTA` fixo para soma viva de itens não devolvidos) — **já em vigor** para todas as notas do ano corrente, sem reconciliação registrada entre os dois braços. | `STACK_MARGEM_BI.md` Objeto 23; `CHANGELOG.md` rodada 07/07 |
| R03 🔴 | `VW_BMC_FRETE_MARITIMO` (15) × `VW_BMC_DESPESAS_PORTUARIAS` (16) | Duas views "irmãs" de mesmo padrão estrutural, mas o rateio de `TGFRAT` é incondicional numa e condicional (só quando o item não tem projeto próprio) na outra. Não confirmado se é intencional ou divergência não documentada — se for bug de uma delas, a correção muda margem. | `STACK_MARGEM_BI.md` Objetos 15 e 16; `CHANGELOG.md` rodada 07/07 |
| R04 🔴 | `VW_BMC_BI_PROV_FORNECEDORES` (17) × `FU_BMC_GETPROVFORN` (4) | Duas fontes de provisão de fornecedor na V9: uma "lançada"/contábil (lote 34 de `TCBLAN`), outra "calculada"/automática. Não está claro pela V9 já documentada se uma substitui a outra ou se são somadas — precisa confirmar com quem manteve a V9. | `STACK_MARGEM_BI.md` Objeto 17; `CHANGELOG.md` rodada 07/07 |
| R05 🟠 | `VW_ARG_DEB_CRE_ITE` (21) | Condição de "débito válido" assimétrica entre o branch por controle (`CT`, só `STATUSNFE='A'`) e o branch por calibre (`CL`, também aceita `CODTIPOPER=2235`). Não confirmado se é intencional. | `STACK_MARGEM_BI.md` Objeto 21; `CHANGELOG.md` rodada 07/07 |

## B. Valores/códigos mágicos sem tabela de-para (risco de quebra silenciosa)

| ID | Objeto | Risco |
|---|---|---|
| R06 🟠 | `VW_BMC_BI_PERCA_PACK` (14) | `CODTIPOPER=500` e `CODNAT LIKE '212%'` sem de-para documentado — se o cadastro de tipo de operação/natureza mudar, a view para de capturar perda de pack sem lançar erro (resultado só fica vazio/incompleto). |
| R07 🟠 | `VW_TGFPARC_TGFEMP` (26), usada por `VW_ARG_CRE_DEB` (22) | `EMP.CGC<>27185579821` exclui uma empresa específica do grupo sem explicar qual é nem por quê. Se essa empresa for renumerada no cadastro, a exclusão para de funcionar silenciosamente. |
| R08 🟠 | `VW_ARG_CRE_DEB` (22) | Lista de códigos de tipo de operação de baixa (`1404/1408/1407/1400/1502/1501/1308/1500`) + filtro de texto `NOT LIKE '%substituição de portador%'` são valores mágicos sem de-para. |
| R09 🟠 | `VW_PERCPROC_NF_V4` (24) | Faixa de código de projeto `4.000.000.000–4.999.999.999` hardcoded como identificador de "processo" — muda de convenção, a view para de capturar processos silenciosamente. |
| R10 🟡 | `VW_BMC_BI_PROV_FORNECEDORES` (17) | `NUMLOTE=34` hardcoded sem de-para. |
| R11 🟡 | `FU_BMC_GETPROVFORN` (4) | `CASE` de 24 níveis de priorização — candidato a virar coluna pré-calculada em `AD_CONFPROVFORNREG`, mas é mudança estrutural: precisa validar que a ordenação resultante é idêntica para todo o histórico. |

## C. Rastreabilidade incompleta / nomenclatura

| ID | Objeto | Pendência |
|---|---|---|
| R12 🟠 | `obtemcusto4`, `FU_BMC_GETPRECOENTRADA` (chamadas por `VW_BMC_BI_CUSTOS_PROD_OTM` e `FUN_ARG_VLRETIQ`) | Corpo ainda não trazido para `sql/` — caixa-preta parcial no cálculo de custo de ficha/etiqueta. |
| R13 🟡 | `VW_BMC_GETPRECOENTRADA` (tratada como view no Objeto 1) × `FU_BMC_GETPRECOENTRADA` (chamada como function dentro do Objeto 13) | Possível inconsistência de nome — não confirmado se é o mesmo objeto ou dois distintos. |
| R14 🟡 | `VW_AD_REC_COMD` | Erro consistente no DBExplorer ao abrir ("Cannot read properties of undefined (reading 'colunas')"), reproduzido 2×. Não confirmado se é bug da ferramenta ou objeto inválido no Oracle (`SELECT status FROM all_objects WHERE object_name='VW_AD_REC_COMD'` resolveria). Enquanto isso, `OPEN_AMOUNT` de `VW_NOTAS_31` fica `[EXTERNO]`. |
| R15 🟡 | `VW_BMC_GET_QTD_DEV_VENDA` (18) | Bloco `UNION ALL` comentado sugere uma segunda fonte de devolução (`CODTIPOPER` 2126/2127) com lista de exclusão manual, hoje desativada — não documentado por quê nem se a lista ainda é válida. |
| R16 🟡 | `FUN_ARG_VLRETIQSRV` (10) / `FUN_ARG_VLRETIQ` (11) | `WHEN OTHERS RETURN NULL` mascara erro de dado (hoje `NULL` vira `0` na V9). Trocar por log é melhoria, mas precisa confirmar que nada depende do silêncio atual. |

## D. Otimizações propostas em `REVISAO_TECNICA` — nenhuma aplicada ainda

Nada aqui está em produção. Listado para não perder o fio quando alguém retomar a otimização da V9 (o item de maior gargalo do stack, ~57% da carga).

| ID | Mudança proposta | Prioridade (matriz Etapa 11) | Risco a validar antes de aplicar |
|---|---|---|---|
| R17 | V9: subconsultas correlacionadas contra `VW_BMC_BI_CUSTOS_PROD_OTM` → join agregado único por pallet | Crítica | Semântica de `MAX` vs `SUM`/qtd precisa bater 1:1 em pallets com múltiplas flags |
| R18 | V9: consolidar `CUSTOTOTALGER`/`MARGEMGER`/`PERCMARGEMGER`/`PROVISAO_FORNECEDOR_GER` num único nível (hoje calculados 2× — N2 e projeção externa, ponto crítico #1 do Objeto 2) | Alta | Confirmar que a camada externa é de fato a única consumida a jusante |
| R19 | Procedure principal: cursor+`BULK COLLECT`/`FORALL` → `INSERT /*+ APPEND */ SELECT` | Alta | Só equivale se não houver leitor concorrente esperando ver a versão anterior durante a recarga — senão manter blue-green sem truncate |
| R20 | V9: blindar `TO_NUMBER(nropallet)` com o padrão `REGEXP_LIKE` já usado em `VW_NOTAS_31` | Baixa | Muda comportamento só em dado não-numérico (hoje erro → depois `0`/`NULL`) |
| R21 | Fundir `FU_ARG_TXADM_CUSTO_GER` + `FU_BMC_PRECO_CUSTO_GER` numa function parametrizada | Baixa | Mantém retorno idêntico; dois objetos passam a depender de um — testar ambos |
| R22 | Unificar as 3 views de devolução (`VW_BMC_GET_QTD_DEV_VENDA` / `_FOR` / `_2`) | Baixa | Mudança estrutural — levantar todos os call sites antes |
| R23 | `obtemcusto4` deveria tratar `NO_DATA_FOUND` internamente | Baixa | Hoje o erro pode estar sendo mascarado a montante — confirmar antes de mudar o tratamento |

## Resolvidos (histórico — mantido para não perder o antes/depois)

| ID | Objeto | Resolução |
|---|---|---|
| — | `VW_NOTAS_31` — colisão de alias Q3/Q4/Q5 | ✅ Corrigida e validada contra produção (`ADR-0001`). Era o item nº 1 de risco do stack. |

---

Fonte de cada linha: `docs/STACK_MARGEM_BI.md` (Objetos 1–26, seções "Pontos críticos"/"Sugestões de melhoria"), `docs/REVISAO_TECNICA_STACK_MARGEM_BI.md` (Etapas 4, 11 e 12), `ARCHITECTURE.md` ("Pontos críticos conhecidos"), `CHANGELOG.md` e `docs/FLUXOS.md`. Em caso de dúvida sobre um item, ler a seção original — este documento resume, não substitui.
