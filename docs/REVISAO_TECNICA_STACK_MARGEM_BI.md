# Revisão Técnica & Otimização — Stack de Margem BI (Argofruta / Sankhya)

Escopo: STP_BMC_CARGA_MRG_BI_BASE, VW_BMC_BI_BASE_ITENS_V9, VW_NOTAS_31, VW_BMC_BI_CUSTOS_PROD_OTM, STP_ARG_PROCESS_AD_TGFITECOMPL e o cluster de funções FU_*/FUN_*. Views de projeção simples entram numa revisão consolidada.

Regra de ouro (etapa 12 do prompt): toda proposta abaixo visa resultado idêntico para qualquer conjunto de dados. Onde a equivalência não é 100% garantível apenas pelo texto, a mudança é marcada [VALIDAR] e descrevo o risco em vez de recomendar cegamente.

## LOG DE PROGRESSO — 05/07/2026
Registro do que foi diagnosticado e executado nesta rodada de otimização. Distinção deliberada entre o que está confirmado por medição e o que ainda é pendência — para não registrar como concluído aquilo que não foi verificado.
✅ Confirmado (medido / evidenciado)
Diagnóstico do gargalo (via v$sql, elapsed_time por SQL na carga):
Carga completa STP_BMC_CARGA_MRG_BI_BASE ≈ 30 min.
SELECT ... FROM VW_BMC_BI_BASE_ITENS_V9 (cursor da carga) ≈ 1.008 s (~17 min ≈ 57% da carga) — é o gargalo real.
STP_ARG_PROCESS_AD_TGFITECOMPL (INSERT em AD_TGFITECOMPL, ~69 execuções) ≈ 7 min.
SELECT ... FROM VW_NOTAS_31 isolada ≈ 3–3,5 min (~10% da carga).
Índice IX_TGFCAB_AD_NUNOTASUB criado e em uso — confirmado nos planos de execução (anti-joins de TGFCAB.AD_NUNOTASUB e AD_NOTASEXC agora por índice, sem FULL SCAN).
Colisão de alias Q3/Q4/Q5 — corrigida e validada contra produção (rodada anterior).
VW_NOTAS_31 refatorada (versão _2, 05/07): ver detalhamento na pendência 2 abaixo. MATERIALIZE reposto em 17 CTEs (estabiliza o plano — havia spill de TEMP de 150–270 MB quando removido). Novas CTEs: PDESC, DEV_ITEM, DEV_NOTA.
⚠️ Pendências abertas (não tratar como concluído)
Ganho de tempo da VW_NOTAS_31 pós-refatoração: não medido. Falta cronometrar a carga completa. Planos coletados foram de COUNT(*) (poda colunas/joins) — não refletem a carga real. Sabe-se que a V9 compila mais rápido (parse), mas isso ≠ execução mais rápida.
⚠️ A versão _2 introduziu MUDANÇAS FUNCIONAIS (não é só performance) — reconciliação agora é OBRIGATÓRIA:
PERCDESCCONTRATUAL mudou de fonte: agora vem da CTE PDESC (AD_CTRLDESCOM, desconto contratual mais recente por cliente via ROW_NUMBER, casado por DHALTER<=DTNEG e RN=1). Valor pode diferir da fonte anterior.
Nova coluna VLR_DESC_FIN_SDEV (desconto financeiro líquido de devolução por nota) — cálculo que usa a nova CTE DEV_NOTA e PARCLI.DESCFIN.
DEV_ITEM/DEV_NOTA filtram devolução por TIPMOV='D' AND STATUSNOTA='L' (só notas de devolução liquidadas).
Sobre REFUGO/TIPMOV='V' (esclarecido antes): a DEV_ITEM dispensa REFUGO porque a distinção vem de VW_BMC_GET_QTD_DEV_VENDA2 (mantida); TIPMOV='V' no QTDNEG_POR_NUNOTA é redundante com a query principal. Esses dois são neutros.
Ação obrigatória antes de publicar: reconciliar por ANO/SEMANA/FRUTA (nova × produção): QTDNEGNOTA, VLRTOTNOTA, QTDDEVVENDA, PERCDESCCONTRATUAL e o total de VLR_DESC_COM (que a V9 usa como dedução de receita). Como PERCDESCCONTRATUAL alimenta desconto → alimenta margem, essa não é opcional.
Reescrita da V9 (alavanca 4.a): não iniciada. É onde estão os ~17 min. Depende de: (a) ambiente de homologação, ou (b) deploy paralelo (_V10).
➡️ Próximo passo recomendado
Congelar a VW_NOTAS_31 (com MATERIALIZE repostos), rodar a reconciliação da pendência 2 uma vez, e mover o foco para a reescrita da V9 — único item que ataca a maior fatia dos 30 min.

