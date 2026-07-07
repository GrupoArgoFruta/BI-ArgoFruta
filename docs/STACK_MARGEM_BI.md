# Documentação Técnica — Stack de Margem BI (Argofruta / Sankhya)

Objetos documentados:

SANKHYA.STP_BMC_CARGA_MRG_BI_BASE (Procedure)
SANKHYA.VW_BMC_BI_BASE_ITENS_V9 (View)
SANKHYA.VW_NOTAS_31 (View)

Relação entre eles (cadeia de carga):

STP_BMC_CARGA_MRG_BI_BASE  (procedure de carga)

        ↓ lê

VW_BMC_BI_BASE_ITENS_V9    (view de margem — camada de cálculo)

        ↓ lê

VW_NOTAS_31                (view base — camada de coleta de notas/itens)

        ↓ lê

TGFCAB / AD_TGFITECOMPL / TGFITE / ... (dados transacionais Sankhya)

Convenção usada neste documento: quando uma dependência não está presente nos 3 arquivos fornecidos, ela é marcada com [EXTERNO]. A lista consolidada de tudo que precisa ser buscado está na Seção Final — Lista de dependências para trazer.

## OBJETO 1 — SANKHYA.STP_BMC_CARGA_MRG_BI_BASE (Procedure)
### 1. Resumo
Objetivo: materializar a base analítica de margem por item de nota fiscal na tabela física AD_NOTASITEMPROMARGEMBI, a partir da view de cálculo VW_BMC_BI_BASE_ITENS_V9.

Problema de negócio que resolve: a view VW_BMC_BI_BASE_ITENS_V9 é extremamente pesada (várias camadas aninhadas, dezenas de funções escalares e subconsultas correlacionadas por linha). Consultá-la em tempo real no Looker Studio / BI seria inviável em performance. A procedure "congela" o resultado num snapshot físico (padrão ETL de materialização), atualizado por execução agendada, que o BI consome de forma rápida e estável.
### 2. Fluxo de execução
Passo a passo do que a procedure faz, em ordem:

Recalcula 3 materialized views com refresh completo (METHOD => 'C'): VW_M_NFVENDAS_DEVINT, VW_M_CONTROLE_VLRMP, VW_M_CUSTOMED_SEMANA. Isso garante que as bases auxiliares de devolução, controle de valor de MP e custo médio semanal estejam atualizadas antes de ler a view de margem (a VW_M_CUSTOMED_SEMANA é consumida lá dentro, dentro de VW_NOTAS_31).
Trunca AD_NOTASITEMPROMARGEMBI (tabela final de margem) e AD_BMCPRECOENTRADA (tabela auxiliar de preço de entrada).
Carrega AD_BMCPRECOENTRADA com o resultado de VW_BMC_GETPRECOENTRADA (NUNOTA, CODPROD, CALIBRE, VLRUNIT, VLRTOT, CONTROLE) e faz COMMIT.
Chama a procedure auxiliar STP_ARG_PROCESS_AD_TGFITECOMPL() e faz COMMIT. Ela prepara/atualiza a tabela AD_TGFITECOMPL, que é a base de itens usada por VW_NOTAS_31.
Abre o cursor c_margem_bi sobre VW_BMC_BI_BASE_ITENS_V9 e percorre os dados em lotes de 1000 (BULK COLLECT ... LIMIT 1000).
Para cada lote, insere em massa (FORALL) na AD_NOTASITEMPROMARGEMBI, gerando a PK com SEQ_NOTASITEMPROMARGEMBI.NEXTVAL. Todos os registros entram com DHCARGA = SYSDATE e ATIVO = 'N'.
Ao esgotar o cursor, executa o par de comandos de "publicação":
DELETE ... WHERE ATIVO = 'S' (remove versão antiga) + COMMIT.
UPDATE ... SET ATIVO = 'S' WHERE ATIVO = 'N' (promove a versão recém-carregada) + COMMIT.

Trechos comentados (não executam): STP_ARG_UPD_AD_TGFITECOMPL, DBMS_MVIEW.REFRESH('VW_NOTAS_30'), STP_ARG_CARGA_AD_REC_COM. Registrados aqui apenas para rastreabilidade histórica.
### 3. Entradas
| Parâmetro | Tipo | Obrigatoriedade | Descrição |
|---|---|---|---|
| (nenhum) | — | — | Procedure sem parâmetros. Toda a origem de dados é fixa no corpo (view + views auxiliares). |

### 4. Saídas
Não há retorno (procedure void). O "resultado" é o efeito colateral: a tabela AD_NOTASITEMPROMARGEMBI fica repovoada com o snapshot atual da margem, com ATIVO = 'S'. A estrutura de colunas gravadas é a mesma projetada por VW_BMC_BI_BASE_ITENS_V9 (ver Seção 4 do Objeto 2), acrescida de:

| Coluna | Significado |
|---|---|
| CODNOTASITEMPROMARGEMBI | Chave primária sequencial (via SEQ_NOTASITEMPROMARGEMBI). |
| DHCARGA | Data/hora da carga (SYSDATE no momento do fetch). |
| ATIVO | Flag de publicação: 'S' = linha vigente para o BI. |

### 5. Regras de negócio
Refresh antes da leitura: as 3 MVs são recalculadas antes de abrir o cursor, para não ler custo/devolução defasados.

Truncate + recarga total: a base é sempre reconstruída do zero (não é incremental).

Padrão de publicação por flag ATIVO: carrega tudo como 'N', apaga o antigo 'S', promove o novo para 'S'.

⚠️ Observação crítica de lógica: como a tabela é truncada no passo 2, quando chega ao DELETE ... WHERE ATIVO='S' não existe nenhuma linha 'S' — o DELETE é um no-op. O par delete/update só faria sentido num desenho sem truncate (recarga lado a lado / blue-green). Hoje ele é redundante e apenas consome tempo e gera redo. Ver Seção 12.
### 6. Cálculos
A procedure em si não faz cálculo de margem — ela só transporta o que a view calcula. Os únicos "cálculos" próprios são operacionais:

SEQ_NOTASITEMPROMARGEMBI.NEXTVAL → geração de PK incremental, uma por linha inserida.
SYSDATE → carimbo de carga.
### 7. Dependências
| Tipo | Nome | Utilização | Está nos arquivos? |
|---|---|---|---|
| View | VW_BMC_BI_BASE_ITENS_V9 | Fonte principal (cursor) | ✔ Sim |
| View | VW_BMC_GETPRECOENTRADA | Carga de AD_BMCPRECOENTRADA | ✖ [EXTERNO] |
| Materialized View | VW_M_NFVENDAS_DEVINT | Refresh prévio | ✖ [EXTERNO] |
| Materialized View | VW_M_CONTROLE_VLRMP | Refresh prévio | ✖ [EXTERNO] |
| Materialized View | VW_M_CUSTOMED_SEMANA | Refresh prévio (usada dentro de VW_NOTAS_31) | ✖ [EXTERNO] |
| Tabela | AD_NOTASITEMPROMARGEMBI | Destino final (truncate + insert + delete + update) | ✖ [EXTERNO] |
| Tabela | AD_BMCPRECOENTRADA | Auxiliar (truncate + insert) | ✖ [EXTERNO] |
| Sequence | SEQ_NOTASITEMPROMARGEMBI | Geração de PK | ✖ [EXTERNO] |
| Procedure | STP_ARG_PROCESS_AD_TGFITECOMPL | Prepara AD_TGFITECOMPL antes da leitura | ✖ [EXTERNO] |
| Package | DBMS_MVIEW | Refresh das MVs (built-in Oracle) | (built-in) |

