# Documentação Técnica — Stack de Margem BI (Argofruta / Sankhya)

Objetos documentados:

SANKHYA.STP_BMC_CARGA_MRG_BI_BASE (Procedure)
SANKHYA.VW_BMC_BI_BASE_ITENS_V9 (View)
SANKHYA.VW_NOTAS_31 (View)
SANKHYA.FU_BMC_GETPROVFORN (Function)
SANKHYA.FU_BMC_GETROYALTIES (Function)
SANKHYA.FU_BMC_GETCOMVENDA (Function)
SANKHYA.FU_BMC_GETPERCCOMVENDA (Function)
SANKHYA.FU_BMC_GETCUSTOPREVISTO (Function)
SANKHYA.FU_ARG_TXADM_CUSTO_GER (Function)
SANKHYA.FUN_ARG_VLRETIQSRV (Function)
SANKHYA.FUN_ARG_VLRETIQ (Function)
SANKHYA.FU_BMC_PRECO_CUSTO_GER (Function)
SANKHYA.VW_BMC_BI_CUSTOS_PROD_OTM (View)
SANKHYA.VW_BMC_BI_PERCA_PACK (View)
SANKHYA.VW_BMC_FRETE_MARITIMO (View)
SANKHYA.VW_BMC_DESPESAS_PORTUARIAS (View)
SANKHYA.VW_BMC_BI_PROV_FORNECEDORES (View)
SANKHYA.VW_BMC_GET_QTD_DEV_VENDA (View)
SANKHYA.VW_BMC_GET_QTD_DEV_VENDA_FOR (View)
SANKHYA.VW_BMC_GET_QTD_DEV_VENDA2 (View)
SANKHYA.VW_ARG_DEB_CRE_ITE (View)
SANKHYA.VW_ARG_CRE_DEB (View)
SANKHYA.VW_DESCFIN (View)
SANKHYA.VW_PERCPROC_NF_V4 (View)
SANKHYA.VW_TGFCAB_ITE (View)
SANKHYA.VW_TGFPARC_TGFEMP (View)

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
| View | VW_BMC_BI_CUSTOS_PROD_OTM | Ficha de custo (MP, embalagem, direto, operação, serviço, colheita, imp. saldo) | ✔ Sim |
| View | VW_BMC_BI_PERCA_PACK | Perda de pack | ✔ Sim |
| View | VW_BMC_FRETE_MARITIMO | Frete marítimo (FR2) | ✔ Sim |
| View | VW_BMC_DESPESAS_PORTUARIAS | Despesas portuárias (FR3) | ✔ Sim |
| Function | FU_BMC_GETPROVFORN | Provisão de fornecedor | ✔ Sim (Objeto 4) |
| Function | FU_BMC_GETROYALTIES | Royalties | ✔ Sim (Objeto 5) |
| Function | FU_BMC_GETCOMVENDA | Comissão comercial/terceiros | ✔ Sim (Objeto 6) |
| Function | FU_BMC_GETPERCCOMVENDA | % comissão comercial (usado em PERCMARGEMGER) | ✔ Sim (Objeto 7) |
| Function | FU_BMC_GETCUSTOPREVISTO | Custos previstos DESC/ETIQ/CRED/ETIQREAL | ✔ Sim (Objeto 8) |
| Function | FU_BMC_PRECO_CUSTO_GER | Custo unitário gerencial | ✔ Sim (Objeto 12) |
| Function | FU_ARG_TXADM_CUSTO_GER | Taxa administrativa sobre custo geral | ✔ Sim (Objeto 9) |
| Function | FUN_ARG_VLRETIQSRV | Valor etiqueta serviço | ✔ Sim (Objeto 10) |
| Function | FUN_ARG_VLRETIQ | Valor etiqueta | ✔ Sim (Objeto 11) |
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

   ├─ VW_BMC_BI_CUSTOS_PROD_OTM     (ficha de custo)

   ├─ VW_BMC_BI_PERCA_PACK

   ├─ VW_BMC_FRETE_MARITIMO

   ├─ VW_BMC_DESPESAS_PORTUARIAS

   ├─ Functions:

   │     FU_BMC_GETPROVFORN (Objeto 4), FU_BMC_GETROYALTIES (Objeto 5), FU_BMC_GETCOMVENDA (Objeto 6),

   │     FU_BMC_GETPERCCOMVENDA (Objeto 7), FU_BMC_GETCUSTOPREVISTO (Objeto 8),

   │     FU_BMC_PRECO_CUSTO_GER (Objeto 12), FU_ARG_TXADM_CUSTO_GER (Objeto 9),

   │     FUN_ARG_VLRETIQSRV (Objeto 10), FUN_ARG_VLRETIQ (Objeto 11)

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

Revisão (rev. 3 — 05/07/2026, versão VW_NOTAS_31_2): refatoração de performance + duas mudanças funcionais. Performance: MATERIALIZE reposto em 17 CTEs (estabiliza plano — havia spill de TEMP de 150–270 MB quando removido); índice IX_TGFCAB_AD_NUNOTASUB criado e em uso; nova CTE DEV_ITEM (devolução por item) e DEV_NOTA (devolução por nota), ambas filtrando TIPMOV='D' AND STATUSNOTA='L'. Mudanças funcionais (afetam número — exigem reconciliação): (1) coluna PERCDESCCONTRATUAL passou a vir da nova CTE PDESC (AD_CTRLDESCOM, desconto contratual mais recente por cliente); (2) nova coluna VLR_DESC_FIN_SDEV (desconto financeiro líquido de devolução por nota). Neutros: DEV_ITEM sem REFUGO (distinção vem de VW_BMC_GET_QTD_DEV_VENDA2) e TIPMOV='V' no QTDNEG_POR_NUNOTA (redundante com a query principal). Não publicar sem reconciliar PERCDESCCONTRATUAL e VLR_DESC_COM (além de QTDNEGNOTA/VLRTOTNOTA/QTDDEVVENDA) nova × produção. Ganho de tempo de execução ainda não medido. Ver CHANGELOG.md.
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
| View | VW_BMC_GET_QTD_DEV_VENDA | Devolução por item/sequência | ✔ Sim (Objeto 18) |
| View | VW_BMC_GET_QTD_DEV_VENDA_FOR | Devolução por fornecedor | ✔ Sim (Objeto 19) |
| View | VW_BMC_GET_QTD_DEV_VENDA2 | Devolução por romaneio | ✔ Sim (Objeto 20) |
| View | VW_BMC_BI_PROV_FORNECEDORES | Provisão de fornecedor | ✔ Sim (Objeto 17) |
| View | VW_TGFCAB_ITE | Cabeçalho+item (pedidos frete/log) | ✔ Sim (Objeto 25) |
| View | VW_PERCPROC_NF_V4 | % rateio processo/NF | ✔ Sim (Objeto 24) |
| View | VW_AD_REC_COMD | Valor em aberto (OPEN_AMOUNT) | ⚠ [EXTERNO] — erro no DBExplorer ao abrir ("Cannot read properties of undefined (reading 'colunas')"), não trazida ainda |
| View | VW_ARG_CRE_DEB | Crédito/débito por projeto (moeda) | ✔ Sim (Objeto 22) |
| View | VW_DESCFIN | Desconto financeiro proporcional | ✔ Sim (Objeto 23) |
| View | VW_ARG_DEB_CRE_ITE | Débito/crédito por item (CT/CL) | ✔ Sim (Objeto 21) |
| MView | VW_M_CUSTOMED_SEMANA | Custo médio semanal (também no Objeto 1) | ✖ [EXTERNO] |
| View | VW_TGFPARC_TGFEMP | Parceiros que são empresas do grupo | ✔ Sim (Objeto 26) |
| Function | F_DESCROPC | Descrição de opção (TIPOPARCERIA) — Sankhya padrão | ✖ padrão |

### 8. Objetos chamados
Views/MViews ainda [EXTERNO]: VW_M_CUSTOMED_SEMANA e VW_AD_REC_COMD (erro ao abrir no DBExplorer, ver Seção 7). Todas as demais já trazidas e documentadas: VW_BMC_GET_QTD_DEV_VENDA (Objeto 18), _FOR (Objeto 19), _2 (Objeto 20), VW_BMC_BI_PROV_FORNECEDORES (Objeto 17), VW_TGFCAB_ITE (Objeto 25), VW_PERCPROC_NF_V4 (Objeto 24), VW_ARG_CRE_DEB (Objeto 22), VW_DESCFIN (Objeto 23), VW_ARG_DEB_CRE_ITE (Objeto 21), VW_TGFPARC_TGFEMP (Objeto 26).
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

   │     VW_BMC_GET_QTD_DEV_VENDA (18) / _FOR (19) / _2 (20)

   │     VW_BMC_BI_PROV_FORNECEDORES             (Objeto 17)

   │     AD_TGFGRUPATENTES, AD_ROMANEIOENTR,

   │     AD_ROMANEIOENTFAT     [EXTERNO], VW_TGFCAB_ITE (Objeto 25)

   ├─ SELECT principal:

   │     TGFCAB ─ AD_TGFITECOMPL ─ TGFITE ─ TGFPRO ─ TGFGRU ─ TGFPAR

   │     ─ TSICID ─ TSIUFS ─ TSIPAI ─ TGFTOP ─ TGFNAT ─ TSICUS

   │     ─ AD_FRUTA ─ TCSPRJ ─ TSIMOE ─ TGFCOM ─ TGFVEI ─ AD_PORTO

   ├─ Fretes/custos [EXTERNO]:

   │     TB_FRETES_HST, TB_FRETES_MARITIMO_HST, ARG_FRETES_RURALVD,

   │     ARG_COMPRA_MP, VW_M_CUSTOMED_SEMANA

   ├─ Financeiro:

   │     VW_AD_REC_COMD [EXTERNO — erro no DBExplorer], VW_ARG_CRE_DEB (22), VW_ARG_DEB_CRE_ITE (21),

   │     VW_DESCFIN (23), VW_PERCPROC_NF_V4 (24)

   └─ Filtros: AD_NOTASEXC [EXTERNO], VW_TGFPARC_TGFEMP (Objeto 26)
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

## OBJETO 4 — SANKHYA.FU_BMC_GETPROVFORN (Function)
### 1. Resumo
Function escalar que calcula o valor de provisão de fornecedor (reserva sobre a receita menos custo e comissão) usado no cálculo de margem para AVOCADO e UVA (ver Objeto 2, Seções 5 e 6).
### 2. Fluxo de execução
1. Recebe data de referência, dimensões do item (fruta, fornecedor, grupo/variedade, cliente, mercado, projeto, país, romaneio) e os 3 valores já calculados (receita líquida, custo calculado, comissão).
2. Busca em AD_CONFPROVFORN (cabeçalho de vigência) + AD_CONFPROVFORNREG (regras) a linha vigente na data de referência cujas colunas de filtro batem (ou são NULL, tratado como coringa).
3. Ordena os candidatos por uma CASE de 24 níveis de especificidade (da combinação mais específica de dimensões para a mais genérica) e pega a primeira linha (FETCH FIRST 1 ROW ONLY).
4. Se PROVISIONAR = 'N' na regra escolhida, retorna 0. Caso contrário, retorna (receita líquida − custo calculado − comissão) + ajuste adicional, arredondado a 2 casas.
5. Se não encontrar nenhuma regra (NO_DATA_FOUND), retorna 0.
### 3. Entradas
P_DTREF (DATE), P_CODFRUTA (INT), P_CODPARCFORNECEDOR (INT), P_CODGRUPOPRODVARIEDADE (INT), P_CODPARCCLIENTE (INT), P_MERCADO (VARCHAR), P_CODPROJ (INT), P_VLRRECEITALIQ (NUMBER), P_VLRCUSTOCALCULADO (NUMBER), P_VLRCOMISSAOCOM (NUMBER), P_CODPAIS (INT), P_NRROMANEIO (INT).
### 4. Saídas
FLOAT — valor de provisão de fornecedor (0 se não provisiona ou se não encontrar regra).
### 5. Regras de negócio
- Regra vigente é a que tem TRUNC(P_DTREF) entre DTVIGENCIAINICIO e DTVIGENCIAFINAL em AD_CONFPROVFORN.
- Cada coluna de filtro em AD_CONFPROVFORNREG (codproj, codfruta, CODGRUPOPROD, MERCADO, CODPARCFORNECEDOR, CODPARCCLIENTE, CODPAIS, NRROMANEIO) casa por igualdade OU é ignorada se NULL na regra — regras mais genéricas (mais colunas NULL) servem de fallback.
- Entre regras aplicáveis, uma CASE de 24 níveis prioriza a combinação mais específica primeiro, separando regras PROVISIONAR='N' (prioridades 1-13) de PROVISIONAR='S'/NULL (prioridades 14-23), com fallback genérico (nível 24).
- DETERMINISTIC + RESULT_CACHE: o mesmo conjunto de parâmetros retorna o valor cacheado até que AD_CONFPROVFORN ou AD_CONFPROVFORNREG mudem (RELIES_ON).
### 6. Cálculos
Quando PROVISIONAR ≠ 'N': `V_VLRPROVFORN = ROUND((P_VLRRECEITALIQ − P_VLRCUSTOCALCULADO − P_VLRCOMISSAOCOM) + NVL(VALORAJUSTEADICIONAL, 0), 2)`. Quando PROVISIONAR = 'N': 0.
### 7. Dependências
| Tipo | Nome | Utilização | Está nos arquivos? |
|---|---|---|---|
| Tabela | AD_CONFPROVFORN | Cabeçalho de vigência da config | ✖ [EXTERNO] |
| Tabela | AD_CONFPROVFORNREG | Regras de provisão por dimensão | ✖ [EXTERNO] |
### 8. Objetos chamados
Nenhuma view/procedure/function — só SELECT direto nas 2 tabelas de configuração.
### 9. Objetos que provavelmente dependem deste objeto
VW_BMC_BI_BASE_ITENS_V9 (Objeto 2) — chamada múltiplas vezes por linha (vlr_margem para AVOCADO/UVA, MARGEMGER, PROVISAO_FORNECEDOR_GER).
### 10. Diagrama textual de dependências
FU_BMC_GETPROVFORN

   ├─ AD_CONFPROVFORN      [EXTERNO]

   └─ AD_CONFPROVFORNREG   [EXTERNO]
