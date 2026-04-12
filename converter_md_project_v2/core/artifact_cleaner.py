"""Limpador de artefatos pós-conversão.

Remove padrões espúrios deixados pelo pipeline de extração e otimização:
- Blocos de "Resumo: ... Palavras-chave: ..." gerados pelo rag_optimizer
- Cabeçalhos/rodapés de página residuais (CS – CIVIL I 2025.2 | 42)
- Linhas com apenas número de página
- Blocos `*Resumo:*` órfãos no corpo

Aplicado como passo final antes da gravação do .md.
"""

import logging
import re

logger = logging.getLogger(__name__)


# ============================================================
# Padrões de metadados espúrios
# ============================================================

# Bloco *Resumo: ... Palavras-chave: ...* gerado pelo rag_optimizer
_RESUMO_PALAVRASCHAVE_RE = re.compile(
    r'\*Resumo[:.]?\s.*?Palavras[-\s]chave[:.]?\s.*?\*',
    re.IGNORECASE | re.DOTALL,
)

# Bloco *Resumo: ...* sem palavras-chave (versão curta)
_RESUMO_SOLO_RE = re.compile(
    r'^\s*\*Resumo[:.]?\s.*?\*\s*$',
    re.IGNORECASE | re.MULTILINE,
)

# ============================================================
# Padrões de cabeçalho/rodapé de página residuais
# ============================================================

# Padrões comuns de header/footer de cadernos didáticos jurídicos:
# "CS – CIVIL I 2025.2 | 42"
# "| CS – CIVIL I 2025.2 |"
# "| CS – CIVIL I 2025.2 | 7 |"
_HEADER_FOOTER_PATTERNS = [
    # CS – DISCIPLINA XX YYYY.S | NN
    re.compile(
        r'^\s*\|?\s*CS\s*[–\-—]\s*[A-ZÀ-Ú][A-ZÀ-Ú\s]+\s+[IVX]+\s+\d{4}\.\d\s*\|?\s*\d*\s*\|?\s*$',
        re.MULTILINE,
    ),
    # Variação simplificada: SIGLA - DISCIPLINA YYYY
    re.compile(
        r'^\s*\|\s*[A-Z]{2,4}\s*[–\-—]\s*[A-ZÀ-Ú][A-ZÀ-Ú\s]+\d{4}\.\d\s*\|.*\|\s*$',
        re.MULTILINE,
    ),
    # Linha com apenas "Página N" ou "Pág. N"
    re.compile(
        r'^\s*P[áa]g(?:ina|\.)\s*\d+\s*$',
        re.IGNORECASE | re.MULTILINE,
    ),
    # Linha "— N —" ou "- N -" (número de página com travessões)
    re.compile(
        r'^\s*[-–—]\s*\d+\s*[-–—]\s*$',
        re.MULTILINE,
    ),
]

# Linha contendo apenas um número (página)
_PAGE_NUMBER_ONLY_RE = re.compile(
    r'^\s*\d{1,4}\s*$',
    re.MULTILINE,
)


def remove_spurious_metadata(text: str) -> int:
    """Remove blocos `*Resumo: ... Palavras-chave: ...*` do corpo.

    Esses blocos são gerados pelo rag_optimizer.generate_section_summaries
    e poluem o texto quando o conteúdo deveria fluir como prosa.

    Returns: número de blocos removidos.
    """
    count = 0
    matches = _RESUMO_PALAVRASCHAVE_RE.findall(text)
    count += len(matches)
    text_out = _RESUMO_PALAVRASCHAVE_RE.sub('', text)

    solo_matches = _RESUMO_SOLO_RE.findall(text_out)
    count += len(solo_matches)
    text_out = _RESUMO_SOLO_RE.sub('', text_out)

    if count > 0:
        logger.info("artifact_cleaner: removidos %d blocos *Resumo:*", count)
    return count, text_out


def remove_layout_artifacts(text: str) -> tuple[int, str]:
    """Remove cabeçalhos/rodapés de página residuais e números de página soltos.

    Cobre padrões comuns de cadernos jurídicos como:
    - "CS – CIVIL I 2025.2 | 42"
    - "| CS – CIVIL I 2025.2 |"
    - "Página 7"
    - "— 42 —"
    - Linhas isoladas contendo apenas um número (entre parágrafos)

    Returns: (count_removed, cleaned_text)
    """
    count = 0
    for pat in _HEADER_FOOTER_PATTERNS:
        matches = pat.findall(text)
        count += len(matches)
        text = pat.sub('', text)

    # Números de página soltos: somente quando isolados (linha em branco antes/depois)
    lines = text.split('\n')
    cleaned_lines = []
    for i, line in enumerate(lines):
        if _PAGE_NUMBER_ONLY_RE.match(line):
            # Verificar se está cercado por linhas em branco (provável número de página)
            prev_blank = i == 0 or not lines[i - 1].strip()
            next_blank = i == len(lines) - 1 or not lines[i + 1].strip()
            if prev_blank and next_blank:
                count += 1
                continue
        cleaned_lines.append(line)
    text = '\n'.join(cleaned_lines)

    if count > 0:
        logger.info("artifact_cleaner: removidos %d artefatos de layout", count)
    return count, text


# Padrões indicativos de ficha catalográfica
_CATALOG_INDICATORS = [
    re.compile(r'ISBN\s+[\d\-]+', re.IGNORECASE),
    re.compile(r'CDD\s+\d', re.IGNORECASE),
    re.compile(r'CDU\s+\d', re.IGNORECASE),
    re.compile(r'Dados\s+Internacionais\s+de\s+Cataloga', re.IGNORECASE),
    re.compile(r'Ficha\s+[Cc]atalogr[áa]fica'),
    re.compile(r'Catalogação\s+na\s+(?:fonte|publicação)', re.IGNORECASE),
]


def strip_catalog_block(text: str) -> tuple[int, str]:
    """Detecta e remove blocos de ficha catalográfica.

    Identifica região com ISBN, CDD/CDU, "Dados Internacionais de
    Catalogação" e remove o bloco inteiro (geralmente nas primeiras
    páginas de livros).

    Returns: (count_removed, cleaned_text)
    """
    lines = text.split('\n')
    best_start = -1
    best_end = -1
    best_count = 0

    for i, line in enumerate(lines):
        indicators = sum(
            1 for pat in _CATALOG_INDICATORS if pat.search(line)
        )
        if indicators > 0 and best_start == -1:
            best_start = max(0, i - 3)
        if indicators > 0:
            best_end = i + 1
            best_count += indicators

    if best_count >= 2 and best_start >= 0:
        # Extend end to include a few more lines (equipe editorial etc.)
        extend_end = min(best_end + 5, len(lines))
        while extend_end < len(lines) and lines[extend_end].strip():
            extend_end += 1
        removed = lines[best_start:extend_end]
        result = lines[:best_start] + lines[extend_end:]
        logger.info(
            "strip_catalog_block: removidas %d linhas de ficha catalográfica",
            len(removed),
        )
        return 1, '\n'.join(result)
    return 0, text


def clean_artifacts(text: str) -> str:
    """Pipeline completo de limpeza de artefatos.

    Aplica todas as remoções e retorna texto limpo.
    """
    _, text = remove_spurious_metadata(text)
    _, text = remove_layout_artifacts(text)
    _, text = strip_catalog_block(text)

    # Normalizar excesso de linhas em branco resultante das remoções
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    return text