### 8. Objetos chamados
Procedures: STP_ARG_PROCESS_AD_TGFITECOMPL; DBMS_MVIEW.REFRESH (built-in).
Views: VW_BMC_BI_BASE_ITENS_V9, VW_BMC_GETPRECOENTRADA.
MVs: VW_M_NFVENDAS_DEVINT, VW_M_CONTROLE_VLRMP, VW_M_CUSTOMED_SEMANA.
Sequences: SEQ_NOTASITEMPROMARGEMBI.
Tabelas: AD_NOTASITEMPROMARGEMBI, AD_BMCPRECOENTRADA.
### 9. Objetos que provavelmente dependem desta procedure
Job de agendamento (Rundeck / DBMS_SCHEDULER / n8n) que dispara a carga — não identificável apenas pelo código, requer consulta ao dicionário.
Pipeline de BI (Pentaho / Oracle → PostgreSQL → Looker Studio) que consome AD_NOTASITEMPROMARGEMBI a jusante.
Qualquer view/relatório que leia AD_NOTASITEMPROMARGEMBI WHERE ATIVO='S'.
### 10. Diagrama textual de dependências
STP_BMC_CARGA_MRG_BI_BASE

   ├─ DBMS_MVIEW.REFRESH

   │     ├─ VW_M_NFVENDAS_DEVINT        [EXTERNO]

   │     ├─ VW_M_CONTROLE_VLRMP         [EXTERNO]

   │     └─ VW_M_CUSTOMED_SEMANA        [EXTERNO]

   ├─ TRUNCATE AD_NOTASITEMPROMARGEMBI  [EXTERNO]

   ├─ TRUNCATE AD_BMCPRECOENTRADA       [EXTERNO]

   ├─ INSERT AD_BMCPRECOENTRADA

   │     └─ VW_BMC_GETPRECOENTRADA      [EXTERNO]

   ├─ STP_ARG_PROCESS_AD_TGFITECOMPL()  [EXTERNO]

   ├─ CURSOR c_margem_bi

   │     └─ VW_BMC_BI_BASE_ITENS_V9  ──►  VW_NOTAS_31  ──►  (dados Sankhya)

   │           └─ SEQ_NOTASITEMPROMARGEMBI  [EXTERNO]

   └─ DELETE/UPDATE por flag ATIVO em AD_NOTASITEMPROMARGEMBI
### 11. Pontos críticos
Consulta pesadíssima na origem: cada FETCH executa a VW_BMC_BI_BASE_ITENS_V9, que dispara múltiplas funções escalares e subconsultas correlacionadas por linha. Este é o gargalo dominante da procedure.
DELETE ... WHERE ATIVO='S' redundante após TRUNCATE (ver Seção 5).
Múltiplos COMMIT intermediários (após INSERT auxiliar, após a procedure, antes do LOOP, e no par delete/update). Se a procedure falhar no meio do LOOP, a tabela final fica parcialmente carregada e sem nenhuma linha ATIVO='S' → o Bs perde a base vigente. Não há transação atômica de publicação.
Ausência total de tratamento de exceção (EXCEPTION WHEN OTHERS). Qualquer erro aborta sem log próprio e sem rollback controlado.
BULK COLLECT de 1000 sem SAVE EXCEPTIONS: um erro de dado numa linha do lote aborta o lote inteiro.
DDL implícito (TRUNCATE/EXECUTE IMMEDIATE) dá commit implícito e pode disparar bloqueios de library cache se houver sessão lendo a tabela (padrão de trava que você já enfrentou no DBeaver).
### 12. Sugestões de melhoria
Performance: avaliar substituir o cursor + FORALL por um único INSERT /*+ APPEND */ INTO AD_NOTASITEMPROMARGEMBI SELECT ... FROM VW_BMC_BI_BASE_ITENS_V9. Com direct-path e sem PL/SQL round-trip, tende a ser bem mais rápido do que buscar 1000 em 1000 para o cliente PL/SQL. A PK pode vir de SEQ.NEXTVAL direto no SELECT (Oracle 12c+) ou de coluna IDENTITY.
Atomicidade de publicação: se quiser manter o padrão por flag, remover o TRUNCATE e fazer de verdade o blue-green (carrega 'N', num único bloco: DELETE 'S' + UPDATE 'N'→'S' + COMMIT). Ou usar ALTER TABLE ... EXCHANGE PARTITION / rename swap. Hoje o snapshot fica indisponível durante a recarga.
Robustez: adicionar EXCEPTION com RAISE/log em tabela de auditoria (ex.: AD_LOG_CARGA_BI com início, fim, linhas, erro). Considerar FORALL ... SAVE EXCEPTIONS.
Manutenção: extrair o mapa de colunas (são >120) para um %ROWTYPE/insert por nome já é feito; documentar a ordem esperada e travar com testes de contagem/soma pós-carga (reconciliação).
Segurança: confirmar que TRUNCATE está coberto por rotina de recuperação (não há backup lógico intra-execução).
### 13. Resumo executivo (para analista funcional)
Esta rotina é o "botão de atualizar" do painel de margem. Ela pega tudo o que a view de margem calcula (receita, custos, comissões, royalties, provisões e a margem final por caixa/nota) e grava numa tabela pronta para o BI ler rápido. Antes de gravar, ela atualiza algumas tabelas de apoio (devoluções e custo médio) para os números saírem corretos. No fim, ela "publica" a versão nova marcando as linhas como ativas. É o que garante que o painel de margem mostre os dados do dia. Hoje, se der erro no meio, o painel pode ficar sem base — é o principal ponto de atenção.

## OBJETO 2 — SANKHYA.VW_BMC_BI_BASE_ITENS_V9 (View)
### 1. Resumo
Objetivo: calcular, por item de nota de venda, a margem de contribuição da operação de exportação/venda de frutas, consolidando receita líquida, todos os componentes de custo (MP, embalagem, frete, portuárias, seguro, royalties, comissões, provisões) e derivando margem em valor e em percentual, com regras específicas por fruta (MANGA, UVA, AVOCADO, LIMÃO e "demais").

Problema de negócio: cada fruta/mercado tem estrutura de custo e regra de provisionamento diferente (ficha de custo x custo calculado, com/sem provisão de fornecedor, tratamento de frete conforme incoterm). Esta view centraliza toda essa lógica num único ponto para alimentar o BI de rentabilidade.
### 2. Fluxo de execução
A view é uma pirâmide de 3 níveis de subconsulta:

N1 (base): lê VW_NOTAS_31 e monta, por item, os componentes brutos: receita bruta, descontos, devoluções (realocação 1228 / perda 1227 / outras), fretes (marítimo, rodoviário, aéreo) conforme incoterm, custos de ficha (VW_BMC_BI_CUSTOS_PROD_OTM), perda de pack, seguro/crédito, despesas portuárias, provisão de fornecedor e chamadas às funções de royalties/comissão/custo geral.
N2 (intermediária): a partir de N1, calcula vlr_receita_liq1, custo_calculado, CUSTOTOTALGER, CUSTOTOTALGERC, MARGEMGER e PERCMARGEMGER — já com as regras por fruta e a exclusão de PROCESSO = 'REFUGO MP'.
N3 / projeção externa: re-expõe as colunas e recalcula por cima alguns indicadores (preco_venda_moeda, custo_mp_caixa, vlr_margem, perc_margem, PROVISAO_FORNECEDOR_GER, e novamente CUSTOTOTALGER/CUSTOTOTALGERC/MARGEMGER/PERCMARGEMGER), aplicando as funções de provisão/etiqueta na camada de saída.

⚠️ Vários indicadores (CUSTOTOTALGER, MARGEMGER, PERCMARGEMGER, PROVISAO_FORNECEDOR_GER) são calculados em dois níveis (N2 e projeção externa) com fórmulas diferentes. A versão da camada externa é a que sai no resultado. Isso é fonte recorrente de confusão — ver Seção 11.
### 3. Entradas
View não recebe parâmetros. As "entradas" são as colunas de VW_NOTAS_31 (ver Objeto 3). Filtros/agrupamentos por fruta usam a coluna FRUTA e por incoterm usam INCONTERMS.
### 4. Saídas
Projeta ~130 colunas. Principais grupos e significado:

| Coluna | Significado |
|---|---|
| REGRA, SEMANA, ANO, MES, DATA | Dimensões temporais/regra. |
| FRUTA, VARIEDADE, VARIEDADEMP, CODVARIEDADE | Dimensão de produto/variedade. |
| NUNOTA, NF, CONTROLE, NROPALLET, ROMANEIO, LOTEARGO | Chaves de rastreabilidade do item/pallet. |
| CODPARC, NOME_CLIENTE, CODPRODUTOR, NOMEPRODUTOR | Cliente e produtor. |
| MOEDA, VLR_COTACAO, INCONTERMS, PAIS | Comercial/exportação. |
| RECEITA_BRUTA_MOE, PRECO_VENDA_MOEDA | Receita e preço em moeda estrangeira. |
| VLR_RECEITA_BRUTA_TOTAL, VLR_RECEITA_LIQ1 | Receita bruta (com frete) e receita líquida. |
| DESCONTO_COMERCIAL, DESCONTO_CONTRATUAL, DEVOLUCAO_REALOCACAO, DEVOLUCAO_PERDA, VLR_OUTRAS_DEV | Deduções de receita. |
| CUSTO_MP, CUSTOMEDIO, CUSTO_MP_CAIXA, CUSTO_EMBALAGEM, FRETE_*, DESP_PORTUARIAS, SEGURO_CRED, PERDA_PACK, CUSTOS_SERVICOS, CUSTO_OPERACAO | Componentes de custo. |
| VLR_ROYALTIES, VLR_COM_VENDA_COM, VLR_COM_VENDA_TERC, PROVISAO_FORNECEDORES, VLR_PROV_FORN | Royalties, comissões e provisões. |
| CUSTO_CALCULADO | Soma de custos "método calculado". |
| CUSTOTOTALGER | Custo total gerencial (usa CUSTO_MP). |
| CUSTOTOTALGERC | Variante do custo total gerencial usando CUSTOMEDIO. |
| VLR_MARGEM, PERC_MARGEM | Margem "simples" (receita líq − custo calculado). |
| MARGEMGER, PERCMARGEMGER | Margem gerencial (regra por fruta; REFUGO MP → 0). |
| TXADM_CUSTO_GER, CUSTOUNITARIOGER | Taxa administrativa e custo unitário gerencial. |
| STATUS_COMERCIAL, ETD/ETA/ETDR/ETAR, VESSEL, BOOKING, LINER, PORTO_*, AD_EX_CONTAINER | Logística/comercial. |
| OPEN_AMOUNT, CREDIT_MOE, DEBIT_MOE | Financeiro (aberto, crédito/débito em moeda). |

### 5. Regras de negócio
Principais condicionais (CASE/IF):

Preço de venda em moeda: RECEITA_BRUTA_MOE / NULLIF(vlr_cotacao,0) — protege contra divisão por zero.
Custo MP por caixa: custo_mp / NULLIF(total_cx,0).
Receita bruta total inclui frete: vlr_receita_bruta_total + receita_frete.
Frete conforme incoterm: quando INCONTERMS IN ('CIF','CIP','CPT') o frete é tratado como receita/embutido; fora disso, entra como custo (frete_rodoviario + frete_maritimo + frete_aereo). Aparece repetidamente em custo total e margem.
vlr_margem: para FRUTA IN ('AVOCADO','UVA','LIMÃO') → receita_liq − custo_calculado − FU_BMC_GETPROVFORN(...); senão → receita_liq − custo_calculado.
perc_margem: (margem / NULLIF(receita_liq,0)) * 100, com COALESCE(...,0).
CUSTOTOTALGER por fruta:
MANGA: etiqueta + frete-ger + (frete se não CIF/CIP/CPT) + custo unit×caixas + desconto + CUSTO_MP + portuárias + seguro + provisão fornecedor + perda pack.
UVA: CUSTO_MP + etiquetas/fretes + portuárias + seguro + custo unit×caixas + desconto + royalties + comissão terceiros.
Demais: custo_calculado + etiquetas + custo unit×caixas + desconto.
Sempre soma FUN_ARG_VLRETIQSRV(nropallet)*total_cx.
CUSTOTOTALGERC: idêntico ao CUSTOTOTALGER, mas troca CUSTO_MP por CUSTOMEDIO (visão de custo médio).
MARGEMGER (camada externa):
MANGA: receita líq − custo total específico da manga.
FRUTA NOT IN ('AVOCADO','UVA','LIMÃO'): receita líq − (custo calculado + etiquetas + custo unit×caixas + desconto + etiqueta serviço).
senão: (receita_liq * PERCMARGEMGER)/100.
PERCMARGEMGER: MARGEMGER / NULLIF(receita_liq,0) * 100, com regra especial para MANGA e para "não provisiona" (usa FU_BMC_GETPERCCOMVENDA), e PROCESSO = 'REFUGO MP' força 0.
PROVISAO_FORNECEDOR_GER: só para AVOCADO e para UVA com prv='S'; senão 0.
status_comercial: NVL(STCOM,' ').
### 6. Cálculos
Receita líquida (vlr_receita_liq1) — o núcleo de tudo (calculado em N2):

vlr_receita_liq1 =

  ( vlr_receita_bruta_total

    + receita_complementar

    + (CASE WHEN inconterms IN ('CIF','CIP','CPT') THEN 0 ELSE receita_frete END)

    + teste_debit )

  - ( vlr_desc_com

      + devolucao_realocacao

      + devolucao_perda

      + outras_devolucoes

      + teste_credit )

Origem dos valores: vlr_receita_bruta_total = vlr_preco_venda × qtd; receita_frete, devoluções e testes de crédito/débito vêm de VW_NOTAS_31.

Exemplo (FOB, sem frete embutido): receita bruta 10.000 + complementar 0 + frete 500 (FOB entra como receita) + débito 0 − (desc 200 + dev.realoc 300 + dev.perda 0 + outras 100 + crédito 0) = 9.900.

Margem simples (vlr_margem) para fruta com provisão (ex.: AVOCADO):