### 11. Pontos críticos
Chamada repetidas vezes por linha dentro da V9 (mesmos parâmetros) — RESULT_CACHE mitiga I/O mas ainda há overhead de context switch por chamada escalar em SQL. A CASE de 24 níveis é difícil de auditar — nova regra de negócio exige revisão cuidadosa de todos os níveis. Um comentário no código (linha 39) mostra um filtro anterior por PROVISIONAR que foi comentado — sinal de que a regra já mudou de comportamento pelo menos uma vez.
### 12. Sugestões de melhoria
[VALIDAR] Extrair a CASE de 24 níveis para uma coluna de prioridade pré-calculada em AD_CONFPROVFORNREG, reduzindo risco ao adicionar regras novas — mudança estrutural, precisa validar que a ordenação resultante é idêntica à atual para todo o histórico antes de trocar.
### 13. Resumo executivo (para analista funcional)
Decide quanto "guardar" (provisionar) do resultado de uma venda para cobrir ajustes futuros com o fornecedor. Olha uma tabela de configuração que diz, por combinação de fruta/cliente/fornecedor/mercado, se deve provisionar e quanto. Quando a config diz "não provisionar", o valor é zero; senão é receita menos custo menos comissão (mais ajuste manual, se houver).

## OBJETO 5 — SANKHYA.FU_BMC_GETROYALTIES (Function)
### 1. Resumo
Function escalar que calcula o valor de royalties devido sobre a receita líquida de um item, usado no custo total gerencial (CUSTOTOTALGER) da fruta UVA (ver Objeto 2, Seção 5).
### 2. Fluxo de execução
1. Recebe data de referência, fornecedor, grupo/variedade, parceiro-patente e mercado, mais a receita líquida do item.
2. Busca em AD_CONFROYALT (vigência) + AD_CONFROYALTREG (regras) a combinação vigente que bate (colunas NULL na regra = coringa).
3. Ordena por especificidade (patente+grupo+fornecedor+mercado > patente+grupo+fornecedor > patente+mercado > patente > genérico) e, em empate, pelo menor PERCROYALTIES.
4. Retorna ((receita líquida × PERCRECEITALIQUIDA/100) × PERCROYALTIES)/100, arredondado a 2 casas; 0 se não achar regra.
### 3. Entradas
P_DTREF (DATE), P_CODPARCFORNECEDOR (INT), P_CODGRUPOPRODVARIEDADE (INT), P_CODPARCPATENTE (INT), P_VLRRECEITALIQ (NUMBER), P_MERCADO (VARCHAR).
### 4. Saídas
FLOAT — valor de royalties (0 se não encontrar regra vigente).
### 5. Regras de negócio
- Vigência por TRUNC(P_DTREF) BETWEEN DTVIGENCIAINICIO AND DTVIGENCIAFINAL em AD_CONFROYALT.
- Casamento por CODPARCPATENTE, CODGRUPOPROD, CODPARCFORNECEDOR, MERCADO — cada um é coringa (NULL) se não informado na regra.
- Prioridade: mais dimensões preenchidas primeiro; em empate, menor PERCROYALTIES.
- PERCRECEITALIQUIDA (default 100 se NULL) permite royalties sobre uma fração da receita líquida, não o valor cheio.
- DETERMINISTIC + RESULT_CACHE, invalidado por mudança em AD_CONFROYALT/AD_CONFROYALTREG.
### 6. Cálculos
`V_VLRROYALTIES = ROUND(((P_VLRRECEITALIQ × NVL(PERCRECEITALIQUIDA,100)/100) × PERCROYALTIES) / 100, 2)`
### 7. Dependências
| Tipo | Nome | Utilização | Está nos arquivos? |
|---|---|---|---|
| Tabela | AD_CONFROYALT | Cabeçalho de vigência | ✖ [EXTERNO] |
| Tabela | AD_CONFROYALTREG | Regras de royalties por dimensão | ✖ [EXTERNO] |
### 8. Objetos chamados
Nenhum — só SELECT nas 2 tabelas de configuração.
### 9. Objetos que provavelmente dependem deste objeto
VW_BMC_BI_BASE_ITENS_V9 (Objeto 2) — usada no CUSTOTOTALGER de UVA, chamada repetidamente por linha.
### 10. Diagrama textual de dependências
FU_BMC_GETROYALTIES

   ├─ AD_CONFROYALT      [EXTERNO]

   └─ AD_CONFROYALTREG   [EXTERNO]
### 11. Pontos críticos
Mesmo padrão de FU_BMC_GETPROVFORN: chamada múltiplas vezes por linha na V9 (ver Objeto 2, Seção 11) — cada ocorrência é uma subconsulta separada mesmo com os mesmos parâmetros dentro do mesmo item.
### 12. Sugestões de melhoria
Nenhuma sugestão específica além da já registrada no Objeto 2 (reduzir chamadas repetidas por linha).
### 13. Resumo executivo (para analista funcional)
Calcula quanto da venda vira royalty a pagar ao dono da patente da variedade, com base numa tabela de regras por fornecedor/variedade/mercado — quanto mais específica a regra cadastrada, maior a prioridade sobre uma regra genérica.

## OBJETO 6 — SANKHYA.FU_BMC_GETCOMVENDA (Function)
### 1. Resumo
Function escalar que calcula o valor de comissão de venda (comercial ou de terceiros, conforme P_TIPO) aplicável a um item, usada no CUSTOTOTALGER (ver Objeto 2).
### 2. Fluxo de execução
1. Recebe tipo de comissão (P_TIPO), data de referência, dimensões do item e as receitas líquida/bruta.
2. Busca em AD_CONFCOMVENDA (vigência + tipo) + AD_CONFCOMVENDAREG (regras) a combinação vigente que bate.
3. Ordena por especificidade (11 níveis, de fruta+país até fruta+mercado+grupo+projeto+fornecedor) e, em empate, pelo menor PERCCOMISSAO.
4. Retorna PERCCOMISSAO × SINAL × (receita líquida ou bruta, conforme BASEPERCENTUAL) / 100, arredondado a 2 casas; 0 se não achar regra.
### 3. Entradas
P_TIPO (VARCHAR), P_DTREF (DATE), P_CODFRUTA (INT), P_CODPARCFORNECEDOR (INT), P_CODGRUPOPRODVARIEDADE (INT), P_CODPARCCLIENTE (INT), P_MERCADO (VARCHAR), P_CODPROJ (INT), P_CODPARCPATENTE (INT), P_VLRRECEITALIQ (NUMBER), P_VLRRECEITABRUTA (NUMBER), P_CODPAIS (INT), P_NRROMANEIO (INT).
### 4. Saídas
FLOAT — valor de comissão (0 se não encontrar regra vigente para o tipo pedido).
### 5. Regras de negócio
- Vigência por data + c.tipo = P_TIPO — a mesma tabela serve mais de um "tipo" de comissão (comercial, terceiros etc.).
- BASEPERCENTUAL define se a % incide sobre receita líquida ('RL', default) ou bruta.
- SINAL multiplica o resultado — permite regra que na prática é um crédito (sinal negativo) em vez de custo.
- Priorização por CASE de 11 níveis (0 a 10), da combinação mais específica pra mais genérica; em empate, menor PERCCOMISSAO.
### 6. Cálculos
`V_VLRCOM = ROUND(PERCCOMISSAO × SINAL × (CASE WHEN BASEPERCENTUAL='RL' (ou NULL) THEN P_VLRRECEITALIQ ELSE P_VLRRECEITABRUTA END) / 100, 2)`
### 7. Dependências
| Tipo | Nome | Utilização | Está nos arquivos? |
|---|---|---|---|
| Tabela | AD_CONFCOMVENDA | Cabeçalho de vigência + tipo | ✖ [EXTERNO] |
| Tabela | AD_CONFCOMVENDAREG | Regras de comissão por dimensão | ✖ [EXTERNO] |
### 8. Objetos chamados
Nenhum — só SELECT nas 2 tabelas de configuração.
### 9. Objetos que provavelmente dependem deste objeto
VW_BMC_BI_BASE_ITENS_V9 (Objeto 2) — chamada ao menos para P_TIPO='TERCEIROS' (comissão de terceiros), conforme Seção 11 do Objeto 2.
### 10. Diagrama textual de dependências
FU_BMC_GETCOMVENDA

   ├─ AD_CONFCOMVENDA      [EXTERNO]

   └─ AD_CONFCOMVENDAREG   [EXTERNO]
### 11. Pontos críticos
Mesmo padrão de chamada repetida por linha na V9. P_TIPO é um filtro de igualdade direto (c.tipo = P_TIPO) sem tratamento de NULL/case — valor de tipo incorreto (typo, case diferente) retorna 0 silenciosamente em vez de erro.
### 12. Sugestões de melhoria
Nenhuma além da já registrada no Objeto 2.
### 13. Resumo executivo (para analista funcional)
Calcula a comissão de venda (comercial ou de terceiros) de um item, usando uma tabela de regras por fruta/cliente/fornecedor/mercado — funciona em conjunto com FU_BMC_GETPERCCOMVENDA, que devolve só a alíquota usada.

## OBJETO 7 — SANKHYA.FU_BMC_GETPERCCOMVENDA (Function)
### 1. Resumo
Function escalar irmã de FU_BMC_GETCOMVENDA: usa as mesmas tabelas de configuração (AD_CONFCOMVENDA/AD_CONFCOMVENDAREG) mas retorna só o percentual de comissão (PERCCOMISSAO), não o valor monetário. Usada em PERCMARGEMGER para o caso "não provisiona" (ver Objeto 2, Seção 5).
### 2. Fluxo de execução
Igual à busca de FU_BMC_GETCOMVENDA (mesmas tabelas, mesmos parâmetros), mas com uma CASE de priorização mais elaborada (19 níveis): primeiro separa candidatos com PERCCOMISSAO = 0 dos com PERCCOMISSAO > 0 (prioriza achar uma regra explícita de comissão zero antes de cair numa regra genérica com comissão positiva), e dentro de cada grupo aplica a mesma escala de especificidade de dimensões.
### 3. Entradas
Mesma assinatura de FU_BMC_GETCOMVENDA: P_TIPO, P_DTREF, P_CODFRUTA, P_CODPARCFORNECEDOR, P_CODGRUPOPRODVARIEDADE, P_CODPARCCLIENTE, P_MERCADO, P_CODPROJ, P_CODPARCPATENTE, P_VLRRECEITALIQ, P_VLRRECEITABRUTA, P_CODPAIS, P_NRROMANEIO — note que P_VLRRECEITALIQ/P_VLRRECEITABRUTA são recebidos mas não usados no cálculo nem no ORDER BY.
### 4. Saídas
FLOAT — percentual de comissão (0 se não encontrar regra).
### 5. Regras de negócio
- Mesma busca de vigência e mesmas colunas de filtro (coringa se NULL) que FU_BMC_GETCOMVENDA.
- Diferença chave: a CASE de prioridade primeiro esgota as combinações com PERCCOMISSAO=0 (níveis 0-9) antes de considerar as com PERCCOMISSAO>0 (níveis 10-17) — uma regra específica de "comissão zero" sempre vence uma regra mais genérica com comissão positiva.
- [VALIDAR] Sem RESULT_CACHE (diferente de FU_BMC_GETCOMVENDA) — só DETERMINISTIC. Não está claro no código se é omissão ou proposital.
### 6. Cálculos
`V_VLRCOM = ROUND(PERCCOMISSAO, 2)` — sem multiplicação, é só a alíquota.
### 7. Dependências
| Tipo | Nome | Utilização | Está nos arquivos? |
|---|---|---|---|
| Tabela | AD_CONFCOMVENDA | Cabeçalho de vigência + tipo | ✖ [EXTERNO] |
| Tabela | AD_CONFCOMVENDAREG | Regras de comissão por dimensão | ✖ [EXTERNO] |
### 8. Objetos chamados
Nenhum — só SELECT nas 2 tabelas de configuração (mesmas de FU_BMC_GETCOMVENDA).
### 9. Objetos que provavelmente dependem deste objeto
VW_BMC_BI_BASE_ITENS_V9 (Objeto 2) — usada em PERCMARGEMGER para o caso "não provisiona".
### 10. Diagrama textual de dependências
FU_BMC_GETPERCCOMVENDA

   ├─ AD_CONFCOMVENDA      [EXTERNO]

   └─ AD_CONFCOMVENDAREG   [EXTERNO]
### 11. Pontos críticos
Falta de RESULT_CACHE (diferente das demais functions de configuração) é uma inconsistência a validar. Duas functions quase-gêmeas (esta e FU_BMC_GETCOMVENDA) mantêm lógica de priorização em paralelo — mudança de regra de negócio precisa lembrar de replicar nas duas.
### 12. Sugestões de melhoria
[VALIDAR] Considerar unificar FU_BMC_GETCOMVENDA e FU_BMC_GETPERCCOMVENDA numa única function que retorna ambos (valor e percentual), evitando duplicar a lógica de priorização — mudança de assinatura, precisa levantar todos os call sites antes.
### 13. Resumo executivo (para analista funcional)
Irmã da function de comissão: em vez do valor em R$, devolve só a alíquota (%) que seria aplicada — usada quando o cálculo de margem precisa saber "qual seria a comissão" sem necessariamente cobrá-la.

## OBJETO 8 — SANKHYA.FU_BMC_GETCUSTOPREVISTO (Function)
### 1. Resumo
Function escalar simples que busca um valor de custo previsto/orçado (por tipo de custo) cadastrado manualmente para um projeto e produtor, na tabela AD_CUSTOSPREV. Usada no CUSTOTOTALGER para os componentes de custo previsto (ver Objeto 2, dependência "Custos previstos DESC/ETIQ/CRED/ETIQREAL").
### 2. Fluxo de execução
1. Recebe CODPROJ, CODPRODUTOR e um TIPOCUSTO (string).
2. Busca em AD_CUSTOSPREV a linha com esse projeto + tipo de custo, tratando CODPARC nulo na tabela como "vale pra qualquer produtor" (NVL(pr.codparc, P_CODPRODUTOR) = P_CODPRODUTOR).
3. Se não achar (NO_DATA_FOUND), retorna 0.
### 3. Entradas
P_CODPROJ (INT), P_CODPRODUTOR (INT), P_TIPOCUSTO (VARCHAR).
### 4. Saídas
FLOAT — valor de custo previsto (0 se não cadastrado).
### 5. Regras de negócio
- Match exato por CODPROJ e TIPOCUSTO; CODPARC é coringa quando NULL na tabela (permite um valor "geral" por projeto, sobrescrito por um valor específico de produtor quando existir uma segunda linha).
- [VALIDAR] Se existir mais de uma linha em AD_CUSTOSPREV que bate simultaneamente, a query não tem ORDER BY/FETCH FIRST — depende de não haver ambiguidade real na tabela; senão estoura TOO_MANY_ROWS (não tratado no EXCEPTION, que só cobre NO_DATA_FOUND).
- DETERMINISTIC + RESULT_CACHE, invalidado por mudança em AD_CUSTOSPREV.
- Comentário no código identifica autor/data (Edmar Miranda, 21/10/2023).
### 6. Cálculos
V_VALOR = pr.VALOR (sem transformação) da linha encontrada; 0 se não encontrar.
### 7. Dependências
| Tipo | Nome | Utilização | Está nos arquivos? |
|---|---|---|---|
| Tabela | AD_CUSTOSPREV | Custos previstos por projeto/produtor/tipo | ✖ [EXTERNO] |
### 8. Objetos chamados
Nenhum.
### 9. Objetos que provavelmente dependem deste objeto
VW_BMC_BI_BASE_ITENS_V9 (Objeto 2) — componentes previstos do custo total gerencial.
### 10. Diagrama textual de dependências
FU_BMC_GETCUSTOPREVISTO

   └─ AD_CUSTOSPREV   [EXTERNO]
