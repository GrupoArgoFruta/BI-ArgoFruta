# Fluxos — Stack de Margem BI

Diagramas complementares à documentação textual (`ARCHITECTURE.md`, `docs/STACK_MARGEM_BI.md`, `docs/REVISAO_TECNICA_STACK_MARGEM_BI.md`). Renderizam nativamente no GitHub (Mermaid) — não é preciso ferramenta externa.

Convenção visual usada em todos os diagramas:

- Retângulo sólido = objeto trazido e documentado no repo (`sql/` + seção em `docs/`).
- Retângulo tracejado / subgrafo "`[EXTERNO]`" = referenciado na documentação mas ainda não trazido.
- Caixa amarela com ⚠️ = achado desta rodada de revisão (não é conteúdo normativo do stack, é um ponto a validar).

Cada diagrama foi construído a partir do texto já existente em `docs/` e, nos pontos em que a doc e o `.sql` real divergiam, a partir do `.sql` em `sql/` (fonte de verdade). Onde houve divergência entre os dois, ela está marcada explicitamente — ver Diagrama 4.

## 1. Visão geral — linhagem de dados ponta a ponta (stack atual)

```mermaid
flowchart TD
    SRC[("Tabelas transacionais Sankhya<br/>TGFCAB / TGFITE / AD_TGFITECOMPL / ...")]
    N31["VW_NOTAS_31<br/>camada de coleta · 15 CTEs, ~40 joins"]
    V9["VW_BMC_BI_BASE_ITENS_V9<br/>camada de cálculo · ~130 colunas"]
    STP["STP_BMC_CARGA_MRG_BI_BASE<br/>procedure de carga"]
    TAB[("AD_NOTASITEMPROMARGEMBI<br/>ATIVO='S' = versão vigente")]
    PENTAHO["Pipeline Pentaho<br/>Oracle → PostgreSQL"]
    LOOKER["Looker Studio<br/>painel de margem"]

    SRC --> N31 --> V9 --> STP --> TAB --> PENTAHO --> LOOKER
```

Ponto cego conhecido: não há documentação do que acontece dentro do Pentaho (transformações, se alguma) nem de quais campos do Looker Studio são cálculo direto da coluna de origem vs. campo calculado dentro do próprio Looker Studio. Não coberto por nenhum diagrama abaixo — ninguém trouxe esse pedaço da cadeia para o repositório ainda.

## 2. Fluxo de execução — `STP_BMC_CARGA_MRG_BI_BASE`

```mermaid
flowchart TD
    A(["Início da carga"]) --> B["Refresh completo (METHOD='C') das 3 MVs<br/>VW_M_NFVENDAS_DEVINT, VW_M_CONTROLE_VLRMP, VW_M_CUSTOMED_SEMANA"]
    B --> C["TRUNCATE AD_NOTASITEMPROMARGEMBI<br/>TRUNCATE AD_BMCPRECOENTRADA"]
    C --> D["INSERT AD_BMCPRECOENTRADA<br/>a partir de VW_BMC_GETPRECOENTRADA + COMMIT"]
    D --> E["STP_ARG_PROCESS_AD_TGFITECOMPL() + COMMIT"]
    E --> F{"Cursor c_margem_bi sobre<br/>VW_BMC_BI_BASE_ITENS_V9<br/>BULK COLLECT LIMIT 1000"}
    F -->|"lote"| G["FORALL INSERT em AD_NOTASITEMPROMARGEMBI<br/>ATIVO='N', DHCARGA=SYSDATE"]
    G -->|"mais linhas"| F
    F -->|"cursor esgotado"| H["DELETE WHERE ATIVO='S' + COMMIT<br/>(no-op hoje — truncate já removeu)"]
    H --> I["UPDATE SET ATIVO='S' WHERE ATIVO='N' + COMMIT"]
    I --> J(["Fim — painel de BI passa a ler ATIVO='S'"])

    RISK["⚠️ Zona de risco (C → I): sem EXCEPTION WHEN OTHERS.<br/>Qualquer falha nesse intervalo aborta sem log/rollback controlado<br/>e deixa o painel SEM NENHUMA linha ATIVO='S' até a próxima carga bem-sucedida."]
    C -.-> RISK
    I -.-> RISK

    style RISK fill:#fff3cd,stroke:#c99,stroke-width:2px
```

