---
name: trazer-documentar-objeto
description: This skill should be used when the user asks to "bring" (trazer), "search", "fetch", or "copy" a Sankhya object (function, view, procedure) from the DBExplorer / Sankhya Om into this repository, or to document an object already added to `sql/`. Covers the full flow from locating the object in the browser to writing its 13-section documentation and updating cross-references.
---

# Trazer e documentar um objeto Sankhya

Fluxo passo a passo pra trazer um objeto (function/view/procedure) do Sankhya (via DBExplorer, módulo `Sankhya Om`) pra este repositório e documentá-lo por completo. Baseado no processo real seguido em 07/07/2026 para 9 functions e 5 views da lista de prioridade — inclusive os erros cometidos naquela rodada (registrados abaixo como avisos).

## 1. Confirmar o que falta

Antes de buscar qualquer coisa, abrir `docs/STACK_MARGEM_BI.md`, seção final ("Lista de dependências para você trazer"), e confirmar contra o `sql/` real (`ls sql/procedures sql/views sql/functions`) o que já foi trazido — a lista da doc pode estar desatualizada se alguém trouxe algo em paralelo. Não confiar cegamente na doc; verificar o filesystem.

## 2. Localizar o objeto no DBExplorer

Com o navegador já aberto na URL do Sankhya Om (`.../mge/system.jsp#app/...DbExplorer`):

1. No dropdown à esquerda ("Tabelas"), trocar para a categoria certa: **Views**, **Procedures** ou **Functions**.
2. Limpar o campo de filtro por completo antes de digitar o próximo nome (`triple_click` no campo, depois `type`) — digitar em cima de texto anterior sem limpar gera um filtro concatenado corrompido (ex.: `V_BMC_FRETEFU_BMC_PRECO...`) que não acha nada.
3. **Atenção a nomes parecidos**: o Sankhya pode ter múltiplas variações do mesmo prefixo (ex.: `FU_BMC_PRECO_CUSTO_GER`, `FU_BMC_PRECO_CUSTO_GERC`, `FU_BMC_PRECO_CUSTO_GER_O`). Conferir que o item clicado é o nome **exato** pedido, não uma variação.
4. Clicar no resultado exato.

## 3. Extrair o corpo real

Para **functions**: o corpo (`CREATE OR REPLACE FUNCTION ...`) já aparece direto na aba, geralmente cabe numa tela — dá pra transcrever do screenshot se for curto.

Para **views**: depois de abrir, o painel mostra só a grade de colunas (aba "Colunas"). É preciso:
1. Rolar a página pra baixo uma vez pra revelar a barra de ferramentas (Executar/Consulta/Salvar/Carregar) e as sub-abas "Colunas | SQL".
2. Clicar na aba "SQL".

Em ambos os casos, se o texto for longo, extrair via `javascript_tool` em vez de screenshot (mais confiável e sem limite de linhas visíveis):

```js
(() => {
  const f = document.querySelectorAll('iframe')[2]; // iframe com o ace_editor
  const win = f.contentWindow;
  const doc = f.contentDocument;
  const aceNodes = Array.from(doc.querySelectorAll('.ace_editor'));
  const visible = aceNodes.find(n => { const r = n.getBoundingClientRect(); return r.width>0 && r.height>0; });
  const value = win.ace.edit(visible).getValue();
  window.__sqlChunks = [];
  for (let i = 0; i < value.length; i += 900) window.__sqlChunks.push(value.slice(i, i+900));
  return `chunks=${window.__sqlChunks.length} totalLen=${value.length}`;
})()
```

Depois, ler `window.__sqlChunks[0]`, `[1]`, `[2]`... em chamadas separadas (chunks de ~900 caracteres evitam truncamento e o falso-positivo `[BLOCKED: Cookie/query string data]` que pode disparar em textos longos com `=`/`&`). Concatenar os chunks **exatamente na ordem**, sem tentar "arrumar" a junção — o corte é só por posição de caractere, então a concatenação bruta reconstrói o texto original perfeitamente.