vlr_margem = vlr_receita_liq1 − custo_calculado − FU_BMC_GETPROVFORN(...)

Ex.: 9.900 − 7.000 − 400 = 2.500. perc_margem = 2.500 / 9.900 × 100 ≈ 25,25%.

Custo total gerencial (CUSTOTOTALGER) — soma modular por fruta (ver Seção 5). Cada parcela vem de N1: CUSTO_MP (ficha VW_BMC_BI_CUSTOS_PROD_OTM ou CUSTO_MP_CALC), fretes (VW_BMC_FRETE_MARITIMO, TB_FRETES_* via VW_NOTAS_31), portuárias (VW_BMC_DESPESAS_PORTUARIAS), etiquetas (FUN_ARG_VLRETIQSRV, FUN_ARG_VLRETIQ), custo unitário geral (FU_BMC_PRECO_CUSTO_GER), royalties (FU_BMC_GETROYALTIES) e comissões (FU_BMC_GETCOMVENDA).

Custo MP (N1) — quando não há custo pré-calculado, busca o maior custo unitário na ficha e multiplica pelo peso:

CUSTO_MP = MAX( COALESCE(vlrcustocalibreunit, vlrcustoprecoentradaunit) )   -- de VW_BMC_BI_CUSTOS_PROD_OTM (mp='S')

           × (pesoliqpro × qtdbase)

Para MANGA usa CUSTOMEDIO × (pesoliqpro × qtdbase).
### 7. Dependências
| Tipo | Nome | Utilização | Está nos arquivos? |
|---|---|---|---|
| View | VW_NOTAS_31 | Fonte base (N1) | ✔ Sim |
| View | VW_BMC_BI_CUSTOS_PROD_OTM | Ficha de custo (MP, embalagem, direto, operação, serviço, colheita, imp. saldo) | ✖ [EXTERNO] |
| View | VW_BMC_BI_PERCA_PACK | Perda de pack | ✖ [EXTERNO] |
| View | VW_BMC_FRETE_MARITIMO | Frete marítimo (FR2) | ✖ [EXTERNO] |
| View | VW_BMC_DESPESAS_PORTUARIAS | Despesas portuárias (FR3) | ✖ [EXTERNO] |
| Function | FU_BMC_GETPROVFORN | Provisão de fornecedor | ✖ [EXTERNO] |
| Function | FU_BMC_GETROYALTIES | Royalties | ✖ [EXTERNO] |
| Function | FU_BMC_GETCOMVENDA | Comissão comercial/terceiros | ✖ [EXTERNO] |
| Function | FU_BMC_GETPERCCOMVENDA | % comissão comercial (usado em PERCMARGEMGER) | ✖ [EXTERNO] |
| Function | FU_BMC_GETCUSTOPREVISTO | Custos previstos DESC/ETIQ/CRED/ETIQREAL | ✖ [EXTERNO] |
| Function | FU_BMC_PRECO_CUSTO_GER | Custo unitário gerencial | ✖ [EXTERNO] |
| Function | FU_ARG_TXADM_CUSTO_GER | Taxa administrativa sobre custo geral | ✖ [EXTERNO] |
| Function | FUN_ARG_VLRETIQSRV | Valor etiqueta serviço | ✖ [EXTERNO] |
| Function | FUN_ARG_VLRETIQ | Valor etiqueta | ✖ [EXTERNO] |
| Tabela | AD_TGFGRUPATENTES | Parceiro-patente (codparcpatentemp) | ✖ [EXTERNO] |
| Tabela | AD_CUSTOSPREV | Custos previstos / OBS / status comercial | ✖ [EXTERNO] |
| Tabela | TCBLAN | Rateio de royalties (conta 205) | ✖ [EXTERNO] (Sankhya padrão) |
| Tabela | TGFITE / TGFPRO / TGFGRU | Base de rateio royalties por kg | ✖ [EXTERNO] (Sankhya padrão) |
| Tabela | TGFCAB / TGFITE / TGFVAR | Devoluções (tipoper 1227/1228) | ✖ [EXTERNO] (Sankhya padrão) |
| Tabela | DUAL | SELECT ... FROM DUAL de funções | (built-in) |

### 8. Objetos chamados
Views: VW_NOTAS_31, VW_BMC_BI_CUSTOS_PROD_OTM, VW_BMC_BI_PERCA_PACK, VW_BMC_FRETE_MARITIMO, VW_BMC_DESPESAS_PORTUARIAS.
Functions: FU_BMC_GETPROVFORN, FU_BMC_GETROYALTIES, FU_BMC_GETCOMVENDA, FU_BMC_GETPERCCOMVENDA, FU_BMC_GETCUSTOPREVISTO, FU_BMC_PRECO_CUSTO_GER, FU_ARG_TXADM_CUSTO_GER, FUN_ARG_VLRETIQSRV, FUN_ARG_VLRETIQ.
Tabelas: AD_TGFGRUPATENTES, AD_CUSTOSPREV, TCBLAN, TGFITE, TGFPRO, TGFGRU, TGFCAB, TGFVAR, DUAL.
Comentado (não chama): FU_BMC_GETCUSTOFRETEGER, FU_BMC_GETCUSTOFRETEGER/qtdnegnota (dentro de bloco /* */).
### 9. Objetos que provavelmente dependem desta view
STP_BMC_CARGA_MRG_BI_BASE (Objeto 1) — consumidor direto (confirmado).
Possíveis views V10+ ou relatórios que herdem desta base — não identificável apenas pelo código.
### 10. Diagrama textual de dependências
VW_BMC_BI_BASE_ITENS_V9

   ├─ VW_NOTAS_31  (fonte base — ver Objeto 3)

   ├─ VW_BMC_BI_CUSTOS_PROD_OTM     [EXTERNO]  (ficha de custo)

   ├─ VW_BMC_BI_PERCA_PACK          [EXTERNO]

   ├─ VW_BMC_FRETE_MARITIMO         [EXTERNO]

   ├─ VW_BMC_DESPESAS_PORTUARIAS    [EXTERNO]

   ├─ Functions [EXTERNO]:

   │     FU_BMC_GETPROVFORN, FU_BMC_GETROYALTIES, FU_BMC_GETCOMVENDA,

   │     FU_BMC_GETPERCCOMVENDA, FU_BMC_GETCUSTOPREVISTO,

   │     FU_BMC_PRECO_CUSTO_GER, FU_ARG_TXADM_CUSTO_GER,

   │     FUN_ARG_VLRETIQSRV, FUN_ARG_VLRETIQ

   └─ Tabelas: AD_TGFGRUPATENTES, AD_CUSTOSPREV, TCBLAN,

              TGFITE, TGFPRO, TGFGRU, TGFCAB, TGFVAR, DUAL