## LOG DE PROGRESSO — 07/07/2026
Rodada de rastreamento de dependências (não é otimização de performance): trazer e documentar objetos [EXTERNO] que a V9 chama, listados na Seção Final de docs/STACK_MARGEM_BI.md.
✅ Confirmado (trazido e documentado) — grupo 🔴 completo
5 views de custo/frete/portuária/provisão: VW_BMC_BI_CUSTOS_PROD_OTM (a mais crítica — ficha de custo por pallet), VW_BMC_BI_PERCA_PACK, VW_BMC_FRETE_MARITIMO, VW_BMC_DESPESAS_PORTUARIAS, VW_BMC_BI_PROV_FORNECEDORES — corpo real trazido do DBExplorer (Sankhya Om) e documentado com seção completa de 13 partes em docs/STACK_MARGEM_BI.md (Objetos 13 a 17).
9 das 9 functions de cálculo documentadas com seção completa de 13 partes (Objetos 4 a 12): FU_BMC_GETPROVFORN, FU_BMC_GETROYALTIES, FU_BMC_GETCOMVENDA, FU_BMC_GETPERCCOMVENDA, FU_BMC_GETCUSTOPREVISTO, FU_BMC_PRECO_CUSTO_GER, FU_ARG_TXADM_CUSTO_GER, FUN_ARG_VLRETIQSRV, FUN_ARG_VLRETIQ.
FU_BMC_PRECO_CUSTO_GER — corpo corrigido: o arquivo original continha, por engano, o corpo de FU_BMC_GETCUSTOPREVISTO (copy/paste errado ao extrair do DBExplorer). Recopiado direto do Sankhya (Functions → FU_BMC_PRECO_CUSTO_GER) e confirmado: é irmã de FU_ARG_TXADM_CUSTO_GER, mesma tabela de config (AD_CUSTOGER/AD_CUSTOGERITE), retorna PRECO em vez de TXADM.
Padronizado sql/procedures/README.md e sql/views/README.md (e criado sql/functions/README.md) com a mesma lista de 13 seções obrigatórias, na mesma ordem — antes cada um citava uma lista diferente (ou nenhuma).
⚠️ Pendências abertas (não tratar como concluído)
obtemcusto4 (function utilitária padrão Sankhya, chamada por FUN_ARG_VLRETIQ e por VW_BMC_BI_CUSTOS_PROD_OTM) e FU_BMC_GETPRECOENTRADA (chamada por VW_BMC_BI_CUSTOS_PROD_OTM) — identificadas como dependências [EXTERNO] durante a documentação; corpo não trazido, comportamento é caixa-preta parcial no cálculo de custo de etiqueta e de ficha de custo.
[VALIDAR] VW_BMC_FRETE_MARITIMO aplica o rateio de TGFRAT sempre (incondicional); VW_BMC_DESPESAS_PORTUARIAS só aplica quando o item não tem projeto próprio (condicional). Não está confirmado se essa diferença entre as duas views irmãs é intencional ou uma divergência não documentada — ver Objetos 15 e 16, Pontos críticos.
[VALIDAR] Relação entre VW_BMC_BI_PROV_FORNECEDORES (provisão "lançada"/contábil, lote 34 de TCBLAN) e FU_BMC_GETPROVFORN (provisão "calculada"/automática) não está clara — não é óbvio pela V9 já documentada se uma fonte substitui a outra ou se são somadas. Precisa confirmar com quem manteve a V9.
➡️ Próximo passo recomendado
Esclarecer os 2 pontos [VALIDAR] acima com o time funcional (rateio condicional vs. incondicional; relação entre as duas fontes de provisão de fornecedor) antes de qualquer otimização que mexa nessas views. Para trazer mais objetos, seguir para o grupo 🟠 (views de quantidade/devolução/financeiro) listado na Seção Final de docs/STACK_MARGEM_BI.md.

Limitações desta análise (importante):

Índices: dicionário real disponível (dump de all_ind_columns, rev. deste documento). As seções 3 (Índices) foram validadas contra o dicionário — os índices existentes estão marcados como fato; apenas o que ainda falta criar aparece como recomendação.
Ainda não tenho EXPLAIN PLAN, estatísticas (DBA_TAB_STATISTICS) nem uso de segmento. Então a seção 9 (Plano de Execução) segue inferida do SQL — a existência do índice não garante que o otimizador o use (depende de cardinalidade/estatísticas).
Ganhos são qualitativos (baixo / médio / alto). Não invento percentuais.

SUMÁRIO EXECUTIVO (leia isto primeiro)
As três alavancas que valem mais do que todo o resto somado:

Eliminar as ~8 subconsultas correlacionadas por item contra VW_BMC_BI_CUSTOS_PROD_OTM (dentro da V9), trocando por um único join agregado por pallet. Ganho: alto. Risco: médio [VALIDAR].
Consolidar CUSTOTOTALGER/MARGEMGER/PERCMARGEMGER/PROVISAO_FORNECEDOR_GER num único nível na V9 (hoje calculados 2×). Ganho: médio-alto (CPU + risco de divergência). Risco: médio [VALIDAR].
Trocar o cursor + BULK COLLECT/FORALL da procedure principal por INSERT /*+ APPEND */ ... SELECT. Ganho: médio-alto. Risco: baixo.

E um item que é correção, não otimização, mas bloqueia tudo:

✅ Colisão de alias Q3/Q4/Q5 em VW_NOTAS_31 — CORRIGIDA E VALIDADA. CTEs renomeados para nomes semânticos, equivalência confirmada contra produção. Destravado — a otimização da V9 já pode prosseguir sobre uma base confiável.

A matriz de priorização completa está na Etapa 11.

Índices — verificados contra o dicionário. O stack está bem indexado (há uma família *_BMC_0x desenhada para ele). Das recomendações de índice do relatório, praticamente todas já existem (incluindo AD_NOTASEXC, AD_TGFITECOMPL_FILA(REQUESTED_AT), AD_BMCPRECOENTRADA, AD_CUSTOSPREV, TGFCUS, pallets). Sobra uma única ação: criar ix_tgfcab_ad_nunotasub (a coluna TGFCAB.AD_NUNOTASUB do anti-join não tem índice). Detalhe por objeto nas seções 3.

## OBJETO 1 — VW_NOTAS_31
### 1. Análise geral
Objetivo: base de itens de venda com quantidades líquidas de devolução e rateios de crédito/débito, frete e desconto.
Complexidade: muito alta (13 CTEs, ~40 joins, anti-joins, joins por expressão calculada).
Pontos fortes: uso consistente de /*+ MATERIALIZE */ nas CTEs de quantidade; pré-cálculo de ROMANEIO_NUM na CTE ITE_BASE (elimina REGEXP_LIKE/TO_NUMBER repetidos nos joins — refatoração correta e valiosa); centralização das quantidades líquidas.
Pontos fracos (remanescentes): joins por expressão (TO_CHAR(...,'IW-YYYY')); anti-joins múltiplos; duplicação do CASE de PROCESSO. (Já resolvidos: colisão de alias, código morto; datas agora em literal ANSI.)
Risco de manutenção: alto — qualquer alteração exige reteste amplo.
### 2. Performance
| Achado | Impacto | Motivo | Ganho esperado |
|---|---|---|---|
| Anti-joins NOT EXISTS ×4 (AD_NOTASEXC 2×, VW_TGFPARC_TGFEMP, tgfcab.AD_NUNOTASUB) | Médio | 3 dos 4 já têm índice; só TGFCAB.AD_NUNOTASUB faz FULL SCAN por falta de índice | Médio (criar 1 índice) |
| Join a VW_M_CUSTOMED_SEMANA por TO_CHAR(ROM1.DTENTRADA,'IW-YYYY')=MSEM.SEMANA_ENTR | Médio | Chave calculada impede uso de índice; força HASH sobre expressão | Baixo-médio |
| /*+ MATERIALIZE */ em PED_FRETE_VENDAS/PED_DESP_LOG (usadas 1×) | Baixo | Materializar CTE de uso único grava temp sem reuso | Baixo |
| Subquery escalar codparcpatentemp (AD_TGFGRUPATENTES) + OBSERVACAO/status_comercial (AD_CUSTOSPREV) na projeção | Baixo-médio | Executadas por linha; poderiam ser joins | Baixo-médio |
| TO_CHAR(DTNEG,'YYYY'), TO_CHAR(DTENTSAI,'MON') na projeção | Nulo p/ plano | Estão no SELECT, não no WHERE — sem impacto de índice | — |

