# 0003 — Remover CLAUDE.md e mover skills/ para a raiz do repositório

## Status

Aceito.

## Contexto

O repositório usava `CLAUDE.md` como arquivo único de instruções de projeto (contexto, convenções, regras) e `.claude/skills/` para checklists/fluxos de trabalho. Esses são nomes/locais específicos da convenção do Claude Code: `CLAUDE.md` é carregado automaticamente ao abrir a pasta, e `.claude/skills/<nome>/SKILL.md` é descoberto automaticamente como skill invocável.

A decisão do time foi adotar um conjunto de documentação no padrão comum de repositórios ("big tech"): `README.md`, `ARCHITECTURE.md`, `CONTRIBUTING.md`, `CHANGELOG.md` e `docs/adr/` — visível e legível por qualquer pessoa ou ferramenta, não amarrado a uma convenção de uma ferramenta de IA específica.

## Decisão

- Redistribuir o conteúdo de `CLAUDE.md` entre `README.md` (visão geral), `ARCHITECTURE.md` (stack técnica, domínio, pontos críticos), `CONTRIBUTING.md` (regra de ouro, tags, convenção de commit, regra de documentação) e `CHANGELOG.md` (log de progresso, antes dentro de `docs/REVISAO_TECNICA_STACK_MARGEM_BI.md`). `CLAUDE.md` foi removido.
- Mover `.claude/skills/bi-impact-check/` para `skills/bi-impact-check/` na raiz, e criar o novo skill `skills/trazer-documentar-objeto/` no mesmo local.
- Não usar link/junction simbólico do Windows para manter `.claude/skills` apontando pra `skills/` (avaliado e descartado — não sobrevive a um `git clone` em outra máquina do time, tornaria o repositório não-portável).

## Consequências

- **Positivo:** documentação e checklists ficam visíveis, versionados e num padrão reconhecível por qualquer pessoa do time ou ferramenta, sem depender de convenção específica de um assistente de IA.
- **Trade-off aceito:** o Claude Code deixa de carregar contexto de projeto e de descobrir skills automaticamente ao abrir esta pasta. Em qualquer sessão futura, é preciso instruir explicitamente a leitura de `README.md`/`ARCHITECTURE.md`/`CONTRIBUTING.md` e dos arquivos em `skills/` — nada disso acontece sozinho mais.
- Referências cruzadas a `CLAUDE.md` espalhadas pelos demais arquivos (`docs/`, `sql/*/README.md`, `skills/`) precisaram ser atualizadas para apontar para o arquivo correto (`ARCHITECTURE.md` ou `CONTRIBUTING.md`, conforme o assunto).