### 11. Pontos críticos
Cálculo duplicado em 2 níveis: CUSTOTOTALGER, MARGEMGER, PERCMARGEMGER, PROVISAO_FORNECEDOR_GER existem em N2 e na projeção externa, com fórmulas diferentes. Manutenção arriscada: alterar um nível sem o outro gera divergência silenciosa. Prioridade alta de consolidação.
Funções escalares chamadas repetidamente na mesma linha: FU_BMC_GETROYALTIES, FU_BMC_GETCOMVENDA('TERCEIROS'), FU_BMC_GETPROVFORN aparecem várias vezes dentro do mesmo item (uma vez no cálculo de custo, outra na margem, outra na provisão). Cada uma é uma subconsulta/round-trip — multiplica o custo de CPU por linha.
Subconsultas correlacionadas por linha contra VW_BMC_BI_CUSTOS_PROD_OTM (vários SELECT MAX/SUM ... WHERE nropallet=... AND lotemp=...) — repetidas por componente de custo (mp, embalagem, direto MI, direto ME, operação, serviço, colheita, imp. saldo). Candidato a consolidar num único join agregado por pallet.
Repetição do bloco de incoterm (frete marítimo/aéreo/rodoviário) copiado em dezenas de CASE — risco de divergência entre cópias (ex.: alguns usam 'CIF','CIP','CPT','FOB', outros só 'CIF','CIP','CPT').
FUN_ARG_VLRETIQSRV(to_number(nropallet)): TO_NUMBER sobre nropallet — se algum pallet não for numérico, estoura ORA-01722.
Vários blocos comentados (versões antigas de CUSTOTOTALGER/MARGEMGER) inflam o código e dificultam leitura.
### 12. Sugestões de melhoria
Consolidar o cálculo num único nível. Manter apenas N2 ou a projeção externa como fonte de verdade dos indicadores gerenciais; a outra apenas repassa. Elimina o risco de divergência.
Materializar a ficha de custo por pallet (VW_BMC_BI_CUSTOS_PROD_OTM) num agregado único (GROUP BY nropallet, codprodutor, lotemp) e fazer LEFT JOIN uma vez, em vez de ~8 subconsultas escalares correlacionadas.
Encapsular a lógica de frete-por-incoterm numa função determinística ou coluna intermediária única, para não replicar o CASE dezenas de vezes.
Marcar funções como DETERMINISTIC (quando aplicável) e/ou usar WITH ... FUNCTION/scalar subquery caching para reduzir chamadas repetidas.
Limpeza: remover blocos comentados obsoletos (mover para histórico em Git).
Blindar TO_NUMBER(nropallet) com CASE WHEN REGEXP_LIKE(nropallet,'^[0-9]+$') (padrão que você já usa em VW_NOTAS_31 — aplicar aqui também).
### 13. Resumo executivo (para analista funcional)
Esta view é a "calculadora de margem" da empresa. Para cada item vendido, ela junta quanto entrou (receita, já descontando devoluções e descontos) e quanto custou (matéria-prima, embalagem, fretes, portos, seguro, royalties, comissões e provisões), e devolve a margem em reais e em percentual. Ela sabe que cada fruta tem regra diferente: manga, uva, avocado e limão são tratadas de formas distintas das demais, e itens de "refugo de MP" não entram no cálculo de margem. É o coração dos números do painel de rentabilidade — e, hoje, é também o objeto mais pesado e mais difícil de manter do stack.

## OBJETO 3 — SANKHYA.VW_NOTAS_31 (View)
Revisão (rev. 2): colisão de alias Q3/Q4/Q5 corrigida (CTEs renomeados para QNOTA/QCEN/QCAL/QCTR/QFOR/QPRV/QPAT/QVAR/QNFMP), datas convertidas para literal ANSI (DATE '2025-12-18' / DATE '2026-06-01') e código morto removido. Equivalência funcional validada contra produção. As seções abaixo já refletem a versão corrigida.

Revisão (rev. 3 — 05/07/2026, versão VW_NOTAS_31_2): refatoração de performance + duas mudanças funcionais. Performance: MATERIALIZE reposto em 17 CTEs (estabiliza plano — havia spill de TEMP de 150–270 MB quando removido); índice IX_TGFCAB_AD_NUNOTASUB criado e em uso; nova CTE DEV_ITEM (devolução por item) e DEV_NOTA (devolução por nota), ambas filtrando TIPMOV='D' AND STATUSNOTA='L'. Mudanças funcionais (afetam número — exigem reconciliação): (1) coluna PERCDESCCONTRATUAL passou a vir da nova CTE PDESC (AD_CTRLDESCOM, desconto contratual mais recente por cliente); (2) nova coluna VLR_DESC_FIN_SDEV (desconto financeiro líquido de devolução por nota). Neutros: DEV_ITEM sem REFUGO (distinção vem de VW_BMC_GET_QTD_DEV_VENDA2) e TIPMOV='V' no QTDNEG_POR_NUNOTA (redundante com a query principal). Não publicar sem reconciliar PERCDESCCONTRATUAL e VLR_DESC_COM (além de QTDNEGNOTA/VLRTOTNOTA/QTDDEVVENDA) nova × produção. Ganho de tempo de execução ainda não medido. Ver LOG DE PROGRESSO na Revisão Técnica.
### 1. Resumo
Objetivo: montar a base de itens de notas de venda (uma linha por item/pallet de venda) com todos os atributos comerciais, logísticos e de custo necessários para o cálculo de margem — incluindo quantidades líquidas de devolução, rateios de crédito/débito, fretes históricos, custo médio e vínculos de romaneio/matéria-prima.

Problema de negócio: os dados de venda estão espalhados por dezenas de tabelas Sankhya (cabeçalho, item, produto, parceiro, cidade/UF/país, TOP, natureza, centro de custo, moeda, comissão, veículo, porto) e por tabelas customizadas (AD_TGFITECOMPL, romaneios, fretes históricos). Esta view unifica tudo e já entrega as quantidades líquidas de devolução e os rateios corretos, servindo de fundação para VW_BMC_BI_BASE_ITENS_V9.
### 2. Fluxo de execução
Bloco WITH (13 CTEs) — pré-agregações materializadas (/*+ MATERIALIZE */):
QTDNEG_POR_NUNOTA, ITE_LIQ, QTDNEG_POR_FORN, QTDNEG_POR_CENCUS, QTDNEG_POR_CALIBRE, QTDNEG_POR_CONTROLE: quantidades líquidas de devolução em diferentes granularidades.
VLRPROVFORN_POR_CENCUS: provisão de fornecedor por centro de custo.
PARC_PATENTE, VARIEDADE_MP, NF_ENT_MP: vínculos de patente, variedade de MP e NF de entrada por romaneio.
PED_FRETE_VENDAS, PED_DESP_LOG: pedidos pendentes de frete e despesa logística por projeto.
ITE_BASE: AD_TGFITECOMPL já com ROMANEIO_NUM (romaneio convertido para número quando numérico).
SELECT principal: parte de TGFCAB (CAB) + ITE_BASE (ITE) e faz ~40 joins para trazer produto, grupo, cliente/produtor, cidade/UF/país, TOP, natureza, centro de custo, fruta, projeto, moeda, comissão, navio, portos, devoluções, custo médio semanal, fretes históricos, crédito/débito e desconto financeiro.
Regras de negócio no SELECT: define PROCESSO (REFUGO PA/MP, transferências), MERCADO (MI/ME), INCONTERMS, quantidades líquidas (QTDNEG, QTDBASE), rateios de débito/crédito por controle e por calibre, e o ajuste de spread de risco (AD_PERCSPREADRISCO).
WHERE: exclui parceiros internos, notas em AD_NOTASEXC, notas substituídas/creditadas e mantém apenas itens com quantidade líquida > 0.
### 3. Entradas
View sem parâmetros. Filtros embutidos relevantes:

CAB.CODPARC NOT IN (10049,15839) (parceiros excluídos).
TOP.GRUPO = 'VENDAS' e TOP.AD_CRE_DEB = 'X'.
CAB.CHAVENFE IS NOT NULL.
Datas fixas em CTEs: PED_FRETE_VENDAS (DATE '2025-12-18'), PED_DESP_LOG (DATE '2026-06-01'). Literais ainda embutidos no código (candidatos a parâmetro), mas já em formato ANSI independente de NLS.
### 4. Saídas
~130 colunas. Grupos principais:

| Coluna | Significado |
|---|---|
| SEMANA, ANO, MES, DATA, DTENTSAI, DTENTROM | Temporais. |
| PROCESSO | Classificação: projeto, REFUGO PA/MP, transferência entre filiais. |
| FRUTA, CODFRUTA, VARIEDADE, VARIEDADEMP, CODPRODCX | Produto/variedade. |
| NUNOTA, NF, SEQUENCIA, CONTROLE, NROPALLET, LOTEARGO, LOTEMP, ROMANEIO | Rastreabilidade. |
| CODPRODUTOR, NOMEPRODUTOR, CODPARC, NOME_CLIENTE | Produtor/cliente (com marcação (R) de realocação). |
| MERCADO (MI/ME), INCONTERMS, PAIS, CODPAIS, AD_MODAL, CIF_FOB | Comercial/exportação. |
| MOEDA, VLR_COTACAO, VLR_PRECO_VENDA, VLR_KG | Preço/moeda. |
| QTDPALLET, QTDNEG, QTDNEGITE, QTDBASE, QTDDEVVENDA, QTDNEGNOTA, QTDNEGCENCUS | Quantidades (brutas e líquidas de devolução). |
| VLR_TOTAL_CX_LIQUIDA, VLRNOTA, VLR_DESC_COM, VLR_OUTRAS_DEV | Valores de venda/dedução. |
| CUSTO_MP_CALC, CUSTOMEDIO | Custo MP pré-calculado / custo médio semanal (VW_M_CUSTOMED_SEMANA). |
| VLRPROVFORN | Provisão de fornecedor por centro de custo. |
| PERCDESCCONTRATUAL, DESCFIN | Descontos contratuais/financeiros. |
| DB_VLRTOT, CR_VLRTOT, DB_VLRTOTMOE, CR_VLRTOTMOE | Rateios de débito/crédito (por controle e por calibre). |
| PERCENTUAL | Percentual de rateio da NF (via VW_PERCPROC_NF_V4). |
| OPEN_AMOUNT, CVLRNOTA, DVLRNOTA, CVLRMOEDAEX, DVLRMOEDAEX | Financeiro (aberto e crédito/débito por projeto). |
| VLRCTE, VLRFRMA, FRUVLRFR, PED_FR, PED_LOG | Fretes (histórico, marítimo, rural, pedidos pendentes). |
| ETD/ETA/ETDR/ETAR, VESSEL, PORTO_*, AD_EX_BOOKING, AD_LINER, LOC_ENT | Logística. |
| AD_PERCSPREADRISCO, DIF_SPREAD | Ajuste de spread de risco sobre o valor. |

### 5. Regras de negócio
Classificação PROCESSO: se natureza contém REFUG e sem projeto → REFUGO PA (controle tipo ____-____%) ou REFUGO MP (demais); se TRANSF sem projeto → 0-TRANSFERENCIAS ENTRE FILIAIS; senão usa REFERENCE_NO.
MERCADO: país 55 (Brasil) e sem data prevista de embarque → MI; senão ME.
INCONTERMS: deriva CIF/FOB a partir de CIF_FOB/TIPFRETE quando é Brasil sem embarque; senão usa AD_INCOTERM.
Quantidade líquida (QTDBASE, QTDNEG): quantidade original menos devolução (VW_BMC_GET_QTD_DEV_VENDA*), com proporcionalização.
VLR_TOTAL_CX_LIQUIDA: valor da caixa removendo o spread de risco (/(AD_PERCSPREADRISCO/100 + 1)).
ROYALT: AD_ROYALTS do grupo (default 'N').
Rateio débito/crédito: por CONTROLE (CD_ITE, consolidação CT) e por CALIBRE/FORNECEDOR (CD_ITE2, CL), proporcionalizado pela quantidade.
VLRCTE (frete rodoviário histórico): zerado para projeto 0/4110260175 e processos com sufixo %._; senão frete de TB_FRETES_HST.
CUSTOMEDIO: vem de VW_M_CUSTOMED_SEMANA casando semana de entrada + produto MP + calibre (ou 'MG').
VLR_DESC_COM: desconto do item (proporcional à quantidade) + desconto financeiro proporcional (VW_DESCFIN).
Filtros WHERE: exclui parceiros que são empresas do grupo (VW_TGFPARC_TGFEMP), notas em AD_NOTASEXC, notas com AD_NUNOTACREF/AD_NUNOTASUB (substituições).
### 6. Cálculos
Quantidade líquida por nota (QTDNEG_POR_NUNOTA):

QTDNEGNOTA = SUM(NVL(AD_QTDNEGOR, QTDNEG)) - SUM(NVL(V_QTDDEV,0))

VLRTOTNOTA = SUM(VLRTOT) - (SUM(V_QTDDEV) × SUM(VLRUNIT))

Origem: TGFITE + devoluções de VW_BMC_GET_QTD_DEV_VENDA.

Valor líquido da caixa sem spread (VLR_TOTAL_CX_LIQUIDA):

VLR_TOTAL_CX_LIQUIDA =

   (ITE.VLRTOT / (AD_PERCSPREADRISCO/100 + 1))

 - (V_QTDDEV × (ITE.VLRUNIT / (AD_PERCSPREADRISCO/100 + 1)))

Ex.: VLRTOT 1.050, spread 5% → 1.050/1,05 = 1.000. DIF_SPREAD guarda a diferença (50).

Rateio de débito por controle (DB_VLRTOT):

DB_VLRTOT = (NVL(CD_ITE.DB_VLRTOT,0) / QCTR.QTDNEGCONTROLE) × ITE.QUANTITY

          + NVL((CD_ITE2.DB_VLRTOT1 / QCAL.QTDNEGCALIBRE) × ITE.QUANTITY, 0)

Distribui o débito consolidado (por controle) e o débito por calibre proporcionalmente à quantidade do item.

Semana ISO (SEMANA):

SEMANA = 1 + TRUNC( (TRUNC(dtentsai) - TRUNC(TRUNC(dtentsai,'YYYY'),'IW')) / 7 )
### 7. Dependências
Tabelas Sankhya padrão:

| Tipo | Nome | Utilização | Nos arquivos? |
|---|---|---|---|
| Tabela | TGFCAB | Cabeçalho da nota | ✖ padrão |
| Tabela | TGFITE | Item da nota (ITEO / CTEs) | ✖ padrão |
| Tabela | TGFPRO | Produto | ✖ padrão |
| Tabela | TGFGRU | Grupo de produto/variedade | ✖ padrão |
| Tabela | TGFPAR | Parceiro (cliente/produtor) | ✖ padrão |
| Tabela | TSICID / TSIUFS / TSIPAI | Cidade / UF / País | ✖ padrão |
| Tabela | TGFTOP | Tipo de operação | ✖ padrão |
| Tabela | TGFNAT | Natureza | ✖ padrão |
| Tabela | TSICUS | Centro de custo | ✖ padrão |
| Tabela | TCSPRJ | Projeto | ✖ padrão |
| Tabela | TSIMOE | Moeda | ✖ padrão |
| Tabela | TGFCOM | Comissão | ✖ padrão |
| Tabela | TGFVEI | Veículo/navio | ✖ padrão |
| Tabela | TGFVAR | Variação/vínculo de nota | ✖ padrão |