Não há UNION (só no branch comentado), DISTINCT desnecessário, nem commits (é view).
### 3. Índices (verificado contra o dicionário)
Já existentes e adequados (confirmado):

✅ AD_NOTASEXC — IX_AD_NOTASEXC_CODPROJ (CODPROJ) + IX_AD_NOTASEXC_NUNOTA (NUNOTA) cobrem os dois NOT EXISTS.
✅ AD_TGFITECOMPL — fartamente indexada: AD_TGFITECOMPL_NN_SI (NUNOTA,SEQITE), IDX_AD_TGFITECOMPL_ROM (NUNOTA,ROMANEIO), AD_TGFITECOMPL_CONTROLE_IDX, IX_AD_TGFITECOMPL_PRODCODE, IX_AD_TGFITECOMPL_CODPROJ.
✅ AD_ROMANEIOENTR — PK (NROUNICO) + IX_AD_ROMANEIOENTR_BMC_01.
✅ AD_CUSTOSPREV — IX_AD_CUSTOSPREV_BMC_02 (CODPROJ,CODPARC,TIPOCUSTO) casa com as subconsultas escalares.
✅ TGFCAB — dezenas de índices, incluindo a família IX_TGFCAB_BMC_0x desenhada para este BI.

Falta criar (única ação de índice do stack):

🔴 TGFCAB.AD_NUNOTASUB — sem nenhum índice (confirmado no dump). É o anti-join NOT EXISTS (... ex1.AD_NUNOTASUB=cab.nunota), que hoje faz FULL SCAN de TGFCAB.

CREATE INDEX ix_tgfcab_ad_nunotasub ON TGFCAB(AD_NUNOTASUB);

Coluna esparsa → índice pequeno (linhas 100% NULL não entram no B-tree).

Não criar:

TGFCAB.AD_NUNOTACREF (predicado IS NULL — B-tree comum não ajuda).
Join por TO_CHAR(...,'IW-YYYY') a VW_M_CUSTOMED_SEMANA: a MV já tem VW_M_CONTROLE_VLRMP_IDX/similar, mas a chave calculada impede uso — resolver seria mudar a expressão de join (fora de escopo de índice).

Não sugiro remover nenhum índice sem ver uso real (V$SEGMENT_STATISTICS).
### 4. Reescrita
4.a — Colisão de alias — ✅ APLICADA E VALIDADA. Os 9 CTEs foram renomeados para nomes semânticos e a equivalência foi confirmada contra produção. Mantido como registro:

-- ANTES (aliases duplicados no mesmo bloco):     -- DEPOIS (nomes semânticos):

Q3 → QTDNEG_POR_CALIBRE / VLRPROVFORN_POR_CENCUS  QCAL.QTDNEGCALIBRE  |  QPRV.VLRPROVFORN

Q4 → QTDNEG_POR_CONTROLE / PARC_PATENTE           QCTR.QTDNEGCONTROLE |  QPAT.CODPARCPATENTE

Q5 → QTDNEG_POR_FORN / VARIEDADE_MP               QFOR.QTDNEGFOR      |  QVAR.CODVARIEDADEMP

(demais: QNOTA, QCEN, QNFMP)

4.b — Datas hardcoded — ✅ parcialmente aplicada. Já convertidas para literal ANSI (DATE '2025-12-18', DATE '2026-06-01'), removendo dependência de NLS. Pendente (opcional): externalizar para tabela de parâmetro que retorne o mesmo valor — não alterar a lógica de corte. [VALIDAR valor idêntico]

4.c — MATERIALIZE de uso único: remover o hint de PED_FRETE_VENDAS/PED_DESP_LOG (viram inline view) — resultado idêntico, evita spill em temp. Risco baixo. (Pendente.)

4.d — Duplicação do CASE de PROCESSO: extrair a classificação (REFUGO PA/MP/TRANSFERÊNCIA) para uma CTE única — hoje repetida na coluna PROCESSO e no CASE de VLRCTE. Resultado idêntico; reduz risco de manutenção. (Pendente.)
### 5. Legibilidade
✅ Aliases já renomeados para nomes semânticos (QNOTA/QCEN/QCAL/QCTR/QFOR/QPRV/QPAT/QVAR/QNFMP).
✅ Comentários mortos removidos (blocos CASE ROMANEIO → ITE.ROMANEIO_NUM; filtro de ano).
Pendente: extrair o CASE de PROCESSO (duplicado no SELECT e no VLRCTE) para 1 CTE de classificação.
### 6. Dependências impactadas
Direto: VW_BMC_BI_BASE_ITENS_V9 consome esta view — o rename de alias é interno e não muda a assinatura (colunas de saída), logo a V9 não é afetada. ✔
MVs (VW_M_CUSTOMED_SEMANA) e views de devolução: inalteradas.
### 7. Segurança
View sem SQL dinâmico → sem superfície de injection.
GRANT SELECT ... TO READ_ONLY (na V9) é apropriado. Sem privilégio excessivo aparente.
### 8. Escalabilidade
100 mil / 1 milhão: aceitável — os índices dos anti-joins já existem, exceto TGFCAB.AD_NUNOTASUB (✅ criado nesta rodada).

Nota de medição (05/07): VW_NOTAS_31 isolada custa ~3 min (~10% da carga). Não é o gargalo — este está na V9 (~17 min). Ver LOG DE PROGRESSO no topo. Otimizações adicionais aqui têm retorno limitado; priorizar a V9.