## 3. Grafo de dependências — os 26 objetos documentados + pendências conhecidas

```mermaid
flowchart TD
    STP["STP_BMC_CARGA_MRG_BI_BASE (1)"]
    V9["VW_BMC_BI_BASE_ITENS_V9 (2)"]
    N31["VW_NOTAS_31 (3)"]

    STP --> V9
    V9 --> N31

    subgraph CUSTO["Custo / frete / portuária / provisão — Objetos 13–17"]
        OTM["VW_BMC_BI_CUSTOS_PROD_OTM (13)"]
        PACK["VW_BMC_BI_PERCA_PACK (14)"]
        FRMAR["VW_BMC_FRETE_MARITIMO (15)"]
        PORT["VW_BMC_DESPESAS_PORTUARIAS (16)"]
        PROVF["VW_BMC_BI_PROV_FORNECEDORES (17)"]
    end

    subgraph FUNC["Functions de cálculo — Objetos 4–12"]
        F4["FU_BMC_GETPROVFORN (4)"]
        F5["FU_BMC_GETROYALTIES (5)"]
        F6["FU_BMC_GETCOMVENDA (6)"]
        F7["FU_BMC_GETPERCCOMVENDA (7)"]
        F8["FU_BMC_GETCUSTOPREVISTO (8)"]
        F9["FU_ARG_TXADM_CUSTO_GER (9)"]
        F10["FUN_ARG_VLRETIQSRV (10)"]
        F11["FUN_ARG_VLRETIQ (11)"]
        F12["FU_BMC_PRECO_CUSTO_GER (12)"]
    end

    V9 --> OTM & PACK & FRMAR & PORT
    V9 --> F4 & F5 & F6 & F7 & F8 & F9 & F10 & F11 & F12

    subgraph QTDDEV["Quantidade / devolução / financeiro — Objetos 18–26"]
        Q18["VW_BMC_GET_QTD_DEV_VENDA (18)"]
        Q19["VW_BMC_GET_QTD_DEV_VENDA_FOR (19)"]
        Q20["VW_BMC_GET_QTD_DEV_VENDA2 (20)"]
        Q21["VW_ARG_DEB_CRE_ITE (21)"]
        Q22["VW_ARG_CRE_DEB (22)"]
        Q23["VW_DESCFIN (23)"]
        Q24["VW_PERCPROC_NF_V4 (24)"]
        Q25["VW_TGFCAB_ITE (25)"]
        Q26["VW_TGFPARC_TGFEMP (26)"]
    end

    N31 --> Q18 & Q19 & Q20 & PROVF & Q21 & Q22 & Q23 & Q24 & Q25 & Q26
    Q25 --> Q21
    Q26 --> Q22

    subgraph EXT["[EXTERNO] — referenciado, ainda não trazido para sql/"]
        MV1["VW_M_CUSTOMED_SEMANA"]
        MV2["VW_M_NFVENDAS_DEVINT"]
        MV3["VW_M_CONTROLE_VLRMP"]
        REC["VW_AD_REC_COMD<br/>⚠ erro consistente no DBExplorer ao abrir"]
        PROC2["STP_ARG_PROCESS_AD_TGFITECOMPL"]
        PRECOENT["VW_BMC_GETPRECOENTRADA / FU_BMC_GETPRECOENTRADA<br/>⚠ nome inconsistente entre os dois usos"]
        CUSTO4["obtemcusto4"]
    end

    STP --> MV1 & MV2 & MV3 & PROC2 & PRECOENT
    N31 --> MV1
    N31 --> REC
    OTM --> PRECOENT
    OTM --> CUSTO4
    F11 --> CUSTO4

    classDef pending stroke-dasharray: 5 5
    class MV1,MV2,MV3,REC,PROC2,PRECOENT,CUSTO4 pending
```

## 4. Grafo interno de CTEs — `VW_NOTAS_31`

Construído lendo direto `sql/views/VW_NOTAS_31.txt` (não só a prosa de `docs/STACK_MARGEM_BI.md`), porque as duas fontes divergem neste objeto — ver caixa de achado no diagrama.

