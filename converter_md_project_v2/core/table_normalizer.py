"""Normalizador de tabelas Markdown.

Resolve defeitos de extração que produzem tabelas malformadas:

1. Colunas duplicadas (merged cells expandidas erradamente)
2. Colunas inteiramente vazias
3. Tabelas de coluna única (devem virar prosa/blockquote)

Aplicado como pós-processamento sobre o texto Markdown.
"""

import logging
import re

logger = logging.getLogger(__name__)

_TABLE_LINE_RE = re.compile(r'^\s*\|.*\|\s*$')
_TABLE_SEP_RE = re.compile(r'^\s*\|?\s*[-:|\s]+\s*\|?\s*$')


def _split_row(row: str) -> list[str]:
    """Divide uma linha de tabela markdown em células."""
    s = row.strip()
    if s.startswith('|'):
        s = s[1:]
    if s.endswith('|'):
        s = s[:-1]
    return [c.strip() for c in s.split('|')]


def _join_row(cells: list[str]) -> str:
    """Reconstrói linha de tabela markdown a partir de células."""
    return '| ' + ' | '.join(cells) + ' |'


def _is_separator_row(cells: list[str]) -> bool:
    """Verifica se a linha é um separador de header (|---|---|)."""
    return all(re.match(r'^[-:]+$', c) for c in cells if c)


def _dedupe_columns(rows: list[list[str]]) -> tuple[list[list[str]], int]:
    """Remove colunas adjacentes que contêm conteúdo idêntico em todas as linhas.

    Causa: merged cells expandidos pelo extrator.
    Returns: (rows_without_dups, num_columns_removed)
    """
    if not rows or len(rows[0]) < 2:
        return rows, 0

    n_cols = max(len(r) for r in rows)
    # Padronizar tamanho das linhas
    rows = [r + [''] * (n_cols - len(r)) for r in rows]

    keep = [True] * n_cols
    removed = 0
    for col in range(1, n_cols):
        # Comparar coluna `col` com a coluna anterior visível
        prev_visible = col - 1
        while prev_visible >= 0 and not keep[prev_visible]:
            prev_visible -= 1
        if prev_visible < 0:
            continue
        identical_to_prev = True
        for r in rows:
            if r[col] != r[prev_visible]:
                identical_to_prev = False
                break
        if identical_to_prev:
            keep[col] = False
            removed += 1

    if removed == 0:
        return rows, 0

    new_rows = [[c for i, c in enumerate(r) if keep[i]] for r in rows]
    return new_rows, removed


def _remove_empty_columns(rows: list[list[str]]) -> tuple[list[list[str]], int]:
    """Remove colunas onde todas as células estão vazias.

    Returns: (rows_without_empty, num_columns_removed)
    """
    if not rows:
        return rows, 0

    n_cols = max(len(r) for r in rows)
    rows = [r + [''] * (n_cols - len(r)) for r in rows]

    keep = []
    for col in range(n_cols):
        if any(r[col].strip() for r in rows):
            keep.append(col)

    removed = n_cols - len(keep)
    if removed == 0:
        return rows, 0

    new_rows = [[r[c] for c in keep] for r in rows]
    return new_rows, removed


def _convert_single_column_to_paragraph(rows: list[list[str]]) -> str | None:
    """Se a tabela tem apenas 1 coluna, converte para texto/blockquote.

    Returns: texto convertido, ou None se não for tabela de coluna única.
    """
    if not rows or any(len(r) != 1 for r in rows):
        return None

    cells = [r[0] for r in rows if r[0].strip() and not _is_separator_row(r)]
    if not cells:
        return None

    # Se tem header (primeira linha curta) + uma única célula longa: blockquote
    if len(cells) == 1:
        return f"> {cells[0]}"

    # Múltiplas células de uma coluna → lista
    return '\n'.join(f"- {c}" for c in cells)


def _process_table(table_lines: list[str]) -> list[str]:
    """Processa um bloco de tabela e retorna as linhas normalizadas."""
    if len(table_lines) < 2:
        return table_lines

    # Parse rows
    parsed = [_split_row(ln) for ln in table_lines]

    # Identificar separator row (geralmente índice 1)
    sep_idx = -1
    for i, row in enumerate(parsed):
        if _is_separator_row(row):
            sep_idx = i
            break

    # Separar header, sep, body
    if sep_idx == 1:
        header = [parsed[0]]
        body = parsed[2:]
    else:
        header = []
        body = parsed

    all_rows = header + body
    if not all_rows:
        return table_lines

    # Aplicar deduplicação de colunas
    all_rows, dup_removed = _dedupe_columns(all_rows)
    all_rows, empty_removed = _remove_empty_columns(all_rows)

    if dup_removed or empty_removed:
        logger.info(
            "table_normalizer: %d colunas duplicadas e %d vazias removidas",
            dup_removed, empty_removed,
        )

    # Tentar converter tabela de 1 coluna para parágrafo
    single = _convert_single_column_to_paragraph(all_rows)
    if single is not None:
        logger.info("table_normalizer: tabela 1-coluna convertida para texto")
        return [single]

    # Reconstruir markdown da tabela
    if not all_rows or not all_rows[0]:
        return table_lines

    n_cols = len(all_rows[0])
    result = [_join_row(all_rows[0])]
    if header:
        result.append(_join_row(['---'] * n_cols))
        for row in all_rows[1:]:
            row = row + [''] * (n_cols - len(row))
            result.append(_join_row(row[:n_cols]))
    else:
        for row in all_rows[1:]:
            row = row + [''] * (n_cols - len(row))
            result.append(_join_row(row[:n_cols]))

    return result


def normalize_tables(text: str) -> str:
    """Detecta tabelas no texto Markdown e normaliza cada uma.

    Operações:
    - Remove colunas duplicadas (merged cells)
    - Remove colunas vazias
    - Converte tabelas 1-coluna para blockquote/lista
    """
    lines = text.split('\n')
    result = []
    i = 0
    while i < len(lines):
        if _TABLE_LINE_RE.match(lines[i]):
            # Coletar bloco de tabela
            table_block = []
            while i < len(lines) and _TABLE_LINE_RE.match(lines[i]):
                table_block.append(lines[i])
                i += 1
            normalized = _process_table(table_block)
            result.extend(normalized)
        else:
            result.append(lines[i])
            i += 1
    return '\n'.join(result)