Tabelas/objetos customizados (AD_/ARG_/TB_):

| Tipo | Nome | Utilização | Nos arquivos? |
|---|---|---|---|
| Tabela | AD_TGFITECOMPL | Base de itens (ITE_BASE) | ✖ [EXTERNO] |
| Tabela | AD_TGFGRUPATENTES | Parceiro-patente | ✖ [EXTERNO] |
| Tabela | AD_ROMANEIOENTR | Romaneio de entrada (LOC_ENT, variedade MP) | ✖ [EXTERNO] |
| Tabela | AD_ROMANEIOENTFAT | Faturamento de romaneio (NF entrada MP) | ✖ [EXTERNO] |
| Tabela | AD_FRUTA | Cadastro de fruta | ✖ [EXTERNO] |
| Tabela | AD_PORTO | Portos | ✖ [EXTERNO] |
| Tabela | AD_NOTASEXC | Notas excluídas do BI | ✖ [EXTERNO] |
| Tabela | TB_FRETES_HST | Frete rodoviário histórico | ✖ [EXTERNO] |
| Tabela | TB_FRETES_MARITIMO_HST | Frete marítimo histórico | ✖ [EXTERNO] |
| Tabela | ARG_COMPRA_MP | Compra de MP (custo/complementos) | ✖ [EXTERNO] |
| Tabela | ARG_FRETES_RURALVD | Frete rural de venda | ✖ [EXTERNO] |

Views:

| Tipo | Nome | Utilização | Nos arquivos? |
|---|---|---|---|
| View | VW_BMC_GET_QTD_DEV_VENDA | Devolução por item/sequência | ✖ [EXTERNO] |
| View | VW_BMC_GET_QTD_DEV_VENDA_FOR | Devolução por fornecedor | ✖ [EXTERNO] |
| View | VW_BMC_GET_QTD_DEV_VENDA2 | Devolução por romaneio | ✖ [EXTERNO] |
| View | VW_BMC_BI_PROV_FORNECEDORES | Provisão de fornecedor | ✖ [EXTERNO] |
| View | VW_TGFCAB_ITE | Cabeçalho+item (pedidos frete/log) | ✖ [EXTERNO] |
| View | VW_PERCPROC_NF_V4 | % rateio processo/NF | ✖ [EXTERNO] |
| View | VW_AD_REC_COMD | Valor em aberto (OPEN_AMOUNT) | ✖ [EXTERNO] |
| View | VW_ARG_CRE_DEB | Crédito/débito por projeto (moeda) | ✖ [EXTERNO] |
| View | VW_DESCFIN | Desconto financeiro proporcional | ✖ [EXTERNO] |
| View | VW_ARG_DEB_CRE_ITE | Débito/crédito por item (CT/CL) | ✖ [EXTERNO] |
| MView | VW_M_CUSTOMED_SEMANA | Custo médio semanal (também no Objeto 1) | ✖ [EXTERNO] |
| View | VW_TGFPARC_TGFEMP | Parceiros que são empresas do grupo | ✖ [EXTERNO] |
| Function | F_DESCROPC | Descrição de opção (TIPOPARCERIA) — Sankhya padrão | ✖ padrão |

### 8. Objetos chamados
Views/MViews [EXTERNO]: as 12 listadas acima (VW_BMC_GET_QTD_DEV_VENDA, ..._FOR, ...2, VW_BMC_BI_PROV_FORNECEDORES, VW_TGFCAB_ITE, VW_PERCPROC_NF_V4, VW_AD_REC_COMD, VW_ARG_CRE_DEB, VW_DESCFIN, VW_ARG_DEB_CRE_ITE, VW_M_CUSTOMED_SEMANA, VW_TGFPARC_TGFEMP).
Functions: F_DESCROPC (Sankhya).
Tabelas: todas as das tabelas Sankhya + customizadas listadas na Seção 7.
### 9. Objetos que provavelmente dependem desta view
VW_BMC_BI_BASE_ITENS_V9 (Objeto 2) — consumidor direto (confirmado).
Indiretamente, STP_BMC_CARGA_MRG_BI_BASE e todo o BI a jusante.
Possíveis versões paralelas (VW_NOTAS_30 aparece comentada no Objeto 1).
### 10. Diagrama textual de dependências
VW_NOTAS_31

   ├─ CTEs (WITH) sobre:

   │     TGFITE, TGFCAB, AD_TGFITECOMPL          [padrão/EXTERNO]

   │     VW_BMC_GET_QTD_DEV_VENDA / _FOR / _2    [EXTERNO]

   │     VW_BMC_BI_PROV_FORNECEDORES             [EXTERNO]

   │     AD_TGFGRUPATENTES, AD_ROMANEIOENTR,

   │     AD_ROMANEIOENTFAT, VW_TGFCAB_ITE        [EXTERNO]

   ├─ SELECT principal:

   │     TGFCAB ─ AD_TGFITECOMPL ─ TGFITE ─ TGFPRO ─ TGFGRU ─ TGFPAR

   │     ─ TSICID ─ TSIUFS ─ TSIPAI ─ TGFTOP ─ TGFNAT ─ TSICUS

   │     ─ AD_FRUTA ─ TCSPRJ ─ TSIMOE ─ TGFCOM ─ TGFVEI ─ AD_PORTO

   ├─ Fretes/custos [EXTERNO]:

   │     TB_FRETES_HST, TB_FRETES_MARITIMO_HST, ARG_FRETES_RURALVD,

   │     ARG_COMPRA_MP, VW_M_CUSTOMED_SEMANA

   ├─ Financeiro [EXTERNO]:

   │     VW_AD_REC_COMD, VW_ARG_CRE_DEB, VW_ARG_DEB_CRE_ITE,

   │     VW_DESCFIN, VW_PERCPROC_NF_V4

   └─ Filtros [EXTERNO]: AD_NOTASEXC, VW_TGFPARC_TGFEMP