10 milhões: os anti-joins e o join por expressão viram gargalo; HASH em temp cresce.
100 milhões: inviável como view online — o consumo já é via materialização (procedure), o que é a mitigação correta. Recomenda-se filtrar por período na carga (a base parece histórica total).
### 9. Plano de execução (inferido — validar)
Provável FULL SCAN em TGFCAB e AD_TGFITECOMPL (tabelas grandes, sem predicado seletivo).
HASH JOIN para as CTEs materializadas (temp).
NESTED LOOPS para os LEFT JOIN a dimensões pequenas (TSIPAI, TSIUFS, AD_PORTO...).
FILTER para os NOT EXISTS — operação mais cara se faltar índice.
HASH GROUP BY nas CTEs de quantidade.
### 10. Classificação (pós-correção da colisão de alias)
| Dimensão | Nota anterior | Nota atual |
|---|---|---|
| Performance | 4 | 4 |
| Legibilidade | 3 | 5 ↑ (aliases semânticos, código morto removido) |
| Escalabilidade | 4 | 4 |
| Segurança | 7 | 7 |
| Manutenibilidade | 3 | 5 ↑ (compila de forma determinística) |
| Complexidade (10=pior) | 9 | 9 |

## OBJETO 2 — VW_BMC_BI_BASE_ITENS_V9
### 1. Análise geral
Objetivo: cálculo de margem por item, com regras por fruta.
Complexidade: extrema (3 níveis aninhados, dezenas de CASE por fruta, funções escalares e subconsultas correlacionadas por linha).
Pontos fortes: funções de custo já com RESULT_CACHE/DETERMINISTIC; proteção NULLIF/COALESCE contra divisão por zero.
Pontos fracos: cálculo duplicado em 2 níveis; funções escalares repetidas na mesma linha; ~8 subconsultas correlacionadas por item; blocos comentados extensos; TO_NUMBER(nropallet) sem guarda.
Risco de manutenção: muito alto.
### 2. Performance
| Achado | Impacto | Motivo | Ganho |
|---|---|---|---|
| ~8 subconsultas correlacionadas por item contra VW_BMC_BI_CUSTOS_PROD_OTM (mp, embalagem, direto MI/ME, operação, serviço, colheita, imp. saldo) | Alto | Cada componente refaz o acesso ao mesmo pallet | Alto |
| Funções escalares repetidas na mesma linha: FU_BMC_GETPROVFORN 2×, FU_BMC_GETROYALTIES 2×, FU_BMC_GETCOMVENDA('TERCEIROS') 2×, FUN_ARG_VLRETIQSRV Nx | Alto | Mesmo com RESULT_CACHE, há overhead de chamada e reavaliação de argumentos | Médio-alto |
| Duplicação de CUSTOTOTALGER/MARGEMGER/PERCMARGEMGER/PROVISAO_FORNECEDOR_GER em N2 e na projeção externa | Médio-alto | CPU dobrada + risco de divergência | Médio-alto |
| Blocos CASE de incoterm repetidos dezenas de vezes | Médio | Reavaliação e risco de inconsistência ('FOB' presente em alguns, ausente em outros) | Médio |
| TO_NUMBER(nropallet) sem REGEXP guard | Correção | ORA-01722 se não numérico | — |

### 3. Índices (verificado contra o dicionário)
A V9 herda o acesso via VW_NOTAS_31 e VW_BMC_BI_CUSTOS_PROD_OTM; o ganho de índice está naquelas views, não em predicados próprios da V9 — e ambas já estão bem cobertas (ver seções 3 dos Objetos 1 e 3).
Se a otimização 4.a (join agregado) materializar a ficha de custo, indexar a materialização por (NROUNICO, CODPRODUTOR, LOTEMP).
### 4. Reescrita (flagship)
4.a — Correlacionadas → join agregado único. Ganho alto, risco médio [VALIDAR].

-- ATUAL (repetido ~8× por item, variando o filtro v.mp / v.embalagem / v.direto ...):

(SELECT MAX(vlrcustoUNIT) FROM VW_BMC_BI_CUSTOS_PROD_OTM v

  WHERE N1.nropallet=v.NROUNICO AND N1.codprodutor=v.codprodutor

    AND N1.lotemp=v.lotemp AND v.colheita='S') * n1.qtdbase   AS CUSTO_COLHEITA_MANGA

-- ... e mais 7 variações (embalagem, direto MI, direto ME, operacao, servico, imp_saldo, mp)

-- OTIMIZADO: 1 join a uma agregação por pallet, com agregação condicional:

LEFT JOIN (

  SELECT NROUNICO, codprodutor, lotemp,

         MAX(CASE WHEN colheita='S'        THEN vlrcustounit END)                 AS un_colheita,

         SUM(CASE WHEN embalagem='S'       THEN vlrcusto END)

           / NULLIF(MAX(CASE WHEN embalagem='S' THEN qtd END),0)                  AS un_embalagem,

         SUM(CASE WHEN direto='S'          THEN vlrcusto END)

           / NULLIF(MAX(CASE WHEN direto='S'    THEN qtd END),0)                  AS un_direto,

         MAX(CASE WHEN implantacaosaldo='S' THEN vlrcustounit END)                AS un_impsaldo,

         MAX(CASE WHEN mp='S' THEN COALESCE(vlrcustocalibreunit,vlrcustoprecoentradaunit) END) AS un_mp

         -- ... demais componentes

  FROM VW_BMC_BI_CUSTOS_PROD_OTM

  GROUP BY NROUNICO, codprodutor, lotemp

) FIC ON FIC.NROUNICO=N1.nropallet AND FIC.codprodutor=N1.codprodutor AND FIC.lotemp=N1.lotemp

Explicação: MAX/SUM ignoram NULL, então a agregação condicional reproduz exatamente cada filtro WHERE ... = 'S'. A multiplicação por qtdbase/pesoliqpro continua por linha, fora do join. Risco [VALIDAR]: conferir cada componente por amostragem (ex.: um pallet que satisfaça mais de uma flag, e o direto MI vs ME que dependem de MERCADO), porque a semântica de SUM(VLRCUSTO)/max(qtd) precisa bater 1:1. Recomendo validar somando CUSTOTOTALGER de um período inteiro antes/depois.