```mermaid
flowchart TD
    subgraph WITHBLOCK["Bloco WITH — 15 CTEs materializadas no arquivo atual"]
        DEVITEM["DEV_ITEM<br/>devolução por item (TIPMOV='D', STATUSNOTA='L')"]
        QNUNOTA["QTDNEG_POR_NUNOTA<br/>alias QNOTA — qtd líquida por nota"]
        ITELIQ["ITE_LIQ"]
        QFOR["QTDNEG_POR_FORN — alias QFOR"]
        QCEN["QTDNEG_POR_CENCUS — alias QCEN"]
        QCAL["QTDNEG_POR_CALIBRE — alias QCAL"]
        QCTR["QTDNEG_POR_CONTROLE — alias QCTR"]
        QPRV["VLRPROVFORN_POR_CENCUS — alias QPRV"]
        QPAT["PARC_PATENTE — alias QPAT"]
        QVAR["VARIEDADE_MP — alias QVAR"]
        QNFMP["NF_ENT_MP — alias QNFMP"]
        PEDFR["PED_FRETE_VENDAS<br/>corte DATE '2025-12-18'"]
        PEDLOG["PED_DESP_LOG<br/>corte DATE '2026-06-01'"]
        ITEBASE["ITE_BASE<br/>AD_TGFITECOMPL + ROMANEIO_NUM"]
        TIPOPARC["TIPO_PARCERIA_LKP<br/>⚠ não descrita em docs/STACK_MARGEM_BI.md Objeto 3"]
    end

    MAIN["SELECT principal<br/>TGFCAB + ITE_BASE + ~40 joins"]

    DEVITEM --> QNUNOTA --> MAIN
    ITELIQ --> MAIN
    QFOR --> MAIN
    QCEN --> MAIN
    QCAL --> MAIN
    QCTR --> MAIN
    QPRV --> MAIN
    QPAT --> MAIN
    QVAR --> MAIN
    QNFMP --> MAIN
    PEDFR --> MAIN
    PEDLOG --> MAIN
    ITEBASE --> MAIN
    TIPOPARC --> MAIN
    DEVITEM --> MAIN

    MAIN --> OUT["~130 colunas de saída<br/>inclui PERCDESCCONTRATUAL, VLR_DESC_FIN_SDEV"]

    DRIFT["⚠️ [VALIDAR] ADR-0002 e CHANGELOG (05/07/2026) descrevem CTEs<br/>PDESC e DEV_NOTA alimentando PERCDESCCONTRATUAL via AD_CTRLDESCOM.<br/>Nenhuma das duas existe em sql/views/VW_NOTAS_31.txt hoje:<br/>PERCDESCCONTRATUAL ali é COALESCE(PARCLI.DESCFIN,0), direto de TGFPAR<br/>(mesma fonte de antes da rev. 3). Ver achado #2 no final deste documento."]
    OUT -.-> DRIFT

    style DRIFT fill:#fff3cd,stroke:#c99,stroke-width:2px
```

## 5. Arquitetura futura proposta (GCP — Multiedro, **não contratada**)

```mermaid
flowchart LR
    SANKHYA[("Sankhya / Oracle<br/>origem, on-premise")]
    VPN["Cloud VPN"]
    DATAFLOW["Dataflow<br/>Apache Beam / Python"]
    GCS[("Cloud Storage<br/>Data Lake")]
    BQ[("BigQuery<br/>Data Warehouse")]
    LOOKER["Looker Studio Pro"]

    SANKHYA --> VPN --> DATAFLOW --> GCS --> BQ --> LOOKER

    NOTE["⚠️ Proposta comercial de vendor terceiro, ainda NÃO contratada.<br/>Não assumir que existe até confirmação explícita.<br/>Escopo da proposta exclui governança de dados e IA.<br/>PDF fica só local — não versionado (ver .gitignore)."]
    LOOKER -.-> NOTE

    style NOTE fill:#fff3cd,stroke:#c99,stroke-width:2px
```

## 6. Fluxo de trabalho — trazer e documentar um objeto Sankhya

