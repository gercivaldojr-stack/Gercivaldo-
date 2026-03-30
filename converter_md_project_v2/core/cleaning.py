"""
Módulo de limpeza e normalização de texto extraído.
Remove artefatos de OCR, hifenização, cabeçalhos/rodapés repetidos, ruído.
"""

import logging
import re
from collections import Counter

logger = logging.getLogger(__name__)


def clean_text(text: str, remove_headers_footers: bool = True) -> str:
    """Pipeline completo de limpeza de texto.

    Args:
        text: Texto bruto extraído.
        remove_headers_footers: Se True, tenta remover cabeçalhos e rodapés repetidos.

    Returns:
        Texto limpo e normalizado.
    """
    if not text or not text.strip():
        return ""

    text = fix_hyphenation(text)
    text = normalize_whitespace(text)
    text = remove_ocr_noise(text)

    if remove_headers_footers:
        text = remove_repeated_headers_footers(text)

    text = normalize_paragraphs(text)

    return text.strip()


def fix_hyphenation(text: str) -> str:
    """Reconstrói palavras hifenizadas em quebra de linha.

    Exemplos:
        'consti-\\ntuição' -> 'constituição'
        'funda-\\nmental' -> 'fundamental'
    """
    # Hifenização no fim de linha
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    # Hifenização com espaço antes da quebra
    text = re.sub(r"(\w)-\s{2,}(\w)", r"\1\2", text)
    return text


def normalize_whitespace(text: str) -> str:
    """Normaliza espaços e tabulações, preservando quebras de parágrafo."""
    # Substituir tabs por espaço
    text = text.replace("\t", " ")
    # Múltiplos espaços em sequência -> um espaço
    text = re.sub(r"[ ]{2,}", " ", text)
    # Remover espaços no início/fim de cada linha
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(lines)


def remove_ocr_noise(text: str) -> str:
    """Remove artefatos comuns de OCR."""
    # Caracteres isolados que são ruído (sequências de chars soltos)
    text = re.sub(r"\b[^a-zA-ZÀ-ÿ0-9\s]{3,}\b", "", text)
    # Linhas compostas apenas de caracteres especiais
    text = re.sub(r"^[^\w\s]*$", "", text, flags=re.MULTILINE)
    # Sequências longas de pontos (sumários)
    text = re.sub(r"\.{4,}", "", text)
    # Sequências longas de underscores ou hífens (separadores visuais)
    text = re.sub(r"[_]{3,}", "", text)
    text = re.sub(r"[-]{5,}", "---", text)
    return text


def remove_repeated_headers_footers(text: str) -> str:
    """Detecta e remove cabeçalhos e rodapés repetidos entre páginas.

    Heurística: linhas curtas que aparecem 3+ vezes com mesmo conteúdo
    são provavelmente cabeçalhos/rodapés.
    """
    lines = text.split("\n")
    if len(lines) < 20:
        return text

    # Padrões que NÃO devem ser removidos (headings jurídicos legítimos)
    legal_heading_patterns = [
        r"^dos?\s+fatos", r"^dos?\s+direito", r"^dos?\s+pedidos",
        r"^fundamenta", r"^preliminar", r"^do\s+mérito",
        r"^relatório", r"^dispositivo", r"^ementa", r"^voto",
        r"^capítulo", r"^seção", r"^cláusula", r"^título",
    ]

    # Contar ocorrências de linhas curtas normalizadas
    # Headers/footers são tipicamente curtos (< 60 chars)
    line_counts = Counter()
    for line in lines:
        stripped = line.strip()
        if 3 < len(stripped) < 60:
            # Normalizar números de página
            normalized = re.sub(r"\d+", "#", stripped.lower())
            line_counts[normalized] += 1

    # Linhas que aparecem 3+ vezes são candidatas a header/footer
    repeated = {pattern for pattern, count in line_counts.items() if count >= 3}

    if not repeated:
        return text

    # Filtrar: não remover padrões que são headings jurídicos legítimos
    filtered_repeated = set()
    for pattern in repeated:
        is_legal = any(re.match(lp, pattern.strip()) for lp in legal_heading_patterns)
        if not is_legal:
            filtered_repeated.add(pattern)

    if not filtered_repeated:
        return text

    logger.info("Detectados %d padrões de cabeçalho/rodapé repetidos", len(filtered_repeated))

    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        normalized = re.sub(r"\d+", "#", stripped.lower())
        if normalized not in filtered_repeated:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def normalize_paragraphs(text: str) -> str:
    """Normaliza separação de parágrafos.

    - Remove quebras de linha excessivas (> 2 em sequência)
    - Junta linhas que pertencem ao mesmo parágrafo (linhas curtas seguidas de texto)
    """
    # Remover mais de 2 quebras de linha consecutivas
    text = re.sub(r"\n{4,}", "\n\n\n", text)

    lines = text.split("\n")
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Se a linha é um heading markdown, preservar
        if line.strip().startswith("#"):
            result.append(line)
            i += 1
            continue

        # Se a linha termina sem pontuação final e a próxima começa com minúscula,
        # provavelmente é continuação do mesmo parágrafo
        if (
            i + 1 < len(lines)
            and line.strip()
            and not line.strip().endswith((".", ":", ";", "!", "?", '"""'))
            and lines[i + 1].strip()
            and lines[i + 1].strip()[0].islower()
            and not lines[i + 1].strip().startswith(("#", "-", "*", ">"))
        ):
            result.append(line.strip() + " " + lines[i + 1].strip())
            i += 2
            continue

        result.append(line)
        i += 1

    return "\n".join(result)