### 11. Pontos críticos
Ausência de tratamento para TOO_MANY_ROWS — se a tabela de configuração acumular linhas ambíguas (mesmo projeto+produtor+tipo cadastrado duas vezes), a function estoura erro em vez de aplicar um desempate, ao contrário das outras functions de configuração (que usam ORDER BY + FETCH FIRST 1 ROW ONLY).
### 12. Sugestões de melhoria
[VALIDAR] Adicionar FETCH FIRST 1 ROW ONLY com um ORDER BY explícito (ou constraint de unicidade na tabela) pra blindar contra cadastro duplicado — mudança só tem efeito se a tabela já tiver ambiguidade hoje.
### 13. Resumo executivo (para analista funcional)
Busca um valor de custo "combinado manualmente" (não calculado automaticamente) para um projeto/produtor específico — serve de override quando o custo previsto de algo (desconto, etiqueta, etc.) foi negociado fora do fluxo automático.

## OBJETO 9 — SANKHYA.FU_ARG_TXADM_CUSTO_GER (Function)
### 1. Resumo
Function escalar que busca a taxa administrativa (TXADM) aplicável ao custo geral de um item, cadastrada em AD_CUSTOGER/AD_CUSTOGERITE, considerando cultivar, tipo de caixa, grupo de produto, transporte, mercado, fornecedor de MP, romaneio e local.
### 2. Fluxo de execução
1. Recebe data de referência e 8 dimensões do item (cultivar, mercado, grupo de produto, transporte, tipo de caixa, fornecedor de MP, romaneio, local de entrada).
2. Busca em AD_CUSTOGER (vigência por DATAINICIAL/DATAFINAL) + AD_CUSTOGERITE (registro ativo, ATIVO='S') a linha que bate em cultivar + tipo de caixa (obrigatórios) e trata as demais colunas como coringa se NULL na regra.
3. Ordena pelo número de colunas opcionais preenchidas (mais preenchidas primeiro) e, em empate, pelo maior CODCUSTOGERITE (cadastro mais recente).
4. Retorna TXADM da primeira linha; 0 se não encontrar.
### 3. Entradas
P_DTREF (DATE), P_CULTIVAR (VARCHAR), P_MERCADO (VARCHAR), P_CODGRUPOPROD (INT), P_TRANSPORTE (VARCHAR), P_TIPOCAIXA (FLOAT), P_CODPARCMP (INT), P_NROROMANEIO (VARCHAR), P_LOC_ENT (INT).
### 4. Saídas
FLOAT — taxa administrativa (0 se não encontrar regra vigente e ativa).
### 5. Regras de negócio
- Vigência por TRUNC(P_DTREF) BETWEEN DATAINICIAL AND DATAFINAL em AD_CUSTOGER.
- CULTIVAR e TIPOCAIXA são obrigatórios (match exato); CODGRUPOPROD, TRANSPORTE, MERCADO, CODPARCMP, NRROMANEIO, CODLOCAL são coringa se NULL na regra.
- Só considera registros com ATIVO='S' em AD_CUSTOGERITE.
- Prioridade: soma de flags (1 se a coluna opcional está preenchida na regra, 0 se NULL) em ordem decrescente; em empate, o CODCUSTOGERITE mais alto (cadastro mais recente) vence.
- DETERMINISTIC + RESULT_CACHE, invalidado por mudança em AD_CUSTOGER/AD_CUSTOGERITE.
### 6. Cálculos
V_PRECO = cgi.TXADM da linha vencedora; 0 se não encontrar (NO_DATA_FOUND tratado no bloco interno).
### 7. Dependências
| Tipo | Nome | Utilização | Está nos arquivos? |
|---|---|---|---|
| Tabela | AD_CUSTOGER | Cabeçalho de vigência do custo geral | ✖ [EXTERNO] |
| Tabela | AD_CUSTOGERITE | Itens/regras de taxa administrativa | ✖ [EXTERNO] |
### 8. Objetos chamados
Nenhum.
### 9. Objetos que provavelmente dependem deste objeto
[VALIDAR] Listada como dependência de VW_BMC_BI_BASE_ITENS_V9 (Objeto 2, Seções 7/8/10), mas o texto de Cálculos/Regras de negócio já documentado da V9 não menciona explicitamente onde ela entra — confirmar o ponto exato de uso na V9 (ou se é chamada por outro objeto ainda não trazido) antes de assumir o fluxo.
### 10. Diagrama textual de dependências
FU_ARG_TXADM_CUSTO_GER

   ├─ AD_CUSTOGER      [EXTERNO]

   └─ AD_CUSTOGERITE   [EXTERNO]
### 11. Pontos críticos
Regra de prioridade por "soma de flags preenchidos" trata todas as colunas opcionais com o mesmo peso — duas regras com o mesmo número de colunas preenchidas mas em dimensões diferentes empatam e o desempate vira "cadastro mais recente", não "dimensão mais relevante para o negócio".
### 12. Sugestões de melhoria
Nenhuma sugestão específica sem confirmar primeiro o ponto [VALIDAR] da Seção 9.
### 13. Resumo executivo (para analista funcional)
Busca a taxa administrativa a aplicar sobre o custo geral de um lote, olhando pra uma tabela de regras por cultivar/tipo de caixa/transporte/mercado — funciona como uma tabela de "de/para" configurável em vez de taxa fixa no código.

## OBJETO 10 — SANKHYA.FUN_ARG_VLRETIQSRV (Function)
### 1. Resumo
Function escalar que calcula o valor total de etiqueta (material + serviço) de um pallet, somando o valor de material vigente na data de paletização com o valor de serviço vigente na mesma data. Usada no CUSTOTOTALGER (soma sempre, para toda fruta — ver Objeto 2, Seção 5).
### 2. Fluxo de execução
1. Recebe o código único do pallet (NROUNICO de AD_MONTPALLET).
2. Busca em AD_MONTPALLET a data de paletização (DTPALETIZACAO), o código da etiqueta de material (NROETIQ) e o código do serviço (NROSRV).
3. Busca em AD_MATPALLETITE o valor de material (VLRMAT) vigente naquela data (DTINI/DTFIN).
4. Busca em AD_SRVPALLETITE o valor de serviço (VLRSRV) vigente na mesma data.
5. Soma os dois e retorna. Se qualquer busca não encontrar linha (NO_DATA_FOUND) ou ocorrer outro erro (WHEN OTHERS), retorna 0 ou NULL respectivamente.
### 3. Entradas
P_CODIGO (NROUNICO — chave de AD_MONTPALLET).
### 4. Saídas
NUMBER — soma de valor de material + valor de serviço da etiqueta (0 se não achar dados; NULL em caso de erro inesperado).
### 5. Regras de negócio
- Valor de material e de serviço são "vigentes por data" — cada um tem uma tabela de histórico de preço (DTINI/DTFIN) e busca o preço válido na data de paletização do pallet, não na data atual.
- DETERMINISTIC (sem RESULT_CACHE/RELIES_ON, diferente das functions de configuração de margem) — cada chamada revalida.
- Tratamento de erro assimétrico: NO_DATA_FOUND vira 0 (comportamento "seguro"), mas WHEN OTHERS vira NULL (silencioso).
### 6. Cálculos
v_valor = VLRSRV + VLRMAT (das linhas vigentes na data de paletização).
### 7. Dependências
| Tipo | Nome | Utilização | Está nos arquivos? |
|---|---|---|---|
| Tabela | AD_MONTPALLET | Cabeçalho do pallet (data, etiqueta, serviço) | ✖ [EXTERNO] |
| Tabela | AD_MATPALLETITE | Histórico de preço de material de etiqueta | ✖ [EXTERNO] |
| Tabela | AD_SRVPALLETITE | Histórico de preço de serviço de etiqueta | ✖ [EXTERNO] |
### 8. Objetos chamados
Nenhum.
### 9. Objetos que provavelmente dependem deste objeto
VW_BMC_BI_BASE_ITENS_V9 (Objeto 2) — somada sempre ao CUSTOTOTALGER, multiplicada por total de caixas (ver Objeto 2, Seção 5: "Sempre soma FUN_ARG_VLRETIQSRV(nropallet)*total_cx").
### 10. Diagrama textual de dependências
FUN_ARG_VLRETIQSRV

   ├─ AD_MONTPALLET     [EXTERNO]

   ├─ AD_MATPALLETITE   [EXTERNO]

   └─ AD_SRVPALLETITE   [EXTERNO]
### 11. Pontos críticos
WHEN OTHERS RETURN NULL engole qualquer erro que não seja NO_DATA_FOUND (ex.: TOO_MANY_ROWS se houver sobreposição de vigência) — um NULL se propaga silenciosamente pro cálculo de custo em vez de sinalizar problema de dado. Já é referenciada no Objeto 2 (Seção 11) com risco de ORA-01722 por causa de um TO_NUMBER(nropallet) do lado de quem chama.
### 12. Sugestões de melhoria
[VALIDAR] Trocar WHEN OTHERS RETURN NULL por um log de erro antes de retornar NULL, pra não perder visibilidade de erro de dado real — risco baixo mas precisa confirmar que nada depende do silêncio atual.
### 13. Resumo executivo (para analista funcional)
Soma quanto custou a etiqueta de um pallet (material + serviço de etiquetar), usando o preço que estava valendo na data em que o pallet foi paletizado — não o preço de hoje.

## OBJETO 11 — SANKHYA.FUN_ARG_VLRETIQ (Function)
### 1. Resumo
Function escalar que calcula o valor de etiqueta (material) de um pallet a partir do custo do produto de etiqueta (via obtemcusto4, function utilitária padrão Sankhya) multiplicado pela quantidade de etiquetas por caixa cadastrada no produto.
### 2. Fluxo de execução
1. Recebe o código único do pallet (NROUNICO de AD_MONTPALLET).
2. Busca em AD_MONTPALLET o produto de etiqueta (CODPRODAD) e a data de fabricação (DTFABRICACAO), junto com o cadastro do produto (TGFPRO) pra pegar AD_QTDPORCX (quantidade por caixa, default 10 se NULL).
3. Chama obtemcusto4(...) — function utilitária Sankhya que devolve o custo do produto numa data/tipo de custo específico (aqui: tipo 3) — e multiplica pelo AD_QTDPORCX.
4. Retorna o valor; 0 se não achar dados (NO_DATA_FOUND), NULL em qualquer outro erro (WHEN OTHERS).
### 3. Entradas
P_CODIGO (NROUNICO — chave de AD_MONTPALLET / AD_MATPALLETITE).
### 4. Saídas
AD_MATPALLETITE.VLRMAT%TYPE (NUMBER) — valor de etiqueta de material (0 se não achar; NULL em erro inesperado).
### 5. Regras de negócio
- O custo unitário do produto de etiqueta vem de uma function utilitária padrão do Sankhya (obtemcusto4), não de uma tabela própria do BI — comportamento de obtemcusto4 não documentado aqui.
- AD_QTDPORCX (quantidade de etiquetas por caixa) tem default 10 quando NULL no cadastro do produto.
- Não é DETERMINISTIC nem tem RESULT_CACHE (diferente da maioria das outras functions de margem) — provavelmente porque depende de obtemcusto4, que por sua vez pode não ser determinística.
- Mesmo padrão de tratamento de erro assimétrico de FUN_ARG_VLRETIQSRV (NO_DATA_FOUND → 0, WHEN OTHERS → NULL).
### 6. Cálculos
`v_valor = obtemcusto4(CODPRODAD, ' ', 1, 0, DTFABRICACAO, 3) × NVL(AD_QTDPORCX, 10)`
### 7. Dependências
| Tipo | Nome | Utilização | Está nos arquivos? |
|---|---|---|---|
| Tabela | AD_MONTPALLET | Cabeçalho do pallet (produto de etiqueta, data de fabricação) | ✖ [EXTERNO] |
| Tabela | TGFPRO | Cadastro do produto (AD_QTDPORCX) | ✖ [EXTERNO] (Sankhya padrão) |
| Function | obtemcusto4 | Custo unitário do produto por tipo/data (utilitária Sankhya) | ✖ [EXTERNO] (Sankhya padrão) |
### 8. Objetos chamados
obtemcusto4 (function utilitária padrão Sankhya, corpo não trazido para o repositório).
### 9. Objetos que provavelmente dependem deste objeto
VW_BMC_BI_BASE_ITENS_V9 (Objeto 2) — componente de custo de etiqueta no CUSTOTOTALGER (junto com FUN_ARG_VLRETIQSRV).
### 10. Diagrama textual de dependências
FUN_ARG_VLRETIQ

   ├─ AD_MONTPALLET   [EXTERNO]

   ├─ TGFPRO          [EXTERNO] (Sankhya padrão)

   └─ obtemcusto4()   [EXTERNO] (Sankhya padrão)