4.b — Materializar funções escalares repetidas por linha. Ganho médio-alto, risco baixo.

-- ATUAL: FU_BMC_GETPROVFORN(...) chamada no cálculo de custo, de novo na margem, de novo na provisão.

-- OTIMIZADO: computar 1× num nível intermediário e referenciar por alias:

... (SELECT FU_BMC_GETPROVFORN(...) FROM dual) AS v_provforn ...  -- ou coluna da subquery N2

-- e usar v_provforn nas expressões seguintes.

Explicação: resultado idêntico (função DETERMINISTIC), elimina reavaliação. Idem para FUN_ARG_VLRETIQSRV(to_number(nropallet))*total_cx.

4.c — Consolidar cálculo em 1 nível. [VALIDAR qual nível é a fonte de verdade] Manter CUSTOTOTALGER/MARGEMGER/PERCMARGEMGER apenas na projeção externa (que é a que sai hoje) e no nível N2 apenas repassar. Risco: confirmar que nenhum consumidor lê a versão de N2 (não lê — N2 é subquery interna).

4.d — Guarda de TO_NUMBER: aplicar o mesmo padrão da VW_NOTAS_31: CASE WHEN REGEXP_LIKE(nropallet,'^[0-9]+$') THEN TO_NUMBER(nropallet) END. [VALIDAR] — só equivale se hoje nropallet é sempre numérico onde a função é chamada; se houver não-numérico, o comportamento atual é erro, então a guarda muda de "erro" para "0/NULL" → é melhoria, mas é mudança de comportamento em caso de erro. Sinalizo.
### 5. Legibilidade
Remover blocos comentados (várias versões antigas de CUSTOTOTALGER/MARGEMGER).
Extrair a expressão de frete-por-incoterm para uma coluna intermediária (frete_incoterm) reutilizada — hoje replicada dezenas de vezes com risco de divergência ('FOB').
Padronizar indentação dos CASE por fruta.
### 6. Dependências impactadas
Consumida por STP_BMC_CARGA_MRG_BI_BASE (cursor). As reescritas não alteram a lista/ordem de colunas → procedure inalterada. ✔
A otimização 4.a depende de VW_BMC_BI_CUSTOS_PROD_OTM (ou de sua materialização) — ver Objeto 3.
### 7. Segurança
Sem SQL dinâmico. Funções RESULT_CACHE leem tabelas de config com RELIES_ON (invalidação correta). Sem injection.
### 8. Escalabilidade
100 mil: ok via materialização.
1 milhão: as correlacionadas por item começam a dominar o tempo de carga.
10 milhões: carga pode estourar janela; a otimização 4.a é o que torna viável.
100 milhões: exige particionamento por período/safra na base materializada.
### 9. Plano de execução (inferido)
Hoje: para cada linha de VW_NOTAS_31, NESTED LOOP com múltiplos acessos a VW_BMC_BI_CUSTOS_PROD_OTM (que por sua vez chama funções escalares) → efeito multiplicativo.
Pós-4.a: um HASH JOIN único contra a agregação por pallet → colapsa N acessos em 1.
### 10. Classificação
| Dimensão | Nota |
|---|---|
| Performance | 3 |
| Legibilidade | 2 |
| Escalabilidade | 3 |
| Segurança | 7 |
| Manutenibilidade | 2 |
| Complexidade (10=pior) | 10 |

## OBJETO 3 — VW_BMC_BI_CUSTOS_PROD_OTM
### 1. Análise geral
Objetivo: ficha de custo por pallet (fonte das correlacionadas da V9).
Complexidade: média (CTE base+custos, 2 funções escalares por linha).
Pontos fortes: estrutura limpa em CTE; precedência de custo via COALESCE(NULLIF(...)) (elegante e correta).
Pontos fracos: 2 escalares por linha; sem persistência (recalculada a cada leitura da V9).
Risco de manutenção: baixo-médio.
### 2. Performance
| Achado | Impacto | Motivo | Ganho |
|---|---|---|---|
| FU_BMC_GETPRECOENTRADA + obtemcusto4 por linha | Médio | 2 funções/linha; multiplicado pelo nº de acessos da V9 | Médio-alto (se materializar) |
| View recalculada a cada subconsulta da V9 | Alto (indireto) | Sem materialização, o custo se repete | Alto |

### 3. Índices (verificado contra o dicionário)
✅ AD_MONTPALLETITE — IX_AD_MONTPALLETITE_BMC_04 (NROUNICO, NUNOTABASE) cobre o join da CTE base; há ainda IX_AD_MONTPALLETITE_BMC_03 (NROUNICO,CODPROD,LOTE,CALIBRE,MERCPROD,NUNOTA).
✅ AD_MONTPALLET — PK (NROUNICO). TGFITE(NUNOTA) fartamente indexada.
✅ AD_BMCPRECOENTRADA — PK (NUNOTA,CODPROD,CALIBRE) casa exatamente com FU_BMC_GETPRECOENTRADA; TGFCUS bem indexada para obtemcusto4 (TGFCUS_I01).
Se materializar (recomendação 4): criar PK/índice (NROUNICO, CODPRODUTOR, LOTEMP) + colunas de flag na tabela materializada.
### 4. Reescrita
Materializar como MV com refresh na mesma janela da carga (ou tabela AD_* populada por procedure), idêntica em conteúdo. A V9 passa a ler a materialização (ver 4.a do Objeto 2). Ganho alto, risco baixo (mesmo SELECT).
obtemcusto4 deveria tratar NO_DATA_FOUND internamente (hoje pode estourar) — [VALIDAR] pois hoje o erro pode estar sendo mascarado a montante.
### 5. Legibilidade
Boa. Só documentar inline as flags (codtipoper=213→implantação; USOPROD 'E'/'M').
### 6. Dependências impactadas
Materializá-la muda como a V9 lê (join em vez de subquery), não o que lê. Refresh precisa entrar na STP_BMC_CARGA_MRG_BI_BASE (junto das outras MVs). ✔
### 7. Segurança
Sem dinâmico. OK.
### 8. Escalabilidade
Como view online recalculada, degrada com o volume da V9. Materializada, escala bem (1 passada por pallet).
### 9. Plano
CTE base: HASH JOINs em TGFCAB/TGFITE/TGFPRO + NESTED LOOP nos pallets. CTE custos: função escalar por linha (não paralelizável bem).
### 10. Classificação
| Dimensão | Nota |
|---|---|
| Performance | 5 |
| Legibilidade | 7 |
| Escalabilidade | 5 |
| Segurança | 7 |
| Manutenibilidade | 6 |
| Complexidade | 5 |