### 11. Pontos críticos
✅ COLISÃO DE ALIAS — CORRIGIDA E VALIDADA. A versão anterior reusava Q3/Q4/Q5 para dois CTEs cada, tornando as referências ambíguas. Foi resolvida renomeando os 9 CTEs para nomes semânticos — QNOTA (por nota), QCEN (por centro), QCAL (por calibre), QCTR (por controle), QFOR (por fornecedor), QPRV (provisão fornecedor), QPAT (parceiro-patente), QVAR (variedade MP), QNFMP (NF entrada MP) — com cada coluna apontando para o CTE correto (mapeamento inequívoco por nome de coluna). Equivalência funcional validada contra produção. Mantido aqui como histórico: era o item nº 1 de risco do stack.
Datas em literal ANSI em PED_FRETE_VENDAS (DATE '2025-12-18') e PED_DESP_LOG (DATE '2026-06-01'): a view ainda "esquece" pedidos anteriores a essas datas (corte intencional), mas o formato agora é NLS-independente. Continua candidato a externalizar para tabela de parâmetro.
Muitas subconsultas escalares e funções por linha (fretes, custo médio, comissões) — mesmo padrão de peso do Objeto 2.
Dependência de VW_M_CUSTOMED_SEMANA: se a procedure (Objeto 1) não tiver dado refresh, o CUSTOMEDIO sai defasado — acoplamento de ordem de execução.
NOT EXISTS múltiplos no WHERE (contra AD_NOTASEXC, VW_TGFPARC_TGFEMP, tgfcab de substituição) — anti-joins que podem pesar sem índice adequado.
Duplicação do CASE de PROCESSO (REFUGO PA/MP/TRANSFERÊNCIA) — a classificação aparece na coluna PROCESSO e de novo dentro do CASE de VLRCTE. Ainda pendente: extrair para uma CTE de classificação (mexer em 2 lugares se a regra mudar).
### 12. Sugestões de melhoria
Resolver a colisão de alias — ✅ feito e validado (ver Seção 11).
Limpar código morto — ✅ feito (comentários CASE ROMANEIO e filtro de ano removidos; joins usam ITE.ROMANEIO_NUM).
Parametrizar as datas dos CTEs de pedidos (externalizar DATE '2025-12-18' / DATE '2026-06-01' para tabela de parâmetro que retorne o mesmo valor).
Extrair a classificação de PROCESSO para uma CTE única, eliminando a duplicação do CASE (pendência remanescente).
Consolidar as views de devolução (_VENDA, _FOR, _2) se compartilham lógica — reduz manutenção em 3 lugares.
Índices dos anti-joins: verificado no dicionário — AD_NOTASEXC(CODPROJ) e (NUNOTA) já existem; falta apenas criar ix_tgfcab_ad_nunotasub em TGFCAB(AD_NUNOTASUB).
Documentar a dependência de ordem com o refresh de VW_M_CUSTOMED_SEMANA (Objeto 1 já faz isso, mas convém deixar explícito).
### 13. Resumo executivo (para analista funcional)
Esta view é a "planilha mestre de vendas" do BI. Ela pega cada item vendido e devolve tudo pronto: cliente, produtor, fruta, mercado (interno/externo), incoterm, quantidades já descontadas de devolução, preço, fretes, custo médio e os rateios de crédito/débito — servindo de base para a calculadora de margem. Em outras palavras, é a camada que "limpa e organiza" os dados brutos do Sankhya antes de qualquer cálculo de rentabilidade. O ponto de atenção mais urgente é técnico: há apelidos de tabela repetidos no código que precisam ser revistos para garantir que a view compile e rode de forma previsível.

SEÇÃO FINAL — Lista de dependências para você trazer
Objetos referenciados pelos 3 arquivos mas não presentes neles. Priorizados por relevância para a lógica de negócio (os padrão Sankhya TGF*/TSI*/TCS* têm estrutura conhecida e ficam por último).
🔴 Prioridade ALTA — funções de cálculo (definem os números da margem)
Traga o corpo (CREATE OR REPLACE FUNCTION ...) de:

FU_BMC_GETPROVFORN
FU_BMC_GETROYALTIES
FU_BMC_GETCOMVENDA
FU_BMC_GETPERCCOMVENDA
FU_BMC_GETCUSTOPREVISTO
FU_BMC_PRECO_CUSTO_GER
FU_ARG_TXADM_CUSTO_GER
FUN_ARG_VLRETIQSRV
FUN_ARG_VLRETIQ
🔴 Prioridade ALTA — views de custo/ficha (parcelas de custo)
VW_BMC_BI_CUSTOS_PROD_OTM  ← a mais crítica (ficha de custo por pallet)
VW_BMC_BI_PERCA_PACK
VW_BMC_FRETE_MARITIMO
VW_BMC_DESPESAS_PORTUARIAS
VW_BMC_BI_PROV_FORNECEDORES
🟠 Prioridade MÉDIA — views de quantidade/devolução e financeiro
VW_BMC_GET_QTD_DEV_VENDA
VW_BMC_GET_QTD_DEV_VENDA_FOR
VW_BMC_GET_QTD_DEV_VENDA2
VW_ARG_DEB_CRE_ITE
VW_ARG_CRE_DEB
VW_DESCFIN
VW_PERCPROC_NF_V4
VW_AD_REC_COMD
VW_TGFCAB_ITE
VW_TGFPARC_TGFEMP
VW_BMC_GETPRECOENTRADA (usada pela procedure)
🟠 Prioridade MÉDIA — materialized views (impactam refresh/ordem)
VW_M_CUSTOMED_SEMANA (definição da MV + o SELECT base)
VW_M_NFVENDAS_DEVINT
VW_M_CONTROLE_VLRMP
🟡 Prioridade MÉDIA/BAIXA — procedure auxiliar e sequence
STP_ARG_PROCESS_AD_TGFITECOMPL (procedure)
SEQ_NOTASITEMPROMARGEMBI (definição da sequence)
🟡 Tabelas customizadas (estrutura — DDL/colunas)
AD_NOTASITEMPROMARGEMBI (destino — para validar mapa de colunas)
AD_BMCPRECOENTRADA
AD_TGFITECOMPL
AD_CUSTOSPREV
AD_TGFGRUPATENTES
AD_ROMANEIOENTR
AD_ROMANEIOENTFAT
AD_FRUTA
AD_PORTO
AD_NOTASEXC
TB_FRETES_HST
TB_FRETES_MARITIMO_HST
ARG_COMPRA_MP
ARG_FRETES_RURALVD
⚪ Baixa prioridade — padrão Sankhya (estrutura já conhecida)
TGFCAB, TGFITE, TGFPRO, TGFGRU, TGFPAR, TSICID, TSIUFS, TSIPAI, TGFTOP, TGFNAT, TSICUS, TCSPRJ, TSIMOE, TGFCOM, TGFVEI, TGFVAR, TCBLAN, F_DESCROPC. Traga só se quiser documentar colunas específicas usadas (ex.: TGFCAB.AD_PERCSPREADRISCO, AD_EX_*).

Sugestão de como enviar
Para a próxima rodada, o ideal é priorizar os grupos 🔴 (funções + views de custo). Só com FU_BMC_GETPROVFORN, FU_BMC_GETROYALTIES, FU_BMC_GETCOMVENDA e VW_BMC_BI_CUSTOS_PROD_OTM eu já consigo fechar o rastreamento completo das fórmulas de margem e apontar de onde vem cada centavo do custo calculado.

Se quiser, você pode gerar a lista real de dependências direto do dicionário com:

SELECT referenced_type, referenced_name, COUNT(*)

FROM   all_dependencies

WHERE  owner = 'SANKHYA'

AND    name IN ('STP_BMC_CARGA_MRG_BI_BASE',

                'VW_BMC_BI_BASE_ITENS_V9',

                'VW_NOTAS_31')

GROUP  BY referenced_type, referenced_name

ORDER  BY referenced_type, referenced_name;

E, para checar a colisão de alias / status de compilação da view:

SELECT object_name, object_type, status

FROM   all_objects

WHERE  owner='SANKHYA' AND status='INVALID'

AND    object_name IN ('VW_NOTAS_31','VW_BMC_BI_BASE_ITENS_V9');