### 11. Pontos críticos
Depende de uma function utilitária padrão do Sankhya (obtemcusto4) cujo comportamento não está documentado neste repositório — mudança de versão do ERP ou de regra de custo padrão pode alterar o resultado sem que nada mude no código do BI. Mesmo risco de WHEN OTHERS RETURN NULL silencioso descrito em FUN_ARG_VLRETIQSRV. Há um bloco comentado (linhas 10-13) mostrando uma versão anterior que buscava DTPALETIZACAO em vez de usar DTFABRICACAO do produto — sinal de mudança de regra não documentada em outro lugar.
### 12. Sugestões de melhoria
[VALIDAR] Trazer o corpo de obtemcusto4 para o repositório (função utilitária Sankhya, referenciada mas não documentada) — sem o corpo dela, o Cálculo desta function é uma caixa-preta parcial.
### 13. Resumo executivo (para analista funcional)
Calcula o valor de material da etiqueta de um pallet, usando o custo cadastrado do produto de etiqueta (pela rotina padrão do Sankhya) multiplicado por quantas etiquetas cabem numa caixa — complementar à FUN_ARG_VLRETIQSRV (que soma o valor do serviço de etiquetar).

## OBJETO 12 — SANKHYA.FU_BMC_PRECO_CUSTO_GER (Function)
### 1. Resumo
Function escalar irmã de FU_ARG_TXADM_CUSTO_GER (Objeto 9): usa exatamente as mesmas tabelas de configuração (AD_CUSTOGER/AD_CUSTOGERITE) e a mesma lógica de busca/priorização, mas retorna o preço de custo unitário gerencial (coluna PRECO) em vez da taxa administrativa (coluna TXADM). Corpo corrigido em 07/07/2026 — o arquivo trazido originalmente continha, por engano, o corpo de FU_BMC_GETCUSTOPREVISTO (ver CHANGELOG.md).
### 2. Fluxo de execução
Idêntico ao de FU_ARG_TXADM_CUSTO_GER (Objeto 9, Seção 2): busca em AD_CUSTOGER (vigência) + AD_CUSTOGERITE (registro ativo) a linha que bate em cultivar + tipo de caixa (obrigatórios), trata as demais 6 dimensões como coringa se NULL na regra, ordena por especificidade (soma de flags preenchidos) e desempata pelo cadastro mais recente (CODCUSTOGERITE DESC). Retorna cgi.PRECO da linha vencedora.
### 3. Entradas
P_DTREF (DATE), P_CULTIVAR (VARCHAR), P_MERCADO (VARCHAR), P_CODGRUPOPROD (INT), P_TRANSPORTE (VARCHAR), P_TIPOCAIXA (FLOAT), P_CODPARCMP (INT), P_NROROMANEIO (VARCHAR), P_LOC_ENT (INT) — mesma assinatura de FU_ARG_TXADM_CUSTO_GER.
### 4. Saídas
FLOAT — preço de custo unitário gerencial (0 se não encontrar regra vigente e ativa).
### 5. Regras de negócio
Mesmas regras de FU_ARG_TXADM_CUSTO_GER (Objeto 9, Seção 5): vigência por data, CULTIVAR+TIPOCAIXA obrigatórios, demais dimensões coringa se NULL, só ATIVO='S', prioridade por soma de flags preenchidos com desempate por cadastro mais recente. DETERMINISTIC + RESULT_CACHE, invalidado por mudança em AD_CUSTOGER/AD_CUSTOGERITE.
### 6. Cálculos
V_PRECO = cgi.PRECO da linha vencedora; 0 se não encontrar (NO_DATA_FOUND tratado no bloco interno).
### 7. Dependências
| Tipo | Nome | Utilização | Está nos arquivos? |
|---|---|---|---|
| Tabela | AD_CUSTOGER | Cabeçalho de vigência do custo geral | ✖ [EXTERNO] |
| Tabela | AD_CUSTOGERITE | Itens/regras de preço de custo unitário | ✖ [EXTERNO] |
### 8. Objetos chamados
Nenhum.
### 9. Objetos que provavelmente dependem deste objeto
VW_BMC_BI_BASE_ITENS_V9 (Objeto 2) — custo unitário gerencial no CUSTOTOTALGER (ver Objeto 2, Seção 6).
### 10. Diagrama textual de dependências
FU_BMC_PRECO_CUSTO_GER

   ├─ AD_CUSTOGER      [EXTERNO]

   └─ AD_CUSTOGERITE   [EXTERNO]
### 11. Pontos críticos
Duas functions (esta e FU_ARG_TXADM_CUSTO_GER) leem exatamente a mesma tabela de configuração com a mesma lógica de priorização, mudando só a coluna retornada — mudança de regra de priorização precisa ser replicada nas duas em conjunto, senão TXADM e PRECO podem divergir em qual "regra vencedora" cada uma usa se a lógica for editada em uma e esquecida na outra.
### 12. Sugestões de melhoria
[VALIDAR] Considerar uma única function parametrizada (ex.: retornando os dois valores, ou recebendo qual coluna buscar) para eliminar a duplicação de lógica de priorização entre esta e FU_ARG_TXADM_CUSTO_GER — mudança de assinatura, precisa levantar todos os call sites antes.
### 13. Resumo executivo (para analista funcional)
Busca o preço de custo unitário "gerencial" de um lote, olhando a mesma tabela de regras por cultivar/tipo de caixa/transporte/mercado usada pela taxa administrativa (Objeto 9) — as duas vêm da mesma configuração, só que uma devolve a taxa (%) e a outra o preço (R$).

## OBJETO 13 — SANKHYA.VW_BMC_BI_CUSTOS_PROD_OTM (View)
### 1. Resumo
Ficha de custo por pallet: para cada item de nota vinculado a um pallet (via AD_MONTPALLET/AD_MONTPALLETITE), calcula até 3 variantes de custo unitário (simples, com calibre, por preço de entrada) e expõe flags de classificação de custo (colheita, direto, serviços, operação, embalagem, matéria-prima). É a dependência mais crítica da V9 (Objeto 2) — fonte de CUSTO_MP no cálculo de CUSTOTOTALGER.
### 2. Fluxo de execução
1. CTE `base`: junta TGFCAB + TGFITE + TGFPRO (nota/item/produto) com AD_MONTPALLET + AD_MONTPALLETITE (pallet do item, casado por `mp.nunotabase = cent.nunota`), trazendo também os flags de classificação de custo do produto (AD_USACLASSIFICACAO, AD_CUSTOSCOLHEITA, AD_CUSTOSDIRETO, AD_CUSTOSSERVICOS, AD_CUSTOSOPERACAO) e pré-calculando `param_preco` (calibre ou mercado do produto, conforme o produto usa classificação por calibre ou não).
2. CTE `custos`: para cada linha de `base`, calcula `precocomcalibre` (via FU_BMC_GETPRECOENTRADA, usando `param_preco`) e `precocusto` (via obtemcusto4, tipo de custo 3).
3. SELECT final: monta as 3 variantes de custo (simples/calibre/preço de entrada, valor total e unitário) e as flags de classificação (implantacaosaldo, colheita, embalagem, direto, servico, operacao, mp).
### 3. Entradas
Nenhum parâmetro — view direta sobre tabelas transacionais (TGFCAB, TGFITE, TGFPRO, AD_MONTPALLET, AD_MONTPALLETITE), filtrada implicitamente pelo join com o pallet (só traz itens que estão vinculados a algum pallet).
### 4. Saídas
Colunas principais: CODEMP, NUNOTA, CODPROD, DESCRPROD, CONTROLE, VLRUNIT, VLRTOT, QTD, LOTEMP, QTDNEG, CODPRODUTOR, VLRCUSTO/VLRCUSTOUNIT (custo simples), VLRCUSTOCALIBRE/VLRCUSTOCALIBREUNIT (com calibre), VLRCUSTOPRECOENTRADA/VLRCUSTOPRECOENTRADAUNIT (por preço de entrada), IMPLANTACAOSALDO, COLHEITA, EMBALAGEM, DIRETO, SERVICO, OPERACAO, MP (flags 'S'/'N'), CALIBREMP, MERCPRODMP, NROUNICO, TIPMOV, CODTIPOPER.
### 5. Regras de negócio
- Só entram itens vinculados a um pallet (INNER JOIN em AD_MONTPALLET/AD_MONTPALLETITE) — item sem pallet não aparece nesta view.
- `param_preco`: se o produto usa classificação por calibre (AD_USACLASSIFICACAO='S'), usa o calibre do pallet (com fallback CALIBREORI → calibre); senão usa o mercado do produto (MERCPROD) — isso decide qual "chave" é passada pra FU_BMC_GETPRECOENTRADA.
- IMPLANTACAOSALDO: 'S' quando CODTIPOPER = 213 (operação de implantação de saldo inicial, não uma venda/compra normal).
- EMBALAGEM: 'S' quando USOPROD = 'E'. MP: 'S' quando USOPROD = 'M'. COLHEITA/DIRETO/SERVICO/OPERACAO: espelham diretamente as flags AD_CUSTOSCOLHEITA/AD_CUSTOSDIRETO/AD_CUSTOSSERVICOS/AD_CUSTOSOPERACAO do produto.
### 6. Cálculos
- `VLRCUSTO = NVL(precocusto, vlrunit) × qtdneg`; `VLRCUSTOUNIT = NVL(precocusto, vlrunit)`.
- `VLRCUSTOCALIBRE = COALESCE(NULLIF(precocomcalibre,0), NULLIF(precocusto,0), vlrunit) × qtdneg`; unitário análogo sem multiplicar.
- `VLRCUSTOPRECOENTRADA = NVL(precocomcalibre,0) × qtdneg`; unitário análogo.
- `precocomcalibre = FU_BMC_GETPRECOENTRADA(nunota, codprod, param_preco)`; `precocusto = obtemcusto4(codprod, controle, codemp, 0, dtentsai, 3)`.
- `qtdneg = NVL(ient.ad_qtdneg_ger, ient.qtdneg)` — usa quantidade "gerencial" ajustada quando existir, senão a quantidade padrão do item.
### 7. Dependências
| Tipo | Nome | Utilização | Está nos arquivos? |
|---|---|---|---|
| View/Function | FU_BMC_GETPRECOENTRADA | Preço de entrada por calibre/mercado | ✖ [EXTERNO] |
| Function | obtemcusto4 | Custo unitário do produto por tipo/data (utilitária Sankhya) | ✖ [EXTERNO] (Sankhya padrão) |
| Tabela | TGFCAB / TGFITE / TGFPRO | Nota/item/produto | ✖ [EXTERNO] (Sankhya padrão) |
| Tabela | AD_MONTPALLET / AD_MONTPALLETITE | Pallet e seus itens (calibre, mercado, produtor, lote) | ✖ [EXTERNO] |
### 8. Objetos chamados
FU_BMC_GETPRECOENTRADA, obtemcusto4.
### 9. Objetos que provavelmente dependem deste objeto
VW_BMC_BI_BASE_ITENS_V9 (Objeto 2) — fonte de CUSTO_MP (MAX de vlrcustocalibreunit/vlrcustoprecoentradaunit × peso) e de todas as flags de classificação de custo usadas no CUSTOTOTALGER modular por fruta.
### 10. Diagrama textual de dependências
VW_BMC_BI_CUSTOS_PROD_OTM

   ├─ TGFCAB / TGFITE / TGFPRO        [EXTERNO] (Sankhya padrão)

   ├─ AD_MONTPALLET / AD_MONTPALLETITE [EXTERNO]

   ├─ FU_BMC_GETPRECOENTRADA           [EXTERNO]

   └─ obtemcusto4()                    [EXTERNO] (Sankhya padrão)
### 11. Pontos críticos
- Já registrado no Objeto 2 (Seção 11): a V9 chama esta view repetidas vezes por linha via subconsulta correlacionada em vez de um join agregado por pallet — é a alavanca de otimização de maior impacto identificada até agora (ver docs/REVISAO_TECNICA_STACK_MARGEM_BI.md, Sumário Executivo).
- FU_BMC_GETPRECOENTRADA e obtemcusto4 ainda são [EXTERNO] — o comportamento exato de precocomcalibre/precocusto não pode ser auditado sem o corpo delas.
- [VALIDAR] O Objeto 1 (STP_BMC_CARGA_MRG_BI_BASE, Seções 3/7/8/10) referencia um objeto chamado **VW_BMC_GETPRECOENTRADA** (prefixo VW_, tratado como view, usado para carregar a tabela AD_BMCPRECOENTRADA). Aqui, o código-fonte real de VW_BMC_BI_CUSTOS_PROD_OTM chama **FU_BMC_GETPRECOENTRADA** (prefixo FU_, sintaxe de chamada de function: `FU_BMC_GETPRECOENTRADA(nunota, codprod, param_preco)`). Não está confirmado se são dois objetos distintos (uma view de carga + uma function de lookup, coincidentemente com nome parecido) ou um erro de prefixo em um dos dois lugares — precisa confirmar no dicionário Oracle (`all_objects`) antes de tratar como o mesmo objeto.
- 3 variantes de custo (simples/calibre/preço de entrada) coexistem na mesma view — qual delas o chamador deve usar não é óbvio só lendo esta view; depende da regra de negócio de quem consome (ver Objeto 2, Seção 6, que usa calibre/preço de entrada, não o simples).
### 12. Sugestões de melhoria
[VALIDAR] Trazer o corpo de FU_BMC_GETPRECOENTRADA e obtemcusto4 pra fechar o rastreamento completo do cálculo de custo — sem eles, dois dos três valores de custo desta view são caixa-preta parcial.
### 13. Resumo executivo (para analista funcional)
Essa view calcula "quanto custou" cada item vendido que passou por um pallet, de três formas diferentes (preço médio simples, ajustado por calibre, ou pelo preço de entrada da matéria-prima) — é a ficha de custo que a calculadora de margem usa pra saber o custo de matéria-prima de cada venda.

## OBJETO 14 — SANKHYA.VW_BMC_BI_PERCA_PACK (View)
### 1. Resumo
Lista os itens de nota classificados como "perda de pack" (embalagem) — notas com tipo de operação 500 e natureza iniciada em '212'. Usada como parcela de custo (perda de pack) no CUSTOTOTALGER de MANGA (ver Objeto 2, Seção 5).
### 2. Fluxo de execução
SELECT direto de TGFCAB + TGFITE + TGFNAT, filtrando CODTIPOPER = 500 e CODNAT LIKE '212%'. Sem CTEs, sem cálculo — é uma projeção filtrada.
### 3. Entradas
Nenhum parâmetro — view direta sobre tabelas transacionais.
### 4. Saídas
NUNOTA, DTNEG, CODPROD, CONTROLE, CODLOCALORIG, QTDNEG, VLRUNIT, VLRTOT.
### 5. Regras de negócio
- CODTIPOPER = 500 identifica o tipo de operação usado para lançar perda de pack (valor fixo no código, sem tabela de referência para o significado de "500").
- CODNAT LIKE '212%' — qualquer natureza contábil que comece com 212 é considerada perda de pack; não há de-para explícito do significado dessa faixa de natureza no código.
### 6. Cálculos
Nenhum — projeção direta das colunas de TGFCAB/TGFITE.
### 7. Dependências
| Tipo | Nome | Utilização | Está nos arquivos? |
|---|---|---|---|
| Tabela | TGFCAB / TGFITE / TGFNAT | Nota, item e natureza contábil | ✖ [EXTERNO] (Sankhya padrão) |
### 8. Objetos chamados
Nenhum.
### 9. Objetos que provavelmente dependem deste objeto
VW_BMC_BI_BASE_ITENS_V9 (Objeto 2) — parcela "perda pack" do CUSTOTOTALGER de MANGA.
### 10. Diagrama textual de dependências
VW_BMC_BI_PERCA_PACK

   └─ TGFCAB / TGFITE / TGFNAT   [EXTERNO] (Sankhya padrão)