## OBJETO 4 — STP_BMC_CARGA_MRG_BI_BASE (procedure principal)
### 1. Análise geral
Objetivo: materializar a margem em AD_NOTASITEMPROMARGEMBI.
Complexidade: média (refresh MV + truncate + cursor/FORALL + swap por flag).
Pontos fortes: BULK COLLECT/FORALL (melhor que row-by-row).
Pontos fracos: sem EXCEPTION; DELETE WHERE ATIVO='S' redundante após TRUNCATE; múltiplos commits; base indisponível durante recarga.
Risco de manutenção: médio.
### 2. Performance
| Achado | Impacto | Motivo | Ganho |
|---|---|---|---|
| Cursor + BULK COLLECT(1000) + FORALL | Médio | Round-trip PL/SQL desnecessário para carga massiva | Médio-alto |
| DELETE ... WHERE ATIVO='S' após TRUNCATE | Baixo | No-op (tabela vazia) — gera redo à toa | Baixo |
| Sem EXCEPTION/log | Robustez | Falha deixa base sem ATIVO='S' | — |

### 3. Índices (verificado contra o dicionário)
AD_NOTASITEMPROMARGEMBI.ATIVO — confirmado sem índice (a tabela tem só ANO, CODPROD, FRUTA, NUNOTA e a PK). Serviria ao swap DELETE/UPDATE WHERE ATIVO, mas a reescrita 4 elimina o swap → não criar.
### 4. Reescrita (flagship) — ganho médio-alto, risco baixo
-- ATUAL:

OPEN c_margem_bi; LOOP FETCH ... BULK COLLECT INTO l ... LIMIT 1000;

  EXIT WHEN l.COUNT=0;

  FORALL i IN 1..l.COUNT INSERT INTO AD_NOTASITEMPROMARGEMBI(...) VALUES(SEQ.NEXTVAL, l(i)...);

END LOOP; CLOSE ...;

DELETE ... WHERE ATIVO='S'; COMMIT;

UPDATE ... SET ATIVO='S' WHERE ATIVO='N'; COMMIT;

-- OTIMIZADO:

INSERT /*+ APPEND */ INTO AD_NOTASITEMPROMARGEMBI

  (CODNOTASITEMPROMARGEMBI, DHCARGA, ATIVO, ... )

SELECT SEQ_NOTASITEMPROMARGEMBI.NEXTVAL, SYSDATE, 'S', v.*  -- 'S' direto: TRUNCATE já zerou a base

FROM   VW_BMC_BI_BASE_ITENS_V9 v;

COMMIT;

Explicação: direct-path (APPEND) + elimina o vaivém PL/SQL. Como o TRUNCATE zera a base, inserir já com ATIVO='S' produz o mesmo estado final do swap delete/update. [VALIDAR]: confirmar que nenhum processo concorrente lê a tabela durante a carga esperando ver a versão anterior — se ler, manter o padrão blue-green sem truncate (carrega 'N', depois DELETE 'S'+UPDATE 'N'→'S' numa transação). Nesse caso o ganho vem de trocar o cursor por INSERT..SELECT, mantendo o swap.

4.b — Envelopar em transação + EXCEPTION com log (a procedure auxiliar já faz isso — replicar o padrão). Preserva resultado; melhora robustez.
### 5. Legibilidade
Extrair a lista gigante de colunas para um comentário de mapa; ou usar %ROWTYPE no INSERT..SELECT (implícito).
Remover chamadas comentadas (STP_ARG_UPD_..., VW_NOTAS_30).
### 6. Dependências impactadas
Refresh das MVs deve continuar antes do INSERT..SELECT. Se materializar a ficha de custo (Objeto 3), adicionar o refresh dela aqui. ✔
### 7. Segurança
EXECUTE IMMEDIATE 'TRUNCATE TABLE ...' com nome de tabela literal (sem entrada de usuário) → sem risco de injection. OK.
### 8. Escalabilidade
INSERT..SELECT com APPEND escala melhor que cursor à medida que a V9 cresce. Para 10M+, avaliar ENABLE PARALLEL DML.
### 9. Plano
Hoje: N execuções da V9 por lote (fetch) + N FORALL. Pós-reescrita: 1 execução da V9 + 1 direct-path load.
### 10. Classificação
| Dimensão | Nota |
|---|---|
| Performance | 4 |
| Legibilidade | 6 |
| Escalabilidade | 5 |
| Segurança | 6 |
| Manutenibilidade | 4 |
| Complexidade | 4 |

## OBJETO 5 — STP_ARG_PROCESS_AD_TGFITECOMPL (procedure CDC)
### 1. Análise geral
Objetivo: consumir a fila de notas e reconstruir AD_TGFITECOMPL incrementalmente.
Complexidade: baixa-média.
Pontos fortes: EXCEPTION com ROLLBACK+RAISE; lote de 500; /*+ APPEND */; preserva AJUSTE_MANUAL='S'.
Pontos fracos: NUM_TAB() init redundante; delete+insert onde MERGE poderia reduzir redo.
Risco de manutenção: baixo.
### 2. Performance
| Achado | Impacto | Motivo | Ganho |
|---|---|---|---|
| DELETE+INSERT APPEND por lote | Baixo-médio | MERGE evitaria reescrever linhas iguais | Baixo-médio |
| l_list := NUM_TAB(); antes do bulk | Nulo | Recriação redundante | — |

