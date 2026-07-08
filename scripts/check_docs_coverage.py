#!/usr/bin/env python3
"""
Verifica a regra obrigatoria de documentacao (ver CONTRIBUTING.md):
todo objeto em sql/procedures|views|functions/ precisa ter uma secao
"## OBJETO N -- NOME" em docs/STACK_MARGEM_BI.md ou
docs/REVISAO_TECNICA_STACK_MARGEM_BI.md.

Uso: python3 scripts/check_docs_coverage.py
Saida: lista de objetos sem secao correspondente; exit code 1 se houver algum.
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SQL_DIRS = ["sql/procedures", "sql/views", "sql/functions"]
DOC_FILES = [
    "docs/STACK_MARGEM_BI.md",
    "docs/REVISAO_TECNICA_STACK_MARGEM_BI.md",
]

# Aceita "## OBJETO 3 -- SANKHYA.VW_NOTAS_31 (View)" e também
# "## OBJETO 1 -- VW_NOTAS_31" (formato usado na REVISAO_TECNICA), com
# hífen comum ou em-dash antes do nome.
HEADER_RE_TEMPLATE = r"^##\s*OBJETO\s+\d+\s*[-—]\s*.*\b{name}\b.*$"


def sql_object_names() -> list[str]:
    names = []
    for rel in SQL_DIRS:
        for path in sorted((REPO_ROOT / rel).glob("*")):
            if path.name.upper() == "README.MD":
                continue
            if path.suffix.lower() not in (".sql", ".txt"):
                continue
            names.append(path.stem.upper())
    return names


def load_docs_text() -> str:
    chunks = []
    for rel in DOC_FILES:
        path = REPO_ROOT / rel
        if path.exists():
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def main() -> int:
    docs_text = load_docs_text()
    missing = []
    for name in sql_object_names():
        pattern = re.compile(
            HEADER_RE_TEMPLATE.format(name=re.escape(name)), re.MULTILINE
        )
        if not pattern.search(docs_text):
            missing.append(name)

    total = len(sql_object_names())
    if missing:
        print(f"[FALHA] {len(missing)}/{total} objeto(s) em sql/ sem secao "
              f"'## OBJETO N -- NOME' em docs/STACK_MARGEM_BI.md ou "
              f"docs/REVISAO_TECNICA_STACK_MARGEM_BI.md:\n")
        for name in missing:
            print(f"  - {name}")
        print("\nVer CONTRIBUTING.md, 'Regra obrigatoria de documentacao'.")
        return 1

    print(f"[OK] {total}/{total} objetos em sql/ tem secao correspondente em docs/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