### 11. Pontos críticos
[VALIDAR] Os valores mágicos CODTIPOPER=500 e CODNAT LIKE '212%' não têm de-para documentado em nenhum lugar do repositório — se o cadastro de tipos de operação ou naturezas mudar (novo código, faixa renumerada), esta view para de capturar perda de pack silenciosamente (nenhum erro, só resultado vazio ou incompleto).
### 12. Sugestões de melhoria
[VALIDAR] Documentar (ou parametrizar via tabela de configuração) o significado de CODTIPOPER=500 e da faixa CODNAT LIKE '212%', para não depender de um "número mágico" no código-fonte.
### 13. Resumo executivo (para analista funcional)
Lista os lançamentos de perda de embalagem (pack) que entram como custo extra na margem da manga — identificados por um tipo de operação e uma faixa de natureza contábil específicos do cadastro Sankhya.

## OBJETO 15 — SANKHYA.VW_BMC_FRETE_MARITIMO (View)
### 1. Resumo
Calcula o custo de frete marítimo (natureza 203008) por item de nota, em duas modalidades: direto (nota já lançada no projeto certo) ou rateado (nota lançada num projeto "guarda-chuva" e distribuída proporcionalmente via TGFRAT — tabela de rateio do Sankhya). Usada como componente FR2 do CUSTOTOTALGER em MANGA e UVA (ver Objeto 2, Seção 5).
### 2. Fluxo de execução
1. Branch 1 ("direto"): TGFCAB + TGFITE + TGFPRO + TCSPRJ, filtrando compras (tipmov='C') de serviço (usoprod='S') com natureza 203008, projeto preenchido (codproj<>0), e que **não** tenham rateio em TGFRAT (NOT EXISTS). Contém 2 linhas de filtro comentadas (identificação de processo específico) — resíduo de depuração.
2. Branch 2 ("rateado"): parte de TGFRAT (a linha de rateio), com uma cadeia de LEFT JOINs de lookup (centro de resultado, natureza, parceiro, plano de conta, projeto, site) só para enriquecer/validar a linha, depois INNER JOIN de volta em TGFCAB/TGFITE/TGFPRO/TCSPRJ pela nota de origem (TGFRAT.NUFIN) com origem='E'. Aplica `percrateio` (percentual de rateio) sobre vlrtot/vlrnota/vlrunit.
3. UNION das duas branches, com filtro externo `WHERE codproj <> 0`.
### 3. Entradas
Nenhum parâmetro — view direta.
### 4. Saídas
CODEMP, DTNEG, NUNOTA, SEQUENCIA, CODPROD, DESCRPROD, CODPROJ, PROCESSO (identificação do projeto), VLRTOT, VLRNOTA, VLRUNIT, AD_EX_PORTOEMBARQUE, AD_EX_PORTODESCARGA.
### 5. Regras de negócio
- Natureza fixa 203008 identifica frete marítimo — valor mágico sem tabela de-para.
- Uma nota só cai no branch "direto" se não tiver nenhuma linha de rateio associada em TGFRAT (NOT EXISTS); caso tenha, só aparece via branch "rateado", evitando duplicidade entre os dois branches.
- No branch rateado, os 3 valores (vlrtot, vlrnota, vlrunit) são sempre multiplicados por `percrateio/100`, sem exceção — diferente de VW_BMC_DESPESAS_PORTUARIAS (Objeto 16), que só aplica o rateio quando o item não tem projeto próprio (ver Objeto 16, Pontos críticos).
- Duas linhas comentadas (`and prj.IDENTIFICACAO = 'AM236/2023'` / `AND prj.identificacao = 'AAV184/2023'`) são resíduo de depuração/teste específico de um processo — não afetam o resultado hoje (comentadas), mas indicam que a view foi testada/ajustada pontualmente para casos específicos.
### 6. Cálculos
Branch direto: valores originais de TGFITE/TGFCAB, sem transformação. Branch rateado: `vlrtot_rateado = (i.vlrtot × TGFRAT.percrateio) / 100` (mesma fórmula para vlrnota e vlrunit).
### 7. Dependências
| Tipo | Nome | Utilização | Está nos arquivos? |
|---|---|---|---|
| Tabela | TGFRAT | Rateio de lançamento financeiro entre projetos | ✖ [EXTERNO] (Sankhya padrão) |
| Tabela | TGFCAB / TGFITE / TGFPRO / TCSPRJ | Nota, item, produto, projeto | ✖ [EXTERNO] (Sankhya padrão) |
| Tabela | TSICUS / TGFNAT / TGFPAR / TCBPLA / TGFSIT | Lookups de enriquecimento do rateio (não alteram o resultado, só join) | ✖ [EXTERNO] (Sankhya padrão) |
### 8. Objetos chamados
Nenhuma view/function — só SELECT/UNION direto.
### 9. Objetos que provavelmente dependem deste objeto
VW_BMC_BI_BASE_ITENS_V9 (Objeto 2) — componente FR2 (frete marítimo) do CUSTOTOTALGER.
### 10. Diagrama textual de dependências
VW_BMC_FRETE_MARITIMO

   ├─ TGFCAB / TGFITE / TGFPRO / TCSPRJ   [EXTERNO] (Sankhya padrão)

   └─ TGFRAT (+ lookups TSICUS/TGFNAT/TGFPAR/TCBPLA/TGFSIT)   [EXTERNO] (Sankhya padrão)
### 11. Pontos críticos
- Linhas de filtro comentadas (processos específicos) são resíduo de depuração — risco baixo (não executam), mas poluem a leitura da view.
- Mesmo padrão estrutural de VW_BMC_DESPESAS_PORTUARIAS (Objeto 16), mas com uma diferença funcional real entre as duas: aqui o rateio é incondicional; lá é condicional a `i.AD_CODPROJ IS NULL`. [VALIDAR] confirmar se essa diferença é intencional (frete marítimo sempre rateado quando existe TGFRAT; despesa portuária só rateada quando o item não tem projeto próprio) ou se é uma divergência não documentada entre views irmãs.
### 12. Sugestões de melhoria
[VALIDAR] Documentar explicitamente (num comentário na view ou neste doc, após confirmar com o time) por que o rateio de frete marítimo é incondicional enquanto o de despesas portuárias é condicional — hoje só é visível comparando o SQL das duas views lado a lado.
### 13. Resumo executivo (para analista funcional)
Calcula o custo de frete marítimo de cada item, considerando que às vezes uma única fatura de frete precisa ser dividida (rateada) entre vários projetos/embarques — a view já devolve o valor certo por item, seja ele lançado direto no projeto ou vindo de um rateio.

## OBJETO 16 — SANKHYA.VW_BMC_DESPESAS_PORTUARIAS (View)
### 1. Resumo
Calcula o custo de despesas portuárias por item de nota, na mesma estrutura de VW_BMC_FRETE_MARITIMO (Objeto 15): branch direto + branch rateado via TGFRAT, unidos e filtrados por projeto preenchido. Usada como componente FR3 do CUSTOTOTALGER (ver Objeto 2, Seção 5).
### 2. Fluxo de execução
1. Branch 1 ("direto"): TGFCAB + TGFITE + TGFPRO + TCSPRJ, compras (tipmov='C') de serviço (usoprod='S'), projeto preenchido, sem rateio em TGFRAT (NOT EXISTS) — mesma estrutura do Objeto 15, porém **sem** filtro de natureza contábil fixa (CODNAT é só uma coluna de saída aqui, não um filtro).
2. Branch 2 ("rateado"): mesma cadeia de LEFT JOINs de lookup de TGFRAT do Objeto 15, mas o rateio só é aplicado condicionalmente: se `i.AD_CODPROJ IS NULL`, aplica `percrateio/100`; senão usa o valor cheio do item (`i.vlrtot`, `C.VLRNOTA`, `i.vlrunit` sem dividir).
3. UNION das duas branches, filtro externo `WHERE codproj <> 0 AND descrprod NOT LIKE '%FRETE%'` — o filtro por descrição de produto é o que efetivamente separa "despesa portuária" de "frete" nesta view, já que não há filtro de natureza contábil fixa como no Objeto 15.
### 3. Entradas
Nenhum parâmetro — view direta.
### 4. Saídas
CODEMP, DTNEG, NUNOTA, SEQUENCIA, CODPROD, DESCRPROD, CODPROJ, PROCESSO, VLRTOT, VLRNOTA, VLRUNIT, CODNAT.
### 5. Regras de negócio
- Diferente do Objeto 15 (frete marítimo, que filtra CODNAT=203008 explicitamente), esta view não filtra por natureza contábil — a exclusão de "isto não é despesa portuária" é feita só por `descrprod NOT LIKE '%FRETE%'` no filtro externo.
- No branch rateado, o rateio (percrateio/100) só é aplicado quando o item **não** tem projeto próprio (`i.AD_CODPROJ IS NULL`); se o item já tem projeto definido, usa o valor cheio da nota, ignorando percrateio — comportamento diferente do Objeto 15 (que sempre aplica o rateio no branch rateado).
### 6. Cálculos
Branch direto: valores originais. Branch rateado: `CASE WHEN i.AD_CODPROJ IS NULL THEN (valor × TGFRAT.percrateio)/100 ELSE valor END`, aplicado a vlrtot, vlrnota e vlrunit.
### 7. Dependências
| Tipo | Nome | Utilização | Está nos arquivos? |
|---|---|---|---|
| Tabela | TGFRAT | Rateio de lançamento financeiro entre projetos | ✖ [EXTERNO] (Sankhya padrão) |
| Tabela | TGFCAB / TGFITE / TGFPRO / TCSPRJ | Nota, item, produto, projeto | ✖ [EXTERNO] (Sankhya padrão) |
| Tabela | TSICUS / TGFNAT / TGFPAR / TCBPLA / TGFSIT | Lookups de enriquecimento do rateio | ✖ [EXTERNO] (Sankhya padrão) |
### 8. Objetos chamados
Nenhuma view/function — só SELECT/UNION direto.
### 9. Objetos que provavelmente dependem deste objeto
VW_BMC_BI_BASE_ITENS_V9 (Objeto 2) — componente FR3 (despesas portuárias) do CUSTOTOTALGER.
### 10. Diagrama textual de dependências
VW_BMC_DESPESAS_PORTUARIAS

   ├─ TGFCAB / TGFITE / TGFPRO / TCSPRJ   [EXTERNO] (Sankhya padrão)

   └─ TGFRAT (+ lookups TSICUS/TGFNAT/TGFPAR/TCBPLA/TGFSIT)   [EXTERNO] (Sankhya padrão)
### 11. Pontos críticos
- [VALIDAR] Ausência de filtro de natureza contábil (diferente do Objeto 15) faz a view depender só de `descrprod NOT LIKE '%FRETE%'` para não capturar frete — um produto de despesa portuária cujo nome contenha "FRETE" (ou vice-versa) seria classificado errado silenciosamente.
- [VALIDAR] O rateio condicional (só quando AD_CODPROJ IS NULL) é uma diferença funcional real frente ao Objeto 15 (rateio sempre aplicado) — confirmar se é intencional; se for um bug de uma das duas views, a correção muda valores de margem.
### 12. Sugestões de melhoria
[VALIDAR] Adicionar um filtro de natureza contábil explícito (como no Objeto 15) em vez de depender só da exclusão por nome de produto — reduz risco de classificação incorreta por causa de um nome de produto ambíguo.
### 13. Resumo executivo (para analista funcional)
Calcula o custo de despesas de porto (embarque/descarga) de cada item, na mesma lógica de rateio do frete marítimo — mas aqui a separação "isto é despesa portuária, não frete" depende do nome do produto, não de um código de natureza contábil fixo.

## OBJETO 17 — SANKHYA.VW_BMC_BI_PROV_FORNECEDORES (View)
### 1. Resumo
Lê lançamentos contábeis manuais de provisão de fornecedor a partir do lote financeiro 34 da tabela padrão TCBLAN, com inversão de sinal para lançamentos de estorno (TIPLANC='R'). Usada como componente de provisão de fornecedor no CUSTOTOTALGER/PROVISAO_FORNECEDOR_GER (ver Objeto 2, Seção 5), em paralelo ao cálculo automático de FU_BMC_GETPROVFORN (Objeto 4).
### 2. Fluxo de execução
SELECT direto de TCBLAN filtrando NUMLOTE = 34 e CODCENCUS <> 0, com o valor de referência calculado por DECODE conforme o tipo de lançamento.
### 3. Entradas
Nenhum parâmetro — view direta sobre TCBLAN.
### 4. Saídas
CODEMP, REFERENCIA, CODCTACTB, NUMLANC, CODCENCUS, TIPLANC, VLRREF (valor com sinal já ajustado).
### 5. Regras de negócio
- NUMLOTE = 34 identifica o lote de lançamentos de provisão de fornecedor dentro do módulo financeiro (TCBLAN é uma tabela genérica de lançamentos contábeis usada por múltiplos processos — Objeto 2 já lista TCBLAN também como fonte de rateio de royalties, filtrado por outro critério/lote) — valor mágico sem tabela de-para.
- CODCENCUS <> 0 exclui lançamentos sem centro de custo definido.
- TIPLANC='R' (estorno/reversão) inverte o sinal do valor (× -1); qualquer outro TIPLANC mantém o valor original.
### 6. Cálculos
`VLRREF = DECODE(TIPLANC, 'R', VLRLANC × -1, VLRLANC)`
### 7. Dependências
| Tipo | Nome | Utilização | Está nos arquivos? |
|---|---|---|---|
| Tabela | TCBLAN | Lançamentos contábeis (lote 34 = provisão de fornecedor) | ✖ [EXTERNO] (Sankhya padrão) |
### 8. Objetos chamados
Nenhum.
### 9. Objetos que provavelmente dependem deste objeto
VW_BMC_BI_BASE_ITENS_V9 (Objeto 2) — parcela de provisão de fornecedor, em paralelo ao cálculo de FU_BMC_GETPROVFORN (Objeto 4); [VALIDAR] confirmar como as duas fontes de provisão (esta view baseada em lançamento manual vs. a function baseada em regra automática) se combinam no cálculo final — não é óbvio pela V9 já documentada se uma substitui a outra ou se são somadas.
### 10. Diagrama textual de dependências
VW_BMC_BI_PROV_FORNECEDORES

   └─ TCBLAN   [EXTERNO] (Sankhya padrão)