### 3. Índices (verificado contra o dicionário)
✅ AD_TGFITECOMPL_FILA — AD_TGFITECOMPL_Q_RT (REQUESTED_AT) já cobre o ORDER BY requested_at FETCH FIRST 500; PK/índice em NUNOTA para a limpeza da fila. Nada a fazer.
✅ AD_TGFITECOMPL — AD_TGFITECOMPL_NUNOTA1_IDX (NUNOTA) + PK (NUNOTA,SEQUENCIA) atendem o delete/insert por nota. (Não há índice em AJUSTE_MANUAL, mas o predicado do delete é por NUNOTA + filtro NVL(AJUSTE_MANUAL,'N')='N' aplicado sobre poucas linhas da nota — impacto baixo.)
### 4. Reescrita
Remover a linha de init redundante. Risco nulo.
[VALIDAR] MERGE só se a semântica de AJUSTE_MANUAL permitir (linhas manuais não podem ser tocadas); o delete atual já exclui ='S', então um MERGE precisaria do mesmo predicado. Como envolve sutileza, descrevo mas não recomendo sem validação.
### 5. Legibilidade
Boa. Nomear o cursor implícito/lote; comentar a preservação de AJUSTE_MANUAL.
### 6. Dependências impactadas
VW_NOTAS_31 e views de devolução _FOR/_2 leem AD_TGFITECOMPL. Mudanças aqui não alteram o conteúdo produzido. ✔
### 7. Segurança
Bind por TABLE(l_list) (coleção) — sem injection. EXCEPTION adequada.
### 8. Escalabilidade
Lote fixo de 500 escala linearmente com a fila. Para picos, avaliar lote maior + LIMIT.
### 9. Plano
FETCH FIRST 500 (STOPKEY) + DELETE/INSERT por IN (TABLE(l_list)) → acesso por índice se AD_TGFITECOMPL(NUNOTA) existir.
### 10. Classificação
| Dimensão | Nota |
|---|---|
| Performance | 7 |
| Legibilidade | 7 |
| Escalabilidade | 7 |
| Segurança | 8 |
| Manutenibilidade | 7 |
| Complexidade | 4 |

## OBJETO 6 — Cluster de funções FU_* / FUN_* / OBTEMCUSTO4
### 1. Análise geral
Objetivo: lookups de configuração ranqueados + custos de pallet.
Pontos fortes: maioria já DETERMINISTIC + RESULT_CACHE RELIES_ON (excelente para chamadas repetidas).
Pontos fracos: FU_BMC_GETPERCCOMVENDA sem RESULT_CACHE; tratamento de exceção heterogêneo; WHEN OTHERS RETURN NULL mascara erro nas de etiqueta.
### 2. Performance
| Achado | Impacto | Motivo | Ganho |
|---|---|---|---|
| FU_BMC_GETPERCCOMVENDA sem RESULT_CACHE | Médio | Chamada por linha na V9 sem cache | Médio |
| ORDER BY CASE ... FETCH FIRST 1 ROW | Baixo | Sort por linha; ok porque resultado é 1 linha | Baixo |

### 3. Índices
Confirmado no dicionário: AD_CONFCOMVENDAREG, AD_CONFPROVFORNREG, AD_CONFROYALTREG e AD_CUSTOGERITE têm apenas a PK (por código sequencial) — os predicados de casamento (CODFRUTA, CODPROJ, CODGRUPOPROD, MERCADO, ...) não são indexados. Como são tabelas pequenas de parâmetro e as funções são RESULT_CACHE, o FULL SCAN é barato e cacheado → ganho de índice baixo, não prioritário. AD_CUSTOSPREV (usada por FU_BMC_GETCUSTOPREVISTO) já tem IX_AD_CUSTOSPREV_BMC_02 (CODPROJ,CODPARC,TIPOCUSTO). ✅
### 4. Reescrita
Adicionar RESULT_CACHE RELIES_ON (AD_CONFCOMVENDA, AD_CONFCOMVENDAREG) a FU_BMC_GETPERCCOMVENDA — resultado idêntico, ganho médio. Risco baixo.
Fundir FU_ARG_TXADM_CUSTO_GER + FU_BMC_PRECO_CUSTO_GER numa função com parâmetro de coluna ('TXADM'/'PRECO') — [VALIDAR] mantém retorno idêntico; reduz duplicação. Risco baixo-médio (dois objetos passam a depender de um; testar ambos os retornos).
Tratamento de exceção: NÃO alterar WHEN OTHERS RETURN NULL das funções de etiqueta sem validação — hoje o NULL vira 0 na V9; trocar para RAISE mudaria comportamento em caso de erro. Descrevo o risco; recomendo ao menos logar antes de retornar NULL.
### 5. Legibilidade
Documentar o ranking CASE (regra mais específica → genérica) num comentário-cabeçalho padrão.
OBTEMCUSTO4: remover END; END; duplicado confuso; tratar NO_DATA_FOUND.
### 6. Dependências impactadas
Fusão das gêmeas afeta VW_BMC_BI_BASE_ITENS_V9/VW_NOTAS_31 (que chamam ambas) — recompilar e testar. ✔ com validação.
### 7. Segurança
Sem SQL dinâmico. RESULT_CACHE RELIES_ON garante invalidação correta. OK.
### 8. Escalabilidade
Com RESULT_CACHE, chamadas repetidas com mesmos argumentos escalam muito bem. O gargalo é a variedade de argumentos (cache miss) em volumes grandes.
### 9. Plano
Cada função: INDEX RANGE SCAN/FULL na tabela de config + SORT ORDER BY STOPKEY. Barato individualmente; o custo é a frequência (mitigada por cache).
### 10. Classificação (média do cluster)
| Dimensão | Nota |
|---|---|
| Performance | 7 |
| Legibilidade | 6 |
| Escalabilidade | 7 |
| Segurança | 8 |
| Manutenibilidade | 6 |
| Complexidade | 5 |

Revisão consolidada — views de projeção simples
Para estas, o texto é enxuto e as recomendações são pontuais (não repito 12 seções):