> ⚠️ Este fluxo reflete o conteúdo de `skills/trazer-documentar-objeto/SKILL.md` **conforme criado no commit `ce3f439`**. Esse arquivo não existe mais no working tree — foi apagado 13 minutos depois, no commit `aa50339` (ver achado #1 no final deste documento). Reconstruído aqui a partir do histórico do Git só para preservar o conteúdo visualmente; não substitui a decisão de restaurar (ou não) o arquivo original.

```mermaid
flowchart TD
    A(["Precisa trazer um objeto novo do Sankhya?"]) --> B["1. Confirmar o que falta:<br/>comparar Seção Final de STACK_MARGEM_BI.md contra sql/ real<br/>(ls sql/procedures sql/views sql/functions) — não confiar só na doc"]
    B --> C["2. Localizar no DBExplorer (Sankhya Om)<br/>trocar categoria (Views/Procedures/Functions), limpar filtro,<br/>conferir que o nome clicado é EXATO (evitar variação de prefixo)"]
    C --> D["3. Extrair o corpo real<br/>function: direto na aba · view: sub-aba SQL<br/>texto longo → javascript_tool em chunks de ~900 caracteres"]
    D --> E["4. Salvar em sql/procedures|views|functions/<br/>nome exato do objeto Oracle, maiúsculo · checar git status por duplicata em pasta errada"]
    E --> F["5. Documentar as 13 seções em docs/STACK_MARGEM_BI.md<br/>só o que o SQL mostra — nome/valor mágico sem de-para vira [VALIDAR]"]
    F --> G["6. Atualizar TODAS as referências cruzadas<br/>grep -n NOME_DO_OBJETO docs/STACK_MARGEM_BI.md — revisar CADA ocorrência,<br/>não só a primeira (lista do topo + Seção Final também)"]
    G --> H["7. Registrar entrada datada no CHANGELOG.md<br/>✅ Confirmado vs ⚠️ Pendência"]
    H --> I["8. Nunca commitar sozinho —<br/>dar o bloco git add/commit/push pro usuário rodar"]
    I --> J(["Fim"])
```

## 7. Árvore de decisão — checklist de impacto em BI

> ⚠️ Mesma observação do diagrama 6: reconstruído a partir do conteúdo de `skills/bi-impact-check/SKILL.md` no commit `ce3f439`, que também não existe mais no working tree.

```mermaid
flowchart TD
    A(["Mudança em objeto que lê/escreve na stack de margem BI"]) --> B["1. Mapear raio de impacto<br/>(STACK_MARGEM_BI.md + REVISAO_TECNICA — inclusive quem depende do objeto)"]
    B --> C{"Objeto já documentado?"}
    C -->|Não| C1["Documentar primeiro — bloqueante"] --> D
    C -->|Sim| D["2. Classificar a mudança"]
    D --> D1{"Tipo?"}
    D1 -->|"Correção funcional"| D1a["Destacar explicitamente<br/>nunca disfarçar de otimização"]
    D1 -->|"Otimização / refatoração"| D1b["Mirar resultado idêntico"]
    D1 -->|"Automação nova"| D1c["Tratar como parte da stack<br/>confirmar se o GCP já foi contratado antes de assumir infra"]
    D1a --> E
    D1b --> E
    D1c --> E{"3. Dá pra provar equivalência só pelo texto/SQL?"}
    E -->|Sim| E1["Explicar por quê"] --> F
    E -->|Não| E2["Marcar [VALIDAR] + descrever o risco concreto"] --> F
    F["4. Reconciliar contra produção (ANO/SEMANA/FRUTA)"] --> F1{"Reconciliação já rodou?"}
    F1 -->|Não| F1a["⚠️ Pendência — nunca marcar ✅ Confirmado"] --> G
    F1 -->|Sim| F1b["✅ Confirmado — registrar o resultado numérico"] --> G
    G{"5. Toca um ponto crítico conhecido?<br/>(publicação não atômica, sem EXCEPTION, etc.)"}
    G -->|Sim| G1["Sinalizar explicitamente o que muda de comportamento<br/>nunca corrigir em silêncio dentro de outra mudança"] --> H
    G -->|Não| H["6. Documentar (13 seções) + entrada no CHANGELOG"]
    H --> I["7. Dar o bloco git add/commit pro usuário — Claude nunca commita"]
    I --> J(["Concluído"])
```

---

## Achados desta rodada de revisão (não são conteúdo normativo do stack)

Dois achados concretos, encontrados conferindo o `git log` e o `.sql` real contra a documentação — reportados aqui, não corrigidos silenciosamente (mesma regra que este repositório pede para todo o resto).

### 1. `skills/` foi apagada 13 minutos depois de criada

`skills/bi-impact-check/SKILL.md` e `skills/trazer-documentar-objeto/SKILL.md` são citadas como existentes em `README.md`, `ARCHITECTURE.md`, `CONTRIBUTING.md`, `sql/*/README.md` e no `docs/adr/0003-remover-claude-md-e-mover-skills-para-raiz.md` — mas não existem em lugar nenhum do working tree. `git log --name-status -- skills` mostra que o commit `aa50339` (17:07, 07/07/2026), 13 minutos depois do commit `ce3f439` (16:54) que finalizou essas duas skills, contém só duas remoções — nada mais:

```
aa50339  skills/bi-impact-check/SKILL.md          | 65 -----
aa50339  skills/trazer-documentar-objeto/SKILL.md | 85 -----
```

Tudo indica commit acidental (mesma mensagem de commit do anterior, nenhuma outra mudança). O conteúdo não está perdido — está no histórico do Git. Comando para restaurar os dois arquivos exatamente como ficaram em `ce3f439` (rodar você mesmo, não vou executar):

```
git checkout ce3f439 -- skills/bi-impact-check/SKILL.md skills/trazer-documentar-objeto/SKILL.md
git status
git commit -m "fix: restaura skills apagadas acidentalmente no commit aa50339"
```

### 2. `VW_NOTAS_31`: documentação e SQL real divergem sobre `PERCDESCCONTRATUAL`

`ADR-0002`, a entrada de `CHANGELOG.md` de 05/07/2026 e a nota de "Revisão (rev. 3)" no topo do Objeto 3 em `docs/STACK_MARGEM_BI.md` descrevem, como já implementado e com equivalência pendente de reconciliação: novas CTEs `PDESC` (baseada em `AD_CTRLDESCOM`, via `ROW_NUMBER`/`DHALTER<=DTNEG`/`RN=1`) e `DEV_NOTA`, com `PERCDESCCONTRATUAL` passando a vir de `PDESC`.

Conferido direto em `sql/views/VW_NOTAS_31.txt`: não existe CTE `PDESC` nem `DEV_NOTA`, não existe `AD_CTRLDESCOM`, não existe `ROW_NUMBER` no arquivo inteiro. `PERCDESCCONTRATUAL` (linha 595-596) é `COALESCE(PARCLI.DESCFIN, 0)` — direto de `TGFPAR`, a mesma fonte de antes da rev. 3. `VLR_DESC_FIN_SDEV` (linha 827-829) também usa `PARCLI.DESCFIN` diretamente, não uma CTE de devolução por nota. As próprias Seções 4, 6, 7 e 10 do Objeto 3 (Saídas, Cálculos, Dependências, Diagrama) nunca foram atualizadas para citar `PDESC`/`DEV_NOTA`/`AD_CTRLDESCOM` — só a nota de topo da rev. 3 fala nisso.

`[VALIDAR]` três hipóteses possíveis, nenhuma confirmável só pelo texto:
- (a) a mudança foi aplicada no Oracle mas o `.txt` local não foi re-sincronizado depois;
- (b) a mudança nunca chegou a ser aplicada no Oracle — o ADR registra uma decisão aceita, não necessariamente deployada;
- (c) foi aplicada e depois revertida no Oracle (por exemplo, se a reconciliação pendente tiver reprovado), sem atualizar ADR/CHANGELOG.

Como `PERCDESCCONTRATUAL` "alimenta desconto → alimenta margem" (linguagem do próprio `CHANGELOG.md`), vale confirmar qual das três é verdade antes de tratar a rev. 3 como vigente em qualquer decisão.

Achado secundário, mesmo objeto: o arquivo real tem **15 CTEs** (incluindo `DEV_ITEM`, adicionada na rev. 3, e `TIPO_PARCERIA_LKP`, que não é mencionada em nenhuma seção do Objeto 3), não as "13 CTEs" que a Seção 2 ainda descreve.
