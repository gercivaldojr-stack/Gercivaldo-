"""Validador e normalizador de hierarquia de headings Markdown.

Resolve três defeitos comuns da conversão DOCX/PDF → Markdown:

1. Saltos de nível (## direto para ####)
2. Numeração duplicada (### 3.1. ### 3.1. Fonte primária)
3. Falta de linhas em branco antes/depois de cada heading

Aplicado como passo de normalização após heuristics.
"""

import logging
import re

logger = logging.getLogger(__name__)

_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+?)\s*$')


def remove_duplicate_numbering(text: str) -> tuple[int, str]:
    """Remove numeração duplicada em headings.

    Casos cobertos:
    - "### 3.1. ### 3.1. Fonte primária" → "### 3.1. Fonte primária"
    - "## 1. ## 1. Capítulo" → "## 1. Capítulo"
    """
    count = 0
    lines = text.split('\n')
    fixed = []
    # Pattern: heading marker + número + ponto + repetição do mesmo padrão
    dup_re = re.compile(
        r'^(#{1,6})\s+(\d+(?:\.\d+)*\.?)\s+\1\s+\2\s+',
    )
    # Variação: ### 3.1. ### 3.1 (sem segundo ponto)
    dup_re2 = re.compile(
        r'^(#{1,6})\s+(\d+(?:\.\d+)*\.?)\s+\1\s+(\2)',
    )

    for line in lines:
        m = dup_re.match(line)
        if m:
            new_line = re.sub(dup_re, f'{m.group(1)} {m.group(2)} ', line)
            fixed.append(new_line)
            count += 1
            continue
        m = dup_re2.match(line)
        if m:
            new_line = re.sub(
                dup_re2,
                f'{m.group(1)} {m.group(2)} ',
                line,
            )
            fixed.append(new_line)
            count += 1
            continue
        fixed.append(line)

    if count > 0:
        logger.info("heading_validator: removidas %d numerações duplicadas", count)
    return count, '\n'.join(fixed)


def fix_heading_level_jumps(text: str) -> tuple[int, str]:
    """Corrige saltos de nível em headings.

    Se um heading pula mais de 1 nível em relação ao anterior
    (ex.: ## seguido direto de ####), promove o heading filho
    para o nível imediatamente abaixo do pai.

    Não altera o primeiro heading do documento.
    """
    count = 0
    lines = text.split('\n')
    last_level = 0
    fixed = []

    for line in lines:
        m = _HEADING_RE.match(line)
        if not m:
            fixed.append(line)
            continue

        level = len(m.group(1))
        title = m.group(2)

        if last_level > 0 and level > last_level + 1:
            new_level = last_level + 1
            new_line = '#' * new_level + ' ' + title
            fixed.append(new_line)
            count += 1
            last_level = new_level
            continue

        last_level = level
        fixed.append(line)

    if count > 0:
        logger.info("heading_validator: corrigidos %d saltos de nível", count)
    return count, '\n'.join(fixed)


def ensure_heading_blank_lines(text: str) -> tuple[int, str]:
    """Garante linha em branco antes e depois de cada heading.

    Casos:
    - Texto colado: "Parágrafo X.\n## Heading" → adiciona blank antes
    - Heading colado: "## Heading\nTexto" → adiciona blank depois
    """
    count = 0
    lines = text.split('\n')
    result = []

    for i, line in enumerate(lines):
        is_heading = bool(_HEADING_RE.match(line))
        if is_heading:
            # Garantir linha em branco antes (se não for início)
            if result and result[-1].strip():
                result.append('')
                count += 1
            result.append(line)
            # Garantir linha em branco depois (se houver próxima)
            if i + 1 < len(lines) and lines[i + 1].strip():
                result.append('')
                count += 1
        else:
            result.append(line)

    if count > 0:
        logger.info("heading_validator: adicionadas %d linhas em branco", count)
    return count, '\n'.join(result)


_VERB_INDICATOR = re.compile(
    r'\b(?:é|são|foi|está|pode|deve|tem|há|não|será|'
    r'consiste|define|trata|configura|constitui|representa|'
    r'caracteriza|compreende|abrange|inclui|'
    r'prevê|dispõe|estabelece|determina|aplica|regula|'
    r'disciplina|prescreve|estipula|assegura|garante|'
    r'veda|proíbe|autoriza|permite|exige|obriga|'
    r'impõe|reconhece|admite)\b',
    re.IGNORECASE,
)


def truncate_heading_with_body(text: str, max_words: int = 15) -> str:
    """Separa headings que contêm início de parágrafo embutido.

    Se um heading tem mais de max_words palavras e contém
    verbo conjugado após o "título" (indicando início de frase),
    separa em heading + parágrafo.
    """
    lines = text.split('\n')
    result = []
    count = 0

    for line in lines:
        m = _HEADING_RE.match(line)
        if not m:
            result.append(line)
            continue

        level = m.group(1)
        content = m.group(2)
        words = content.split()

        if len(words) <= max_words:
            result.append(line)
            continue

        # Procurar ponto de corte: verbo conjugado após ~8 palavras
        cut_point = -1
        for wi in range(8, min(len(words), max_words + 5)):
            word = words[wi]
            if _VERB_INDICATOR.match(word):
                # Verificar se a palavra anterior é um substantivo (capitalized)
                if wi > 0 and words[wi - 1][0].isupper():
                    cut_point = wi
                    break
                # Ou se a frase simplesmente começa com maiúscula
                if word[0].isupper():
                    cut_point = wi
                    break

        if cut_point > 0:
            heading_text = ' '.join(words[:cut_point])
            body_text = ' '.join(words[cut_point:])
            result.append(f"{level} {heading_text}")
            result.append("")
            result.append(body_text)
            count += 1
        else:
            result.append(line)

    if count > 0:
        logger.info(
            "truncate_heading_with_body: %d headings truncados", count,
        )
    return '\n'.join(result)


def normalize_heading_hierarchy(text: str) -> str:
    """Pipeline completo de normalização de headings."""
    _, text = remove_duplicate_numbering(text)
    _, text = fix_heading_level_jumps(text)
    text = truncate_heading_with_body(text)
    _, text = ensure_heading_blank_lines(text)
    return text