| View | Achado principal | Ação | Ganho | Risco |
|---|---|---|---|---|
| VW_BMC_GET_QTD_DEV_VENDA | UNION ALL + lista de NUNOTAs hardcoded (comentado) | Remover código morto; se reativar, mover exclusões para tabela | Baixo | Baixo |
| VW_BMC_GET_QTD_DEV_VENDA_FOR / _2 | 3 views quase idênticas | Avaliar unificar com coluna de granularidade | Baixo (manut.) | Médio [VALIDAR] |
| VW_CTE_CODPROJ | 2 linhas de dados fixas via UNION ALL | Mover para tabela de exceção | Baixo | Baixo |
| VW_DESCFIN | UNION ALL por corte de data (legado/novo) | Correto manter; UNION ALL já é o certo (sem dedup) | — | — |
| VW_PERCPROC_NF_V4 | usa VW_BMC_GET_QTD_DEV_VENDA + AD_MONTPALLITE | ok; indexar AD_MONTPALLETITE(NROUNICO) | Baixo | Baixo |
| VW_ARG_DEB_CRE_ITE | agregações por controle/calibre | validar índices de CODPROJ,CODPROD,CONTROLE | Médio | Baixo |
| ARG_COMPRA_MP | CASE %COMPLEMENTAR% por linha | ok funcionalmente; indexar CODPROD,CONTROLEPA | Baixo | Baixo |

UNION → UNION ALL: verifiquei — VW_DESCFIN e VW_CTE_CODPROJ já usam UNION ALL (correto, pois não há necessidade de dedup e os conjuntos são disjuntos). Não encontrei UNION (com dedup) que deva virar UNION ALL nas views fornecidas.

ETAPA 11 — Matriz de priorização (todas as melhorias)
| Prioridade | Mudança | Ganho esperado | Risco | Esforço |
|---|---|---|---|---|
| Crítica ✅ CONCLUÍDA | Colisão de alias Q3/Q4/Q5 em VW_NOTAS_31 | (destravou o stack) | — validada em produção | — |
| Crítica | V9: correlacionadas → join agregado por pallet (4.a) | Alto | Médio [VALIDAR] | Alto |
| Alta | Procedure principal: cursor/FORALL → INSERT /*+ APPEND */ SELECT | Médio-alto | Baixo [VALIDAR concorrência] | Baixo |
| Alta | Materializar VW_BMC_BI_CUSTOS_PROD_OTM (+ refresh na carga) | Alto | Baixo | Médio |
| Alta | V9: consolidar cálculo em 1 nível (4.c) | Médio-alto | Médio [VALIDAR] | Médio |
| Alta | V9: materializar funções escalares repetidas por linha (4.b) | Médio-alto | Baixo | Médio |
| Média | FU_BMC_GETPERCCOMVENDA: adicionar RESULT_CACHE | Médio | Baixo | Baixo |
| Baixa | Criar 1 índice: ix_tgfcab_ad_nunotasub (única lacuna real; resto do stack já indexado) | Médio | Baixo | Baixo |
| Média | Procedure principal: EXCEPTION + log + revisar swap/TRUNCATE | (robustez) | Baixo | Baixo |
| Média | Externalizar datas/patches p/ tabela de parâmetro (datas já em ANSI ✅; falta externalizar) | (manut.) | Baixo [VALIDAR valor idêntico] | Baixo |
| Baixa | Fundir funções gêmeas TXADM/PRECO_CUSTO_GER | (manut.) | Baixo-médio [VALIDAR] | Baixo |
| Baixa | Código morto ✅ (VW_NOTAS_31) · falta MATERIALIZE de uso único / extrair CASE de PROCESSO | (legib.) | Baixo | Baixo |
| Baixa | Unificar as 3 views de devolução | (manut.) | Médio [VALIDAR] | Médio |

ETAPA 12 — Garantia de comportamento (itens que exigem validação humana)
Estas mudanças não devem ser aplicadas sem validar equivalência funcional por amostragem (comparar soma/contagem de um período inteiro antes×depois):

Correlacionadas → join agregado (V9, 4.a): a semântica de MAX vs SUM/max(qtd) e os filtros direto MI/ME por MERCADO precisam bater 1:1. Risco de divergência silenciosa em pallets com múltiplas flags.
Consolidação de cálculo em 1 nível (4.c): confirmar que a versão externa é de fato a única consumida (é subquery — sim, mas validar).
INSERT..SELECT sem swap (procedure): só equivalente se não houver leitor concorrente esperando a versão anterior durante a recarga. Se houver, manter blue-green sem TRUNCATE.
Guarda REGEXP/TO_NUMBER (V9, 4.d): muda comportamento apenas em caso de dado não-numérico (hoje erro → depois 0/NULL). É melhoria, mas é mudança em cenário de exceção.
WHEN OTHERS RETURN NULL das funções de etiqueta: não trocar por RAISE sem validar — hoje NULL vira 0 na V9.
Fusão das funções gêmeas: recompilar e testar TXADM e PRECO separadamente.
Alias rename (VW_NOTAS_31) — ✅ CONCLUÍDA e validada em produção. A view compila de forma determinística e o resultado confere. Sai da lista de pendências.

Regra aplicada: onde a equivalência dependeu de suposição sobre dados/concorrência que não posso verificar só pelo texto, marquei [VALIDAR] e descrevi o risco — em vez de recomendar a mudança como segura.

Query para fechar as lacunas de diagnóstico
-- 1) Objetos do stack estão VÁLIDOS? (VW_NOTAS_31 já validada; manter no CI)

SELECT object_name, object_type, status

FROM   all_objects

WHERE  owner='SANKHYA'

AND    object_name IN ('VW_NOTAS_31','VW_BMC_BI_BASE_ITENS_V9',

                       'VW_BMC_BI_CUSTOS_PROD_OTM');

-- 2) Índices: JÁ LEVANTADOS via dump de all_ind_columns (rev. deste doc).

--    Conclusão: stack bem indexado; única lacuna é TGFCAB.AD_NUNOTASUB.

--    Ação:

CREATE INDEX ix_tgfcab_ad_nunotasub ON SANKHYA.TGFCAB(AD_NUNOTASUB);

-- 3) O que FALTA confirmar: o plano real (existência do índice ≠ uso pelo otimizador)

EXPLAIN PLAN FOR SELECT * FROM SANKHYA.VW_NOTAS_31 WHERE ROWNUM <= 1000;

SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY);

-- procurar nas linhas de AD_NOTASEXC / TGFCAB por INDEX ... SCAN (bom) vs FULL (revisar estatísticas)