### 11. Pontos críticos
- NUMLOTE = 34 é um valor mágico sem tabela de referência — se o lote de provisão de fornecedor for renumerado no financeiro, a view para de capturar dados silenciosamente.
- [VALIDAR] Relação entre esta view (provisão "manual"/contábil) e FU_BMC_GETPROVFORN (Objeto 4, provisão "calculada"/automática) não está clara — podem ser fontes complementares (uma cobre o que a outra não cobre) ou redundantes; precisa confirmar com quem manteve a V9 antes de qualquer otimização que mexa em uma delas.
### 12. Sugestões de melhoria
[VALIDAR] Documentar (ou parametrizar) o significado de NUMLOTE=34, e esclarecer com o time funcional a relação entre esta view e FU_BMC_GETPROVFORN antes de qualquer consolidação.
### 13. Resumo executivo (para analista funcional)
Traz os lançamentos manuais de provisão de fornecedor já registrados na contabilidade (lote específico do financeiro), com o sinal certo para estornos — é a "provisão de fato lançada", diferente da function que calcula quanto *deveria* ser provisionado por regra.

## OBJETO 18 — SANKHYA.VW_BMC_GET_QTD_DEV_VENDA (View)
### 1. Resumo
Calcula quantidade e valor devolvidos (V_QTDDEV/V_VLRDEV) por item de venda original (nunotaorig/sequenciaorig), agregando via LISTAGG as notas de devolução (nunotadest) e as chaves de NFe (chavenfe) associadas. Usada por `VW_NOTAS_31` (Objeto 3) para calcular quantidade líquida de devolução e por `VW_PERCPROC_NF_V4` (Objeto 24) para excluir quantidade já devolvida do rateio.
### 2. Fluxo de execução
SELECT direto de TGFVAR (tabela de vínculo/variação entre nota original e nota de devolução) + TGFCAB (só notas de devolução liquidadas, tipmov='D' e STATUSNOTA='L') + TGFITE, agrupando por nota/sequência de origem. Um bloco `UNION ALL` inteiro (linhas 60+ do arquivo) está comentado (`/* ... */`) — código morto que somava devolução por uma lógica alternativa (AD_QTDNEGOR, codtipoper 2126/2127, com uma lista de NUNOTA excluídos hardcoded).
### 3. Entradas
Nenhum parâmetro — view direta.
### 4. Saídas
V_QTDDEV, V_VLRDEV, NUNOTAORIG, SEQUENCIAORIG, REFUGO ('S'/'N'), NUNOTADEST (lista concatenada), TIPO (fixo 'D'), CHAVENFE (lista concatenada).
### 5. Regras de negócio
- Só considera devoluções liquidadas (STATUSNOTA='L') do tipo de movimento 'D'.
- REFUGO = 'S' quando CODTIPOPER da nota de devolução está em (1227, 1228); 'N' caso contrário — mesma faixa de tipo de operação usada em outros pontos do stack para identificar refugo/realocação (ver Objeto 2, Seção 7, dependência "TGFCAB / TGFITE / TGFVAR | Devoluções (tipoper 1227/1228)").
- `[VALIDAR]` O bloco `UNION ALL` comentado sugere que já existiu (ou foi cogitada) uma segunda fonte de devolução baseada em CODTIPOPER 2126/2127 com uma lista de notas excluídas manualmente — não está documentado por que foi desativado nem se a lista de exclusões ainda é válida.
### 6. Cálculos
`V_QTDDEV = SUM(i.qtdneg)`; `V_VLRDEV = SUM(i.vlrtot)`; agregação por `nunotaorig`, `sequenciaorig`, REFUGO, `v.NUNOTA`, `c.chavenfe`.
### 7. Dependências
| Tipo | Nome | Utilização | Está nos arquivos? |
|---|---|---|---|
| Tabela | TGFVAR | Vínculo nota original ↔ nota de devolução | ✖ [EXTERNO] (Sankhya padrão) |
| Tabela | TGFCAB / TGFITE | Nota e item de devolução | ✖ [EXTERNO] (Sankhya padrão) |
### 8. Objetos chamados
Nenhum.
### 9. Objetos que provavelmente dependem deste objeto
VW_NOTAS_31 (Objeto 3) — quantidade líquida de devolução. VW_PERCPROC_NF_V4 (Objeto 24) — exclusão de quantidade devolvida do rateio de processo.
### 10. Diagrama textual de dependências
VW_BMC_GET_QTD_DEV_VENDA

   └─ TGFVAR / TGFCAB / TGFITE   [EXTERNO] (Sankhya padrão)
### 11. Pontos críticos
Bloco `UNION ALL` morto comentado no meio do arquivo — polui a leitura e mantém uma lista de exclusão de notas hardcoded (13 números de nota) sem explicação; se algum dia for reativado por engano, o comportamento muda silenciosamente.
### 12. Sugestões de melhoria
[VALIDAR] Remover o bloco comentado (mover para histórico em Git) se de fato está desativado definitivamente — confirmar com o time antes.
### 13. Resumo executivo (para analista funcional)
Descobre quanto de uma venda foi devolvido depois, olhando o vínculo entre a nota original e a(s) nota(s) de devolução — é o que permite calcular a "quantidade líquida" (vendido menos devolvido) usada no cálculo de margem.

## OBJETO 19 — SANKHYA.VW_BMC_GET_QTD_DEV_VENDA_FOR (View)
### 1. Resumo
Variante de VW_BMC_GET_QTD_DEV_VENDA (Objeto 18) agregada também por fornecedor (CODPARC) — "por fornecedor" (FOR no nome). Usa `AD_TGFITECOMPL` em vez de `TGFITE` como fonte de item.
### 2. Fluxo de execução
Mesma lógica de TGFVAR + TGFCAB (devolução liquidada), mas o join de item é com `AD_TGFITECOMPL` (base de itens customizada, casada por `i.SEQITE = v.sequencia`), e o GROUP BY inclui `i.codparc`.
### 3. Entradas
Nenhum parâmetro — view direta.
### 4. Saídas
V_QTDDEV (`SUM(i.QUANTITY)`), V_VLRDEV, NUNOTAORIG, SEQUENCIAORIG, REFUGO, NUNOTADEST (lista concatenada), CODPARC.
### 5. Regras de negócio
Mesmas regras de vigência/liquidação de VW_BMC_GET_QTD_DEV_VENDA. Diferença: usa `AD_TGFITECOMPL.QUANTITY` (não `TGFITE.qtdneg`) e agrega por fornecedor, permitindo saber quanto foi devolvido por fornecedor específico dentro da mesma nota.
### 6. Cálculos
`V_QTDDEV = SUM(i.QUANTITY)`; `V_VLRDEV = SUM(i.vlrtot)`; agregado por nunotaorig, sequenciaorig, codparc, REFUGO.
### 7. Dependências
| Tipo | Nome | Utilização | Está nos arquivos? |
|---|---|---|---|
| Tabela | TGFVAR / TGFCAB | Vínculo e cabeçalho de devolução | ✖ [EXTERNO] (Sankhya padrão) |
| Tabela | AD_TGFITECOMPL | Base de itens customizada | ✖ [EXTERNO] |
### 8. Objetos chamados
Nenhum.
### 9. Objetos que provavelmente dependem deste objeto
VW_NOTAS_31 (Objeto 3) — listada como dependência (CTE `QTDNEG_POR_FORN`).
### 10. Diagrama textual de dependências
VW_BMC_GET_QTD_DEV_VENDA_FOR

   ├─ TGFVAR / TGFCAB       [EXTERNO] (Sankhya padrão)

   └─ AD_TGFITECOMPL        [EXTERNO]
### 11. Pontos críticos
Mesma família de 3 views quase-idênticas (Objetos 18, 19, 20) com pequenas variações de agregação (sem dimensão extra / por fornecedor / por romaneio) — mudança de regra de negócio na devolução precisa ser replicada nas 3.
### 12. Sugestões de melhoria
[VALIDAR] Considerar consolidar as 3 variantes (VENDA, VENDA_FOR, VENDA2) numa única view parametrizável ou com as 3 dimensões extras já expostas, evitando manter 3 cópias da mesma lógica de devolução.
### 13. Resumo executivo (para analista funcional)
Mesma ideia da devolução líquida (Objeto 18), mas quebrada por fornecedor — usada quando o cálculo de margem precisa saber de qual fornecedor específico veio a mercadoria devolvida.

## OBJETO 20 — SANKHYA.VW_BMC_GET_QTD_DEV_VENDA2 (View)
### 1. Resumo
Segunda variante de VW_BMC_GET_QTD_DEV_VENDA (Objeto 18), agregada por romaneio em vez de fornecedor.
### 2. Fluxo de execução
Idêntica estrutura à Objeto 19 (TGFVAR + TGFCAB + AD_TGFITECOMPL), trocando a dimensão de agregação de `codparc` para `i.romaneio`.
### 3. Entradas
Nenhum parâmetro — view direta.
### 4. Saídas
V_QTDDEV, V_VLRDEV, NUNOTAORIG, SEQUENCIAORIG, REFUGO, NUNOTADEST, ROMANEIO.
### 5. Regras de negócio
Mesmas regras de VW_BMC_GET_QTD_DEV_VENDA_FOR (Objeto 19), trocando a granularidade de agregação para romaneio — permite saber quanto de um romaneio (lote de colheita/entrada) específico foi devolvido.
### 6. Cálculos
`V_QTDDEV = SUM(i.QUANTITY)`; `V_VLRDEV = SUM(i.vlrtot)`; agregado por nunotaorig, sequenciaorig, REFUGO, romaneio.
### 7. Dependências
| Tipo | Nome | Utilização | Está nos arquivos? |
|---|---|---|---|
| Tabela | TGFVAR / TGFCAB | Vínculo e cabeçalho de devolução | ✖ [EXTERNO] (Sankhya padrão) |
| Tabela | AD_TGFITECOMPL | Base de itens customizada | ✖ [EXTERNO] |
### 8. Objetos chamados
Nenhum.
### 9. Objetos que provavelmente dependem deste objeto
VW_NOTAS_31 (Objeto 3) — citada na Seção 5 da doc original desta view como fonte da distinção de REFUGO em devoluções (dispensa REFUGO no cálculo principal porque a distinção já vem daqui).
### 10. Diagrama textual de dependências
VW_BMC_GET_QTD_DEV_VENDA2

   ├─ TGFVAR / TGFCAB       [EXTERNO] (Sankhya padrão)

   └─ AD_TGFITECOMPL        [EXTERNO]
### 11. Pontos críticos
Mesmo ponto da Objeto 19 — família de 3 views quase-idênticas.
### 12. Sugestões de melhoria
Nenhuma além da já registrada na Objeto 19.
### 13. Resumo executivo (para analista funcional)
Mesma devolução líquida, agora quebrada por romaneio (lote de entrada) — permite rastrear devolução até o lote físico de origem.

## OBJETO 21 — SANKHYA.VW_ARG_DEB_CRE_ITE (View)
### 1. Resumo
Calcula o rateio de débito/crédito por item de nota, em duas modalidades identificadas pela coluna CT_CL: 'CT' (consolidado por controle, `AD_CONSCTRL='S'`) e 'CL' (por calibre/fornecedor, `AD_CONSCTRL='C'`). É a fonte de `CD_ITE`/`CD_ITE2` citada em `VW_NOTAS_31` (Objeto 3, Seção 6 — "Rateio de débito por controle").
### 2. Fluxo de execução
Duas metades quase idênticas unidas por `UNION ALL`, ambas lendo de `VW_TGFCAB_ITE` (Objeto 25): a primeira filtra `AD_CONSCTRL='S'` e agrupa por CONTROLE (branch 'CT'); a segunda filtra `AD_CONSCTRL='C'` e não agrupa por controle, usando `' '` fixo (branch 'CL'). Cada metade soma valores de débito (AD_CRE_DEB='D') e crédito (AD_CRE_DEB='C') separadamente, e também converte pra moeda (dividindo por VLRCOT).
### 3. Entradas
Nenhum parâmetro — view direta sobre VW_TGFCAB_ITE.
### 4. Saídas
CODPROJ, PROJETO, CODPROD, CONTROLE, AD_CALIBRE, DB_VLRTOT, CR_VLRTOT, VLRTOT (líquido), DB_VLRTOTMOE, CR_VLRTOTMOE, VLRTOTMOE, AD_CRE_DEB, NUNOTA, QTD, DB_VLRTOT1, CR_VLRTOT1, DB_VLRTOTMOE1, CR_VLRTOTMOE1 (variantes não divididas pela quantidade), CT_CL ('CT'/'CL'), AD_CONSCTRL.
### 5. Regras de negócio
- Branch 'CT': exige `STATUSNFE='A'` para débito, `AD_CRE_DEB IN ('C','D')`, `AD_CONSCTRL='S'`, `STATUSNOTA='L'`, exclui notas em `AD_NOTASEXC` e notas substituídas (`AD_NUNOTASUB`). Agrupa por CODPROJ/PROJETO/CODPROD/CONTROLE/AD_CRE_DEB/AD_CALIBRE/AD_CONSCTRL.
- Branch 'CL': mesma exclusão de `AD_NOTASEXC`/substituídas, mas a condição de débito é mais ampla (`STATUSNFE='A' OR CODTIPOPER IN (2235)`), `AD_CONSCTRL='C'`, e **não** agrupa por CONTROLE (fica `' '` fixo) — ou seja, consolida por produto/calibre, não por controle individual.
- `VLRTOT`/`VLRTOTMOE` (sem sufixo) são o **líquido** (`SUM(VLRTOT)/SUM(quantidade)`, ou seja, uma média ponderada); `DB_VLRTOT1`/`CR_VLRTOT1` (com sufixo `1`) são os brutos, não divididos — duas granularidades coexistindo na mesma linha.
- Comentários no código (`/* ... */`) mostram fórmulas anteriores que dividiam DB_VLRTOT/CR_VLRTOT pela quantidade — foram substituídas pela soma bruta; sinal de que essa divisão foi removida numa correção/otimização anterior.
### 6. Cálculos
`DB_VLRTOT = SUM(CASE WHEN AD_CRE_DEB='D' THEN VLRTOT ELSE 0 END)`; `CR_VLRTOT` análogo para 'C'; `VLRTOT = SUM(VLRTOT) / SUM(quantidade líquida)`; versões `*MOE` dividem por `VLRCOT` antes de somar.
### 7. Dependências
| Tipo | Nome | Utilização | Está nos arquivos? |
|---|---|---|---|
| View | VW_TGFCAB_ITE | Fonte única de dados (nota+item já enriquecidos) | ✔ Sim (Objeto 25) |
| Tabela | AD_NOTASEXC | Notas excluídas do BI | ✖ [EXTERNO] |
### 8. Objetos chamados
VW_TGFCAB_ITE (Objeto 25).
### 9. Objetos que provavelmente dependem deste objeto
VW_NOTAS_31 (Objeto 3) — fonte de CD_ITE/CD_ITE2 no rateio de débito/crédito por controle e por calibre (Seção 6).
### 10. Diagrama textual de dependências
VW_ARG_DEB_CRE_ITE

   ├─ VW_TGFCAB_ITE      (Objeto 25)

   └─ AD_NOTASEXC        [EXTERNO]
