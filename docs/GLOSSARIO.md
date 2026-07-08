# Glossário e Dicionário de Dados — Stack de Margem BI

Três seções: (1) termos e siglas de domínio usados nos 26 objetos documentados, (2) os 26 objetos resumidos numa frase cada, (3) dicionário das colunas finais que chegam ao painel de margem. Tudo aqui é extraído do que já está em `docs/STACK_MARGEM_BI.md` — este arquivo não define nada novo, só torna buscável o vocabulário que hoje está espalhado por 26 seções.

Onde o significado exato de uma sigla não está expandido em nenhum lugar da documentação-fonte, está marcado `[VALIDAR]` em vez de inventado.

## 1. Termos e siglas de domínio

| Termo | Significado |
|---|---|
| **MP** | Matéria-prima. |
| **MI / ME** | Mercado Interno / Mercado Externo. |
| **INCONTERMS** (`CIF`, `FOB`, `CIP`, `CPT`) | Termo de comércio internacional. Determina se o frete entra como receita (embutido no preço, quando `CIF`/`CIP`/`CPT`) ou como custo separado (fora disso). |
| **PROCESSO** | Classificação do item de venda: projeto normal, `REFUGO PA` (produto acabado descartado), `REFUGO MP` (matéria-prima descartada — **margem sempre zerada**), ou `0-TRANSFERENCIAS ENTRE FILIAIS`. |
| **REFUGO** | Sucata/descarte — `PA` (produto acabado) ou `MP` (matéria-prima). |
| **TIPMOV** | Tipo de movimento da nota fiscal. `V` = venda, `D` = devolução (uso observado no SQL — Sankhya padrão). |
| **STATUSNOTA** | Status da nota. `L` = liquidada — usado para filtrar devoluções válidas (`DEV_ITEM`, `VW_NOTAS_31`). |
| **CENCUS / CODCENCUS** | Centro de Custo. |
| **CALIBRE / AD_CALIBRE** | Calibre (tamanho) do produto — granularidade alternativa de rateio de crédito/débito. |
| **CONTROLE** | Código de controle de lote/pallet — outra granularidade de rateio de crédito/débito. |
| **ROMANEIO / ROMANEIO_NUM** | Documento de romaneio (registro de entrada de matéria-prima). `ROMANEIO_NUM` é o valor convertido para número quando é numérico (`ITE_BASE`, `VW_NOTAS_31`). |
| **NUNOTA** | Número único da nota fiscal — chave Sankhya. |
| **SEQUENCIA / SEQUENCIAORIG** | Sequência do item dentro da nota (nota original, no caso de devolução). |
| **NROPALLET** | Identificador do pallet — unidade de rastreabilidade de custo (ficha de custo em `VW_BMC_BI_CUSTOS_PROD_OTM`). |
| **LOTEARGO / LOTEMP** | Lote Argofruta / lote de matéria-prima. |
| **CODPARC / CODPRODUTOR** | Código do parceiro (cliente ou fornecedor) / código do produtor de matéria-prima. |
| **CGC / CPF** | Documento de identificação de empresa/pessoa — usado para identificar parceiros que são, na verdade, empresas do próprio grupo (`VW_TGFPARC_TGFEMP`, Objeto 26). |
| **DESCFIN** | Percentual de desconto financeiro cadastrado no parceiro (`TGFPAR.DESCFIN`). Hoje é a fonte direta de `PERCDESCCONTRATUAL` em `VW_NOTAS_31` — ver `docs/RISCOS_ABERTOS.md` R01 sobre a divergência entre essa fonte e o que a documentação de rev. 3 descreve. |
| **PERCDESCCONTRATUAL** | Percentual de desconto contratual aplicado à nota. |
| **VLR_DESC_COM** | Valor total de desconto comercial (desconto do item + parcela proporcional de desconto financeiro). |
| **AD_PERCSPREADRISCO** | Percentual de "spread de risco" embutido no valor de venda; removido no cálculo para achar o valor líquido real (`VLR_TOTAL_CX_LIQUIDA`). |
| **DIF_SPREAD** | Diferença entre o valor da venda com e sem o spread de risco. |
| **CUSTOMEDIO** | Custo médio semanal de matéria-prima — vem de `VW_M_CUSTOMED_SEMANA` (materialized view, `[EXTERNO]`), casada por semana de entrada + produto + calibre. |
| **CUSTO_MP / CUSTO_MP_CALC** | Custo de matéria-prima da ficha de custo (`VW_BMC_BI_CUSTOS_PROD_OTM`) / custo calculado quando não há valor pré-definido na ficha. |
| **CUSTOTOTALGER** | Custo total "gerencial" — soma modular por fruta, usando `CUSTO_MP`. Calculado em 2 níveis na V9 (ver `docs/RISCOS_ABERTOS.md` R18). |
| **CUSTOTOTALGERC** | Variante de `CUSTOTOTALGER` usando `CUSTOMEDIO` em vez de `CUSTO_MP`. |
| **MARGEMGER / PERCMARGEMGER** | Margem gerencial em valor / percentual — a versão que efetivamente sai no painel (a da camada externa da V9, não a de N2). |
| **VLR_MARGEM / PERC_MARGEM** | Margem "simples" (não gerencial): receita líquida menos custo calculado, sem as regras específicas por fruta. |
| **PROVISAO_FORNECEDOR_GER** | Provisão de fornecedor gerencial — calculada só para `AVOCADO` e para `UVA` com `prv='S'`; demais frutas = 0. |
| **TXADM_CUSTO_GER** | Taxa administrativa aplicada sobre o custo geral do lote (`FU_ARG_TXADM_CUSTO_GER`). |
| **ROYALT / AD_ROYALTS** | Indicador (`S`/`N`) se o item paga royalties de patente de variedade. |
| **PED_FR / PED_LOG** | Pedidos pendentes de frete / de despesa logística ainda não faturados. |
| **ETD / ETA / ETDR / ETAR** | Datas logísticas de embarque/chegada (estimado e revisado). `[VALIDAR]` sigla não expandida na documentação-fonte — inferido como *Estimated Time of Departure/Arrival* por convenção do comércio exterior, não confirmado no repositório. |
| **VESSEL / BOOKING / LINER** | Navio / reserva de contêiner / armador. |
| **OPEN_AMOUNT** | Valor em aberto (financeiro) — vem de `VW_AD_REC_COMD`, hoje `[EXTERNO]` (ver `docs/RISCOS_ABERTOS.md` R14). |
| **ATIVO** | Flag `S`/`N` na tabela final `AD_NOTASITEMPROMARGEMBI`. `S` = versão vigente que o painel de BI lê. |
| **DHCARGA** | Data/hora em que a linha foi gravada na carga (`SYSDATE` no momento do fetch). |
| **SEQ_NOTASITEMPROMARGEMBI** | Sequence Oracle que gera a chave primária da tabela final. |
| **FRUTA** | Dimensão de produto: `MANGA`, `UVA`, `AVOCADO`, `LIMÃO`, "demais" — cada uma com regra de custo/margem própria na V9 (Objeto 2, Seção 5). |