**Se há mais de um objeto aberto em abas ao mesmo tempo**, `.ace_editor` pode retornar múltiplos nós — sempre pegar o que tem `getBoundingClientRect().width > 0` (o visível), não o índice `[0]` (que pode ser de uma aba anterior ainda no DOM).

## 4. Salvar no repositório

- Nome do arquivo = nome exato do objeto Oracle, maiúsculo, extensão `.txt` ou `.sql`.
- Pasta certa por tipo: `sql/procedures/`, `sql/views/` ou `sql/functions/` — **nunca** misturar (já aconteceu de uma view acabar copiada também em `sql/procedures/` por engano; sempre conferir `git status` depois de salvar pra achar duplicatas em pasta errada).
- Convenção observada: views salvam só o corpo `WITH ... SELECT` (sem o `CREATE OR REPLACE VIEW ... AS` em volta); procedures/functions salvam o `CREATE OR REPLACE ...` completo, inclusive o `/` final.
- **Antes de assumir que o conteúdo está certo**, se o arquivo já existir (trazido em paralelo por outra pessoa/sessão), ler e comparar — não sobrescrever sem checar. Já aconteceu de um arquivo conter, por erro de copy/paste, o corpo de **outro** objeto (mesmo nome de function dentro do arquivo, diferente do nome do arquivo) — se o nome dentro do `CREATE OR REPLACE` não bater com o nome do arquivo, é sinal de erro, não normalizar silenciosamente.

## 5. Documentar as 13 seções

Em `docs/STACK_MARGEM_BI.md`, adicionar `## OBJETO N — SANKHYA.NOME (Function|View|Procedure)` com as 13 partes, na ordem (ver `CONTRIBUTING.md` para a lista completa): Resumo, Fluxo de execução, Entradas, Saídas, Regras de negócio, Cálculos, Dependências, Objetos chamados, Objetos que provavelmente dependem deste objeto, Diagrama textual de dependências, Pontos críticos, Sugestões de melhoria, Resumo executivo.

- Basear cada seção só no que o SQL realmente mostra — nunca inventar regra de negócio não visível no código. Onde o nome de uma coluna/valor mágico (ex.: `CODTIPOPER=500`, `NUMLOTE=34`) não tem de-para no repositório, marcar `[VALIDAR]` e descrever o risco em vez de adivinhar o significado.
- Se dois objetos parecidos (ex.: duas views "irmãs" com a mesma estrutura) tiverem uma diferença de comportamento sutil, registrar isso explicitamente como `[VALIDAR]` — não assumir que a diferença é proposital nem que é bug.

## 6. Atualizar TODAS as referências cruzadas (não só a mais óbvia)

Isso é fácil de esquecer: o objeto novo pode ser citado como `[EXTERNO]` em **mais de um lugar** do documento (ex.: a tabela de Dependências de mais de um Objeto, o "Objetos chamados", o diagrama textual, a lista consolidada no topo do arquivo, e a "Lista de dependências para trazer" no fim). Antes de considerar a documentação concluída:

```
grep -n "NOME_DO_OBJETO" docs/STACK_MARGEM_BI.md
```

E revisar cada ocorrência — trocar `✖ [EXTERNO]` por `✔ Sim (Objeto N)` em **todas** elas, não só na primeira que aparecer. (Na rodada de 07/07/2026, uma ocorrência em outro objeto ficou esquecida numa primeira passada e só foi pega numa revisão explícita depois.)

Também atualizar:
- A lista "Objetos documentados" no topo do arquivo.
- A seção final ("Lista de dependências para trazer") — remover o objeto da lista de pendências.

## 7. Registrar no CHANGELOG

Em `CHANGELOG.md`, nova entrada datada distinguindo `✅ Confirmado` (o que foi de fato trazido/documentado) de `⚠️ Pendência` (o que ainda falta — incluindo qualquer `[VALIDAR]` novo descoberto no processo, como uma dependência nova identificada ou uma inconsistência de nome entre objetos).

## 8. Nunca commitar sozinho

Ao final, dar o bloco de comandos `git add`/`commit`/`push` pro usuário rodar — nunca executar `git commit`, `git push` ou até `git config` (nem leitura) diretamente. Ver `CONTRIBUTING.md`, seção "Ownership de commit e git".