### 11. Pontos críticos
- Duas condições de "débito válido" diferentes entre os branches ('CT' exige só STATUSNFE='A'; 'CL' também aceita CODTIPOPER=2235) — `[VALIDAR]` não está claro se essa assimetria é intencional (CODTIPOPER 2235 só se aplica ao caso calibre/fornecedor) ou uma divergência não documentada.
- Coexistência de valores líquidos (sem sufixo) e brutos (`1`) na mesma linha exige que quem consome saiba qual usar para qual finalidade — não há comentário na view explicando a diferença.
### 12. Sugestões de melhoria
[VALIDAR] Documentar (comentário na view ou aqui) por que CODTIPOPER=2235 é aceito como débito válido só no branch 'CL', não no 'CT'.
### 13. Resumo executivo (para analista funcional)
Distribui valores de débito e crédito entre os itens de uma nota, de duas formas (por controle individual do lote, ou por produto/calibre agregado) — é uma peça do cálculo de rateio financeiro que a "planilha mestre" (VW_NOTAS_31) usa para saber quanto de crédito/débito cabe a cada item.

## OBJETO 22 — SANKHYA.VW_ARG_CRE_DEB (View)
### 1. Resumo
View mais complexa do grupo: consolida, por nota de venda, a semana de packing, dados logísticos (navio, portos, incoterm), valor líquido de desconto financeiro, valor já baixado (pago) e um flag "possui_financeiro" indicando se a nota tem vínculo com o financeiro. Fonte de `VW_ARG_CRE_DEB` citada em `VW_NOTAS_31` (Objeto 3) como "Crédito/débito por projeto (moeda)".
### 2. Fluxo de execução
1. CTE `vlrbaixa_cte`: soma valores já baixados (pagos) por nota em `tgffin`, filtrando por tipos de operação de baixa específicos (1404/1408/1407/1400 a receber; 1502/1501/1308/1500 a pagar) e excluindo históricos de "substituição de portador".
2. CTE `vlrdesc_cte`: soma desconto financeiro por nota.
3. CTE `main_query`: junta TGFCAB com ~12 tabelas (produto, parceiro, projeto, tipo de operação, moeda, portos, navio, cidade/UF/país), calculando semana de packing (com tratamento especial para notas substituídas via `AD_NUNOTASUB`), mercado MI/ME, valor em moeda e taxa de câmbio. Filtra vendas liquidadas (`tipmov='V'`, `statusnota='L'`) que não tenham devolução total associada, com uma cadeia de `NOT EXISTS`/condições sobre `AD_CRE_DEB`, `VW_TGFPARC_TGFEMP` (exclui parceiros do grupo) e notas substituídas.
4. SELECT final: junta `main_query` com `vlrbaixa_cte` e com `tgffin` (duas vezes, `f_nota`/`f_credito`) para determinar `possui_financeiro`, e agrega tudo por nota.
### 3. Entradas
Nenhum parâmetro — view direta.
### 4. Saídas
PACKINGWEEK, GRUPO, DESCROPER, CODPROJ, PROCESSO, NUNOTA, NUMNOTA, DTNEG, TIPOPROD, CLIENTE, AD_EX_CONTAINER, BOXES, VESSEL, SHIPPINGLINE, ETD, ETA, PORTO_ORIGEM, PORTO_DESTINO, INCONTERMS, AD_EX_TERMOG, MODTERMOGRAFO, AD_PALLET, MERCADO, VLRMOEDA, VLRNOTA (já líquido de desconto), VLRBAIXA, NOMEMOEDA, VLRMOEDAEX, AD_CRE_DEB, COTACAO, POSSUI_FINANCEIRO ('S'/'N'), NUNOTAORIG, AD_CONSCTRL.
### 5. Regras de negócio
- PACKINGWEEK: semana ISO calculada a partir de `dtfatur` (ou da nota original, se a nota for substituta via `AD_NUNOTASUB`) — mesmo padrão de cálculo de semana usado em `VW_NOTAS_31` (Objeto 3, Seção 6).
- MERCADO: mesma regra de MI/ME de `VW_NOTAS_31` (país 55 + sem data prevista de embarque ⇒ MI).
- `AD_CRE_DEB`: força 'D' quando `CODTIPOPER=2126`, senão usa o valor cadastrado no tipo de operação.
- Exclui parceiros que são empresas do próprio grupo (`VW_TGFPARC_TGFEMP`, Objeto 26) e notas já substituídas.
- `VLRBAIXA`: valor pago/baixado, limitado ao valor da nota (nunca maior que `VLRNOTA`) — trata baixa parcial/excedente.
- `POSSUI_FINANCEIRO`: 'S' quando existe ao menos um lançamento em `tgffin` vinculado à nota (direto ou por crédito de projeto com tipo de operação 1317 e `ad_numop` contendo 'CREDIT'). Havia uma versão anterior comentada dessa mesma lógica como subquery correlacionada (`NVL((SELECT 'S' ...))`) — substituída por `COUNT(...) > 0` (provável otimização, mesma regra).
### 6. Cálculos
`VLRNOTA = mq.vlrnota - NVL(mq.VLRDESC, 0)`; `VLRBAIXA = LEAST(vb.vlrbaixa, mq.vlrnota)` (via CASE); `VLRMOEDAEX = ROUND(vlrnota / NULLIF(vlrmoeda,0), 2)`.
### 7. Dependências
| Tipo | Nome | Utilização | Está nos arquivos? |
|---|---|---|---|
| View | VW_TGFPARC_TGFEMP | Exclusão de parceiros do grupo | ✔ Sim (Objeto 26) |
| Tabela | TGFCAB / TGFITE / TGFPRO / TGFPAR / TCSPRJ / TGFTOP / TSIMOE / TGFVEI / TSICID / TSIUFS | Nota, item, produto, parceiro, projeto, tipo de operação, moeda, navio, localização | ✖ [EXTERNO] (Sankhya padrão) |
| Tabela | AD_PORTO | Portos de embarque/descarga | ✖ [EXTERNO] |
| Tabela | TGFFIN | Lançamentos financeiros (baixa, crédito) | ✖ [EXTERNO] (Sankhya padrão) |
| Tabela | TGFVAR | Vínculo de nota substituta | ✖ [EXTERNO] (Sankhya padrão) |
### 8. Objetos chamados
VW_TGFPARC_TGFEMP (Objeto 26).
### 9. Objetos que provavelmente dependem deste objeto
VW_NOTAS_31 (Objeto 3) — fonte de crédito/débito por projeto em moeda (OPEN_AMOUNT, CVLRNOTA, DVLRNOTA, CVLRMOEDAEX, DVLRMOEDAEX).
### 10. Diagrama textual de dependências
VW_ARG_CRE_DEB

   ├─ VW_TGFPARC_TGFEMP (Objeto 26)

   └─ TGFCAB / TGFITE / TGFPRO / TGFPAR / TCSPRJ / TGFTOP / TSIMOE / TGFVEI /

      TSICID / TSIUFS / AD_PORTO / TGFFIN / TGFVAR   [EXTERNO] (Sankhya padrão)
### 11. Pontos críticos
- View muito densa (14+ joins, 3 CTEs, subquery lateral) — mesmo padrão de peso das views centrais do stack (VW_NOTAS_31, V9).
- `[VALIDAR]` A lista de códigos de tipo de operação de baixa (1404/1408/1407/1400/1502/1501/1308/1500) e o filtro por texto `NOT LIKE '%substituição de portador%'` são valores/strings mágicos sem tabela de-para — mudança no cadastro Sankhya desses tipos de operação quebra o cálculo silenciosamente.
### 12. Sugestões de melhoria
[VALIDAR] Documentar (ou externalizar para tabela de configuração) os códigos de tipo de operação de baixa usados em `vlrbaixa_cte`.
### 13. Resumo executivo (para analista funcional)
Monta a "ficha financeira" de cada nota de venda: quanto já foi pago, se tem vínculo com o financeiro, dados de logística (navio, portos, prazo) e a semana de packing — é uma das fontes de crédito/débito que a planilha mestre de vendas usa.

## OBJETO 23 — SANKHYA.VW_DESCFIN (View)
### 1. Resumo
Calcula o desconto financeiro proporcional por item de nota, ratando o desconto total lançado no financeiro entre os itens da nota pelo peso de cada um no valor total. Citada em `VW_NOTAS_31` (Objeto 3, Seção 5) como "Desconto financeiro proporcional".
### 2. Fluxo de execução
View com **dois braços unidos por `UNION ALL`, divididos por data de negociação** (`CAB.DTNEG`): braço "legado" para `DTNEG < DATE '2026-01-01'` (rateia o desconto sobre `VLRNOTA` da nota) e braço "novo" para `DTNEG >= DATE '2026-01-01'` (rateia sobre a soma viva de `VLRTOT` dos itens ainda válidos, via `AD_TGFITECOMPL`/`TGFITE` com `QTDNEG - AD_QTDDEV > 0`).
### 3. Entradas
Nenhum parâmetro — view direta.
### 4. Saídas
NUNOTA, NUMNOTA, CODPROD, SEQITE, VLRNOTA, VLRDESC, DESCPROP (desconto proporcional ao item), QUANTITY, TRACEABILITY.
### 5. Regras de negócio
- **Corte de data já em vigor** (`DATE '2026-01-01'`, e a data de hoje neste projeto é 07/07/2026) — diferente das datas de corte de `VW_NOTAS_31` (`PED_FRETE_VENDAS`/`PED_DESP_LOG`, ainda no futuro); aqui a mudança de regra **já está ativa** para todas as notas do ano corrente.
- Braço legado: só considera lançamentos financeiros com `VLRDESC > 0.10` (ignora descontos residuais/arredondamento) e rateia sobre o `VLRNOTA` do cabeçalho.
- Braço novo: rateia sobre a soma de `VLRTOT` dos itens **ainda válidos** (quantidade negociada menos devolução > 0), usando `AD_TGFITECOMPL` como base de item — ou seja, o rateio novo exclui itens totalmente devolvidos da base de rateio, o legado não distinguia isso.
- `[VALIDAR]` A mudança de fonte de rateio (VLRNOTA fixo → soma viva de itens) é uma mudança funcional, não só de sintaxe — o valor de `DESCPROP` por item pode divergir entre uma nota antiga e uma nova mesmo com desconto total idêntico, se a nota tiver itens devolvidos.
### 6. Cálculos
Legado: `DESCPROP = ROUND(SUM(VLRDESC)/VLRNOTA × (QUANTITY×VLRUNIT), 2)`. Novo: `DESCPROP = ROUND(VLRDESC_TOT / SUM(VLRTOT) OVER (PARTITION BY NUNOTA) × (QUANTITY×VLRUNIT), 2)`.
### 7. Dependências
| Tipo | Nome | Utilização | Está nos arquivos? |
|---|---|---|---|
| Tabela | VGFFIN | Lançamentos financeiros (desconto) | ✖ [EXTERNO] |
| Tabela | AD_TGFITECOMPL / TGFITE / TGFCAB | Item/nota (braço novo) | ✖ [EXTERNO] |
### 8. Objetos chamados
Nenhum.
### 9. Objetos que provavelmente dependem deste objeto
VW_NOTAS_31 (Objeto 3) — componente de `VLR_DESC_COM` (desconto do item + desconto financeiro proporcional).
### 10. Diagrama textual de dependências
VW_DESCFIN

   ├─ VGFFIN                          [EXTERNO]

   └─ AD_TGFITECOMPL / TGFITE / TGFCAB [EXTERNO]
### 11. Pontos críticos
`[VALIDAR]` Corte de regra por data (`2026-01-01`) já em vigor sem reconciliação registrada neste repositório entre o braço legado e o novo — se a mudança de fonte de rateio (VLRNOTA vs. soma viva) gerar diferença material em notas com devolução parcial, isso já está impactando o `VLR_DESC_COM`/margem de notas do ano corrente sem que haja registro de validação.
### 12. Sugestões de melhoria
[VALIDAR] Reconciliar DESCPROP por ANO/SEMANA/FRUTA para notas próximas ao corte de 2026-01-01, comparando braço legado vs. novo em notas com devolução parcial — para confirmar que a mudança de fonte de rateio não introduziu divergência de margem não sinalizada.
### 13. Resumo executivo (para analista funcional)
Divide o desconto financeiro (lançado uma vez para a nota inteira) entre os itens dessa nota, proporcionalmente ao valor de cada um — a partir de 2026, esse rateio passou a ignorar itens já devolvidos, o que pode mudar o valor por item comparado a notas mais antigas com desconto e devolução parcial ao mesmo tempo.