## 2. Os 26 objetos documentados, em uma frase

| # | Objeto | Tipo | Em uma frase |
|---|---|---|---|
| 1 | `STP_BMC_CARGA_MRG_BI_BASE` | Procedure | O "botão de atualizar" do painel — grava o cálculo de margem numa tabela pronta pro BI ler rápido e publica a versão nova. |
| 2 | `VW_BMC_BI_BASE_ITENS_V9` | View | A "calculadora de margem": junta receita líquida e todos os custos por item vendido e devolve margem em R$ e %. |
| 3 | `VW_NOTAS_31` | View | A "planilha mestre de vendas": limpa e organiza os dados brutos do Sankhya (cliente, fruta, quantidades líquidas, fretes, rateios) antes do cálculo de margem. |
| 4 | `FU_BMC_GETPROVFORN` | Function | Decide quanto provisionar do resultado de uma venda para ajustes futuros com o fornecedor. |
| 5 | `FU_BMC_GETROYALTIES` | Function | Calcula o royalty a pagar ao dono da patente da variedade. |
| 6 | `FU_BMC_GETCOMVENDA` | Function | Calcula a comissão de venda (comercial ou de terceiros) de um item. |
| 7 | `FU_BMC_GETPERCCOMVENDA` | Function | Irmã da anterior: devolve só a alíquota (%) de comissão, não o valor. |
| 8 | `FU_BMC_GETCUSTOPREVISTO` | Function | Busca um custo combinado manualmente (override fora do fluxo automático). |
| 9 | `FU_ARG_TXADM_CUSTO_GER` | Function | Busca a taxa administrativa a aplicar sobre o custo geral de um lote. |
| 10 | `FUN_ARG_VLRETIQSRV` | Function | Soma o custo da etiqueta de um pallet (material + serviço), pelo preço vigente na data da paletização. |
| 11 | `FUN_ARG_VLRETIQ` | Function | Calcula só o valor de material da etiqueta de um pallet. |
| 12 | `FU_BMC_PRECO_CUSTO_GER` | Function | Busca o preço de custo unitário gerencial de um lote — irmã de `FU_ARG_TXADM_CUSTO_GER`, mesma config. |
| 13 | `VW_BMC_BI_CUSTOS_PROD_OTM` | View | A ficha de custo por pallet, de três formas (preço médio, por calibre, ou preço de entrada da MP). |
| 14 | `VW_BMC_BI_PERCA_PACK` | View | Lista lançamentos de perda de embalagem que entram como custo extra da manga. |
| 15 | `VW_BMC_FRETE_MARITIMO` | View | Calcula o custo de frete marítimo por item, ratando faturas entre projetos quando necessário. |
| 16 | `VW_BMC_DESPESAS_PORTUARIAS` | View | Mesma lógica de rateio do frete marítimo, para despesas de porto. |
| 17 | `VW_BMC_BI_PROV_FORNECEDORES` | View | Provisão de fornecedor já lançada na contabilidade (diferente da calculada por `FU_BMC_GETPROVFORN`). |
| 18 | `VW_BMC_GET_QTD_DEV_VENDA` | View | Descobre quanto de uma venda foi devolvido, ligando nota original × nota de devolução. |
| 19 | `VW_BMC_GET_QTD_DEV_VENDA_FOR` | View | Mesma devolução líquida, quebrada por fornecedor. |
| 20 | `VW_BMC_GET_QTD_DEV_VENDA2` | View | Mesma devolução líquida, quebrada por romaneio (lote de entrada). |
| 21 | `VW_ARG_DEB_CRE_ITE` | View | Distribui débito/crédito entre itens de uma nota, por controle de lote ou por produto/calibre. |
| 22 | `VW_ARG_CRE_DEB` | View | Monta a "ficha financeira" da nota: pago, vínculo financeiro, logística, semana de packing. |
| 23 | `VW_DESCFIN` | View | Divide o desconto financeiro da nota entre os itens, proporcional ao valor de cada um. |
| 24 | `VW_PERCPROC_NF_V4` | View | Calcula que fatia (%) cada nota representa de um processo/embarque consolidado. |
| 25 | `VW_TGFCAB_ITE` | View | Nota + item combinados, com projeto e centro de custo já resolvidos — base para as views de rateio. |
| 26 | `VW_TGFPARC_TGFEMP` | View | Identifica quais parceiros cadastrados são, na verdade, empresas do próprio grupo econômico. |