## OBJETO 24 — SANKHYA.VW_PERCPROC_NF_V4 (View)
### 1. Resumo
Calcula o percentual que cada nota fiscal representa dentro de um "processo" (projeto guarda-chuva, código entre 4.000.000.000 e 4.999.999.999) — usado para ratear custos/despesas lançados no nível do processo entre as notas individuais que o compõem.
### 2. Fluxo de execução
CTE `BASE`: para cada item de venda liquidada vinculado a um processo (projeto na faixa 4bi-5bi), calcula o valor do item já líquido de devolução (via `VW_BMC_GET_QTD_DEV_VENDA`, Objeto 18) e sua fração do valor total da nota (usando calibre via `AD_MONTPALLETITE` quando disponível). CTE `AGREGADO`: soma o valor de todas as notas do mesmo processo/parceiro/tipo de operação. SELECT final: percentual = valor do item / total do processo.
### 3. Entradas
Nenhum parâmetro — view direta.
### 4. Saídas
PROCESSO, NUNOTA, VLRNOTA, NRO_NFS (quantidade de notas no processo), TOTAL_VLRNOTA (valor total do processo), PERCENTUAL.
### 5. Regras de negócio
- Só considera itens com quantidade líquida positiva (`QTDNEG - devolução > 0`, via LEFT JOIN com Objeto 18).
- Processo é identificado por uma faixa numérica de código de projeto (4bi-5bi) — valor mágico sem tabela de-para explicando por que essa faixa específica identifica "processo" (provavelmente uma convenção de numeração de projeto do Sankhya para este cliente).
- Prioriza o vínculo por pallet/calibre (`AD_MONTPALLETITE`) quando existir, senão usa a quantidade negociada direta do item.
### 6. Cálculos
`VLRNFROPP = VLRNOTA × ((qtd do item) × VLRUNIT) / SUM(VLRTOT da nota)`; `PERCENTUAL = SUM(VLRNFROPP) / TOTAL_VLRNOTA do processo`.
### 7. Dependências
| Tipo | Nome | Utilização | Está nos arquivos? |
|---|---|---|---|
| View | VW_BMC_GET_QTD_DEV_VENDA | Líquido de devolução por item | ✔ Sim (Objeto 18) |
| Tabela | TGFCAB / TGFITE / TGFTOP | Nota, item, tipo de operação | ✖ [EXTERNO] (Sankhya padrão) |
| Tabela | AD_MONTPALLETITE | Vínculo de pallet/calibre | ✖ [EXTERNO] |
### 8. Objetos chamados
Nenhum (usa a view VW_BMC_GET_QTD_DEV_VENDA via JOIN, não chamada escalar).
### 9. Objetos que provavelmente dependem deste objeto
VW_NOTAS_31 (Objeto 3) — coluna PERCENTUAL, usada no rateio de crédito/débito por projeto.
### 10. Diagrama textual de dependências
VW_PERCPROC_NF_V4

   ├─ VW_BMC_GET_QTD_DEV_VENDA (Objeto 18)

   ├─ TGFCAB / TGFITE / TGFTOP     [EXTERNO] (Sankhya padrão)

   └─ AD_MONTPALLETITE             [EXTERNO]
### 11. Pontos críticos
`[VALIDAR]` Faixa de código de projeto (4.000.000.000–4.999.999.999) hardcoded como identificador de "processo" — se a numeração de projetos mudar de convenção, esta view para de capturar processos silenciosamente.
### 12. Sugestões de melhoria
[VALIDAR] Documentar (ou mover para uma tabela de configuração) o significado da faixa 4bi-5bi de código de projeto.
### 13. Resumo executivo (para analista funcional)
Quando várias notas fiscais pertencem ao mesmo "processo" (embarque/projeto consolidado), esta view calcula que fatia (%) cada nota representa do total — usado para dividir custos ou despesas lançadas no processo inteiro entre as notas que o compõem.

## OBJETO 25 — SANKHYA.VW_TGFCAB_ITE (View)
### 1. Resumo
View de enriquecimento "cabeçalho + item": uma junção ampla de nota (TGFCAB), item (TGFITE), produto, grupo de produto, parceiro, projeto (resolvido a nível de item ou de cabeçalho), natureza contábil e centro de custo (idem, item ou cabeçalho), localização geográfica do parceiro. É a base comum de `VW_ARG_DEB_CRE_ITE` (Objeto 21) e referenciada por `VW_NOTAS_31` (Objeto 3) como "Cabeçalho+item (pedidos frete/log)".
### 2. Fluxo de execução
SELECT direto (sem CTE) com ~13 INNER JOINs (tipo de operação, item, produto, grupo, parceiro, projeto por item, projeto por cabeçalho, natureza, centro de custo por cabeçalho, cidade/UF/país, centro de custo por item, centro de custo por cabeçalho de novo) + 1 LEFT JOIN (usuário de inclusão).
### 3. Entradas
Nenhum parâmetro — view direta.
### 4. Saídas
~50 colunas: CODEMP, CODPROJ/PROJETO (resolvido: usa o do item se preenchido, senão o do cabeçalho), dados temporais (DTENTSAI/DTNEG/DTFATUR/DTVAL/DTCONTAB), parceiro, moeda, CODCENCUS/DESCRCENCUS (idem resolução item/cabeçalho), natureza, valores (VLRNOTA/VLRFRETE/VLRMOEDA), tipo de movimento/operação, colunas de item (produto, controle, pallet, calibre, localização, quantidade, valores unit/total, peso, grupo de produto), MERCADO (MI/ME, mesma regra de VW_NOTAS_31), AD_CRE_DEB, AD_CONSCTRL, AD_QTDNEG/AD_QTDNEGOR.
### 5. Regras de negócio
- CODPROJ/PROJETO: prioriza o projeto do **item** (`AD_CODPROJ`); se for 0 (não preenchido), usa o projeto do **cabeçalho**. Mesmo padrão de resolução para CODCENCUS/DESCRCENCUS (centro de custo do item, com fallback pro do cabeçalho).
- MERCADO: mesma regra de MI/ME das demais views do stack (país 55 sem data prevista de embarque ⇒ MI).
- `--ITE.AD_CODPROJ` aparece comentado no SELECT — a coluna bruta não é exposta diretamente (só o CODPROJ já resolvido).
### 6. Cálculos
`VLRNOTA_MOE = ROUND(VLRNOTA / NULLIF(VLRMOEDA,0), 2)`; `VLRCOT = CASE WHEN VLRMOEDA=0 THEN 1 ELSE VLRMOEDA END`.
### 7. Dependências
| Tipo | Nome | Utilização | Está nos arquivos? |
|---|---|---|---|
| Tabela | TGFCAB / TGFTOP / TGFITE / TGFPRO / TGFGRU / TGFPAR / TCSPRJ / TGFNAT / TSICUS / TSICID / TSIUFS / TSIPAI / TSIUSU | Nota, item, produto, grupo, parceiro, projeto, natureza, centro de custo, localização, usuário | ✖ [EXTERNO] (Sankhya padrão) |
### 8. Objetos chamados
Nenhum.
### 9. Objetos que provavelmente dependem deste objeto
VW_ARG_DEB_CRE_ITE (Objeto 21) — fonte única de dados. VW_NOTAS_31 (Objeto 3) — referenciada para pedidos de frete/log.
### 10. Diagrama textual de dependências
VW_TGFCAB_ITE

   └─ TGFCAB / TGFTOP / TGFITE / TGFPRO / TGFGRU / TGFPAR / TCSPRJ (x2) /

      TGFNAT / TSICUS (x3) / TSICID / TSIUFS / TSIPAI / TSIUSU   [EXTERNO] (Sankhya padrão)
### 11. Pontos críticos
Múltiplos INNER JOIN na mesma tabela `TSICUS` com aliases diferentes (CUS, CUSI, CUSC) para resolver centro de custo em 3 granularidades diferentes — legível mas fácil de confundir qual alias representa qual nível (cabeçalho vs. item vs. resolvido).
### 12. Sugestões de melhoria
Nenhuma sugestão específica — view é uma junção direta sem lógica de cálculo complexa.
### 13. Resumo executivo (para analista funcional)
É uma "visão combinada" de nota + item já com projeto e centro de custo resolvidos (prioriza o do item, cai pro do cabeçalho se não tiver) — serve de base para as views de rateio de crédito/débito.

## OBJETO 26 — SANKHYA.VW_TGFPARC_TGFEMP (View)
### 1. Resumo
Lista os parceiros (TGFPAR) que são, na verdade, empresas do próprio grupo econômico (identificados por CGC/CPF em comum com o cadastro de empresas TSIEMP) — usada para excluir transações intercompany das views de crédito/débito e da planilha mestre de vendas.
### 2. Fluxo de execução
SELECT DISTINCT direto: junta TGFPAR com TSIEMP pelo CGC/CPF, excluindo um CGC específico e exigindo CGC/CPF preenchido (>0).
### 3. Entradas
Nenhum parâmetro — view direta.
### 4. Saídas
CODPARC, NOMEPARC, CGC_CPF.
### 5. Regras de negócio
- Um parceiro "é do grupo" quando seu CGC/CPF bate com o de alguma empresa cadastrada em TSIEMP.
- `[VALIDAR]` `EMP.CGC<>27185579821` exclui explicitamente uma empresa específica do grupo desta lista — não está documentado qual empresa é essa nem por que ela é tratada como "não é parceiro do grupo para este fim" (pode ser a própria empresa matriz/emissora, que não faz sentido aparecer como "parceiro" dela mesma; ou pode ser uma filial que deveria ser tratada como parceiro externo por algum motivo de negócio).
### 6. Cálculos
Nenhum — filtro direto.
### 7. Dependências
| Tipo | Nome | Utilização | Está nos arquivos? |
|---|---|---|---|
| Tabela | TGFPAR / TSIEMP | Parceiro e cadastro de empresas do grupo | ✖ [EXTERNO] (Sankhya padrão) |
### 8. Objetos chamados
Nenhum.
### 9. Objetos que provavelmente dependem deste objeto
VW_ARG_CRE_DEB (Objeto 22) — exclusão de parceiros do grupo. VW_NOTAS_31 (Objeto 3) — mesma finalidade ("Parceiros que são empresas do grupo").
### 10. Diagrama textual de dependências
VW_TGFPARC_TGFEMP

   └─ TGFPAR / TSIEMP   [EXTERNO] (Sankhya padrão)
### 11. Pontos críticos
`[VALIDAR]` CGC hardcoded (27185579821) sem comentário explicando qual empresa é ou por que está excluída — se essa empresa for renumerada/refeita no cadastro, a exclusão para de funcionar silenciosamente.
### 12. Sugestões de melhoria
[VALIDAR] Documentar (comentário na view) qual empresa é o CGC 27185579821 e por que é excluída da lista de "parceiros do grupo".
### 13. Resumo executivo (para analista funcional)
Identifica quais "clientes/fornecedores" cadastrados são, na real, outras empresas do mesmo grupo econômico — usado para não contar venda entre empresas do próprio grupo como se fosse venda externa de verdade.

SEÇÃO FINAL — Lista de dependências para você trazer
Objetos referenciados pelos arquivos já trazidos mas ainda não presentes no repositório. Priorizados por relevância para a lógica de negócio (os padrão Sankhya TGF*/TSI*/TCS* têm estrutura conhecida e ficam por último).

✅ Grupo 🔴 completo, trazido e documentado (07/07/2026): as 5 views de custo (VW_BMC_BI_CUSTOS_PROD_OTM, VW_BMC_BI_PERCA_PACK, VW_BMC_FRETE_MARITIMO, VW_BMC_DESPESAS_PORTUARIAS, VW_BMC_BI_PROV_FORNECEDORES — Objetos 13 a 17) e as 9 functions de cálculo (FU_BMC_GETPROVFORN, FU_BMC_GETROYALTIES, FU_BMC_GETCOMVENDA, FU_BMC_GETPERCCOMVENDA, FU_BMC_GETCUSTOPREVISTO, FU_BMC_PRECO_CUSTO_GER, FU_ARG_TXADM_CUSTO_GER, FUN_ARG_VLRETIQSRV, FUN_ARG_VLRETIQ — Objetos 4 a 12).

✅ Grupo 🟠 (views de quantidade/devolução/financeiro) quase completo, trazido e documentado (07/07/2026): VW_BMC_GET_QTD_DEV_VENDA (Objeto 18), VW_BMC_GET_QTD_DEV_VENDA_FOR (19), VW_BMC_GET_QTD_DEV_VENDA2 (20), VW_ARG_DEB_CRE_ITE (21), VW_ARG_CRE_DEB (22), VW_DESCFIN (23), VW_PERCPROC_NF_V4 (24), VW_TGFCAB_ITE (25), VW_TGFPARC_TGFEMP (26).

🔴 Pendência de conteúdo (não é objeto novo, é erro ao trazer)
VW_AD_REC_COMD — o DBExplorer (Sankhya Om) dá erro consistente ao abrir esta view especificamente ("Cannot read properties of undefined (reading 'colunas')"), reproduzido em 2 tentativas. Pode ser um bug pontual da ferramenta ou o objeto estar de fato inválido no Oracle — [VALIDAR] checar `SELECT status FROM all_objects WHERE object_name = 'VW_AD_REC_COMD'` direto no banco antes de insistir via DBExplorer.

🟡 Descobertas nesta rodada — variações não previstas na lista original, ainda não trazidas (mencionar se quiser que eu busque numa próxima rodada)
VW_BMC_GET_QTD_DEV_VENDA_ROM (variação de _FOR/_2, possivelmente "por romaneio" com lógica diferente de VENDA2), VW_ARG_CRE_DEB_BAIXA, VW_ARG_CRE_DEB_NOVA, VW_ARG_CRE_DEB1 (variações de VW_ARG_CRE_DEB), VW_DESCFIN_V2 (variação de VW_DESCFIN).

VW_BMC_GETPRECOENTRADA / FU_BMC_GETPRECOENTRADA — [VALIDAR] confirmar se é um único objeto (nome com prefixo inconsistente num dos dois lugares) ou dois objetos distintos; ver Objeto 13, Pontos críticos

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
Descoberta nesta rodada (07/07/2026): obtemcusto4 — function utilitária padrão Sankhya, chamada por FUN_ARG_VLRETIQ e por VW_BMC_BI_CUSTOS_PROD_OTM (Objeto 2 dependency). Corpo ainda não trazido — comportamento é uma caixa-preta parcial (ver Objeto 11, Pontos críticos).

Sugestão de como enviar
Grupos 🔴 e 🟠 praticamente fechados. Falta só VW_AD_REC_COMD (erro na ferramenta, ver acima) e, opcionalmente, as variações descobertas nesta rodada. Para a próxima rodada, priorizar o grupo 🟠 restante (materialized views VW_M_CUSTOMED_SEMANA/VW_M_NFVENDAS_DEVINT/VW_M_CONTROLE_VLRMP) ou o grupo 🟡.

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