## 3. Dicionário de dados — colunas finais do painel (`VW_BMC_BI_BASE_ITENS_V9`)

Grupos de colunas que efetivamente chegam a `AD_NOTASITEMPROMARGEMBI` e, na cadeia atual, ao Looker Studio via Pentaho. Fonte: `docs/STACK_MARGEM_BI.md`, Objeto 2, Seção 4. Descrição completa de cada fórmula está na Seção 6 do mesmo objeto.

| Grupo | Colunas | Significado |
|---|---|---|
| Dimensões temporais | `REGRA`, `SEMANA`, `ANO`, `MES`, `DATA` | Período de referência do item. |
| Produto | `FRUTA`, `VARIEDADE`, `VARIEDADEMP`, `CODVARIEDADE` | Dimensão de produto/variedade. |
| Rastreabilidade | `NUNOTA`, `NF`, `CONTROLE`, `NROPALLET`, `ROMANEIO`, `LOTEARGO` | Chaves de rastreio do item/pallet. |
| Cliente/produtor | `CODPARC`, `NOME_CLIENTE`, `CODPRODUTOR`, `NOMEPRODUTOR` | Quem vendeu/comprou. |
| Comercial/exportação | `MOEDA`, `VLR_COTACAO`, `INCONTERMS`, `PAIS` | Moeda, câmbio, termo de comércio. |
| Receita | `RECEITA_BRUTA_MOE`, `PRECO_VENDA_MOEDA`, `VLR_RECEITA_BRUTA_TOTAL`, `VLR_RECEITA_LIQ1` | Receita bruta e líquida (já com frete e deduções). |
| Deduções de receita | `DESCONTO_COMERCIAL`, `DESCONTO_CONTRATUAL`, `DEVOLUCAO_REALOCACAO`, `DEVOLUCAO_PERDA`, `VLR_OUTRAS_DEV` | O que é abatido da receita bruta. |
| Custo | `CUSTO_MP`, `CUSTOMEDIO`, `CUSTO_MP_CAIXA`, `CUSTO_EMBALAGEM`, `FRETE_*`, `DESP_PORTUARIAS`, `SEGURO_CRED`, `PERDA_PACK`, `CUSTOS_SERVICOS`, `CUSTO_OPERACAO` | Todos os componentes de custo somados na margem. |
| Royalties/comissão/provisão | `VLR_ROYALTIES`, `VLR_COM_VENDA_COM`, `VLR_COM_VENDA_TERC`, `PROVISAO_FORNECEDORES`, `VLR_PROV_FORN` | Componentes de custo "de terceiro". |
| Margem | `CUSTO_CALCULADO`, `CUSTOTOTALGER`, `CUSTOTOTALGERC`, `VLR_MARGEM`, `PERC_MARGEM`, `MARGEMGER`, `PERCMARGEMGER` | O resultado final — `MARGEMGER`/`PERCMARGEMGER` são os que valem (camada externa, ver `docs/RISCOS_ABERTOS.md` R18). |
| Custo unitário | `TXADM_CUSTO_GER`, `CUSTOUNITARIOGER` | Taxa administrativa e custo unitário gerencial. |
| Logística/comercial | `STATUS_COMERCIAL`, `ETD/ETA/ETDR/ETAR`, `VESSEL`, `BOOKING`, `LINER`, `PORTO_*`, `AD_EX_CONTAINER` | Rastreio de embarque. |
| Financeiro | `OPEN_AMOUNT`, `CREDIT_MOE`, `DEBIT_MOE` | Valor em aberto e crédito/débito em moeda. |

---

Última milha não coberta por este dicionário: o pipeline Pentaho (Oracle → PostgreSQL) e o Looker Studio em si não têm documentação própria no repositório — não é possível hoje confirmar, só a partir daqui, se algum campo do painel é resultado de um cálculo adicional feito dentro do Looker Studio (campo calculado) em vez de vir 1:1 de uma destas colunas.
