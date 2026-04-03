"""
Módulo de limpeza e normalização de texto extraído.
Remove artefatos de OCR, hifenização, cabeçalhos/rodapés repetidos,
ruído, boilerplate de e-reader e glyphs corrompidos.
"""

import logging
import re
import unicodedata
from collections import Counter

logger = logging.getLogger(__name__)

# Palavras-chave de instruções de e-reader/epub a remover no início do documento
EREADER_KEYWORDS = [
    "escolher fonte",
    "alterar layout",
    "luminosidade",
    "fazer buscas",
    "anotar trechos",
    "menu",
    "marca-texto",
    "marcador",
    "bookmark",
    "aumentar fonte",
    "diminuir fonte",
    "tamanho da fonte",
    "modo noturno",
    "modo de leitura",
    "configurações de leitura",
    "opções de visualização",
    "deslize para",
    "toque para",
    "toque na tela",
    "arraste",
    "pinça para zoom",
    "sumário interativo",
    "índice interativo",
    "navegação",
    "barra de progresso",
    "epub",
    "e-reader",
    "e-book",
    "ebook",
    "kindle",
    "kobo",
    "google play livros",
    "apple books",
    "this ebook",
    "digital rights",
    "drm",
    "choose font",
    "adjust layout",
    "brightness",
    "search text",
    "annotate",
    "highlight",
]


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

    # Normalizar Unicode NFC (chars decompostos de DOCX)
    text = unicodedata.normalize("NFC", text)

    text = fix_hyphenation(text)
    text = normalize_whitespace(text)
    text = remove_corrupted_glyphs(text)
    text = remove_ocr_noise(text)
    text = remove_ereader_boilerplate(text)
    if remove_headers_footers:
        text = remove_repeated_headers_footers(text)
    text = remove_residual_pagination(text)
    text = reconnect_cnj_numbers(text)
    text = reconstruct_pdf_headings(text)
    text = rejoin_broken_paragraphs(text)
    text = separate_enumerations(text)
    text = normalize_legal_citations(text)
    text = normalize_paragraphs(text)

    return text.strip()


def reconstruct_pdf_headings(text: str) -> str:
    """Reconstrói headings de seções numeradas quebrados em múltiplas linhas pelo PDF.

    Problema: Quando um heading como
        '8. DA RESERVA INTEGRAL DE BENS (Art. 628, § 2°, DO CPC) E DO'
        'PROSSEGUIMENTO DO ARROLAMENTO'
    é extraído de um PDF, ele aparece em duas (ou mais) linhas porque o
    extrator preserva as quebras visuais de linha da página.

    Solução: Detecta linhas que começam com padrão de seção numerada
    (\d+\.\s+MAIÚSCULAS) e, se a próxima linha é curta e em MAIÚSCULAS
    (continuação do heading), junta as duas.

    Também trata headings nomeados em MAIÚSCULAS sem número que foram quebrados.
    """
    # Normalizar Unicode NFC
    text = unicodedata.normalize("NFC", text)

    # Normalizar caracteres especiais (NBSP, degree sign, zero-width space)
    text = text.replace('\xa0', ' ').replace('\u200b', '')

    lines = text.split("\n")
    if len(lines) < 2:
        return text

    # Padrão: linha começando com número + ponto + texto majoritariamente MAIÚSCULAS
    numbered_heading_re = re.compile(
        r"^(\d+)\.\s+([A-ZÁÉÍÓÚÀÂÊÔÃÕÇ][A-ZÁÉÍÓÚÀÂÊÔÃÕÇa-záéíóúàâêôãõç\s,§°º().\-:/\d]+)$"
    )

    # Padrão: linha toda em MAIÚSCULAS (possível continuação de heading)
    uppercase_line_re = re.compile(
        r"^[A-ZÁÉÍÓÚÀÂÊÔÃÕÇ][A-ZÁÉÍÓÚÀÂÊÔÃÕÇa-záéíóúàâêôãõç\s,§°º().\-:/\d]*$"
    )

    # Preposições/conjunções que indicam heading incompleto no final da linha
    trailing_connector_re = re.compile(
        r"\b(?:DE|DA|DO|DAS|DOS|NA|NO|NAS|NOS|EM|COM|E|OU|PARA|POR|"
        r"AO|AOS|À|ÀS|ANTE|PERANTE|SOBRE|SOB|ENTRE|ESTE|ESTA|DESTE|DESTA)\s*$"
    )

    # Padrão de heading nomeado sem número: "DOS FATOS", "DO MÉRITO", etc.
    named_heading_re = re.compile(
        r"^(D[AO]S?|PRELIMINAR|FUNDAMENTAÇÃO|RELATÓRIO|DISPOSITIVO|EMENTA|VOTO)\s+[A-ZÁÉÍÓÚÀÂÊÔÃÕÇ]"
    )

    result = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Pular linhas vazias ou curtas
        if not stripped or len(stripped) < 3:
            result.append(line)
            i += 1
            continue

        # Caso 1: Seção numerada (ex: "8. DA RESERVA INTEGRAL DE BENS...")
        if numbered_heading_re.match(stripped):
            merged = stripped
            while i + 1 < len(lines):
                next_stripped = lines[i + 1].strip()
                if not next_stripped:
                    break
                is_next_upper = (
                    uppercase_line_re.match(next_stripped) and len(next_stripped) < 80
                )
                ends_with_connector = bool(trailing_connector_re.search(merged))
                if is_next_upper and (ends_with_connector or len(next_stripped) < 40):
                    merged = merged + " " + next_stripped
                    i += 1
                    logger.debug(
                        "Heading reconstruído: juntou '%s' com '%s'",
                        stripped[:50],
                        next_stripped[:50],
                    )
                else:
                    break
            result.append(merged)
            i += 1
            continue

        # Caso 2: Heading nomeado em MAIÚSCULAS sem número
        if (
            named_heading_re.match(stripped)
            and stripped.isupper()
            and len(stripped) < 100
        ):
            merged = stripped
            while i + 1 < len(lines):
                next_stripped = lines[i + 1].strip()
                if not next_stripped:
                    break
                is_next_upper = (
                    uppercase_line_re.match(next_stripped) and len(next_stripped) < 60
                )
                ends_with_connector = bool(trailing_connector_re.search(merged))
                if is_next_upper and (ends_with_connector or len(next_stripped) < 30):
                    merged = merged + " " + next_stripped
                    i += 1
                else:
                    break
            result.append(merged)
            i += 1
            continue

        # Caso 3: Linha em MAIÚSCULAS curta que termina com conector
        if (
            stripped.isupper()
            and len(stripped) < 100
            and trailing_connector_re.search(stripped)
        ):
            merged = stripped
            while i + 1 < len(lines):
                next_stripped = lines[i + 1].strip()
                if not next_stripped:
                    break
                is_next_upper = (
                    uppercase_line_re.match(next_stripped) and len(next_stripped) < 80
                )
                if is_next_upper:
                    merged = merged + " " + next_stripped
                    i += 1
                else:
                    break
            result.append(merged)
            i += 1
            continue

        result.append(line)
        i += 1

    return "\n".join(result)


def reconnect_cnj_numbers(text: str) -> str:
    """Reconecta números CNJ e siglas de processos partidos por quebra de linha.

    Siglas reconhecidas: HC, RHC, REsp, AgRg, ARE, AREsp, ADI, ADPF, RE, RMS.
    Padrão: SIGLA\\n1234567-89.2024 → SIGLA 1234567-89.2024 (em uma linha).
    """
    text = re.sub(
        r"\b(HC|RHC|REsp|AgRg|ARE|AREsp|ADI|ADPF|RE|RMS)\s*\n\s*(\d{7}-\d{2}\.\d{4})",
        r"\1 \2",
        text,
    )
    return text


def remove_residual_pagination(text: str) -> str:
    """Remove paginação residual do texto.

    Remove padrões de paginação:
    - "Página NN", "Pág. NN", "— NN —"
    - Números isolados (^\\d+$) somente nas primeiras/últimas 3 linhas.
    """
    lines = text.split("\n")
    cleaned = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.match(r"^P[áa]gina\s+\d+\s*$", stripped, re.IGNORECASE):
            continue
        if re.match(r"^P[áa]g\.\s*\d+\s*$", stripped, re.IGNORECASE):
            continue
        if re.match(r"^[-–—]\s*\d+\s*[-–—]\s*$", stripped):
            continue
        if re.match(r"^\d+$", stripped):
            if i < 3 or i >= len(lines) - 3:
                continue
        cleaned.append(line)
    return "\n".join(cleaned)


def fix_hyphenation(text: str) -> str:
    """Reconstrói palavras hifenizadas em quebra de linha."""
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    text = re.sub(r"(\w)-\s{2,}(\w)", r"\1\2", text)
    return text


def normalize_whitespace(text: str) -> str:
    """Normaliza espaços e tabulações, preservando quebras de parágrafo."""
    text = text.replace("\t", " ")
    text = re.sub(r"[ ]{2,}", " ", text)
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(lines)


def remove_ocr_noise(text: str) -> str:
    """Remove artefatos comuns de OCR."""
    text = re.sub(r"\b[^a-zA-ZÀ-ÿ0-9\s]{3,}\b", "", text)
    text = re.sub(r"^[^\w\s]*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\.{4,}", "", text)
    text = re.sub(r"[_]{3,}", "", text)
    text = re.sub(r"[-]{5,}", "---", text)
    return text


def remove_repeated_headers_footers(
    text: str,
    preserve_first: bool = True,
) -> str:
    """Detecta e remove cabeçalhos e rodapés repetidos entre páginas.

    Heurística: linhas curtas que aparecem 3+ vezes com mesmo conteúdo
    são provavelmente cabeçalhos/rodapés.

    Args:
        text: Texto com possíveis headers/footers repetidos.
        preserve_first: Se True, mantém a primeira ocorrência de cada padrão.
    """
    lines = text.split("\n")
    if len(lines) < 20:
        return text

    legal_heading_patterns = [
        r"^dos?\s+fatos",
        r"^dos?\s+direito",
        r"^dos?\s+pedidos",
        r"^fundamenta",
        r"^preliminar",
        r"^do\s+mérito",
        r"^relatório",
        r"^dispositivo",
        r"^ementa",
        r"^voto",
        r"^capítulo",
        r"^seção",
        r"^cláusula",
        r"^título",
    ]

    line_counts = Counter()
    for line in lines:
        stripped = line.strip()
        if 3 < len(stripped) < 60:
            normalized = re.sub(r"\d+", "#", stripped.lower())
            line_counts[normalized] += 1

    repeated = {pattern for pattern, count in line_counts.items() if count >= 3}

    if not repeated:
        return text

    filtered_repeated = set()
    for pattern in repeated:
        is_legal = any(re.match(lp, pattern.strip()) for lp in legal_heading_patterns)
        if not is_legal:
            filtered_repeated.add(pattern)

    if not filtered_repeated:
        return text

    logger.info("Detectados %d padrões de cabeçalho/rodapé repetidos", len(filtered_repeated))

    first_seen: set[str] = set()
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        normalized = re.sub(r"\d+", "#", stripped.lower())
        if normalized in filtered_repeated:
            if preserve_first and normalized not in first_seen:
                first_seen.add(normalized)
                cleaned_lines.append(line)
                logger.debug("Preservada primeira ocorrência: %s", stripped[:50])
            else:
                continue
        else:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def separate_enumerations(text: str) -> str:
    """Garante que alíneas jurídicas (a), b), I —, etc.) sejam parágrafos separados."""
    lines = text.split("\n")
    result = []
    enum_re = re.compile(
        r"^([a-z]\)|[IVXLC]+\s*[-–—]\s|[ivxlc]+\)\s|\d+\.\d+\.?\s)"
    )
    for i, line in enumerate(lines):
        stripped = line.strip()
        if enum_re.match(stripped) and i > 0:
            prev = lines[i - 1].strip()
            if prev:
                result.append("")
        result.append(line)
    return "\n".join(result)


def normalize_paragraphs(text: str) -> str:
    """Normaliza separação de parágrafos. Remove quebras de linha excessivas."""
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text


def _is_block_boundary(line: str) -> bool:
    """Verifica se a linha é um delimitador de bloco que não deve ser unido."""
    s = line.strip()
    if not s:
        return True
    if s.startswith("#"):
        return True
    if s.startswith(("* ", "> ", "```")):
        return True
    if s == "---" or s == "***":
        return True
    if s.startswith("|"):
        return True
    # Seções numeradas (N. TÍTULO) são sempre block boundaries
    if re.match(r"^\d+\.\s+[A-ZÁÉÍÓÚÀÂÊÔÃÕÇ]", s):
        return True
    # Seções com numeração romana (I –, II –, etc.) também são boundaries
    if re.match(r"^[IVXLC]+\s*[-–—.]\s+[A-ZÁÉÍÓÚÀÂÊÔÃÕÇ]", s) and s.upper() == s:
        return True
    if s.isupper() and len(s) < 100:
        return True
    return False


def _is_next_line_protected(line: str) -> bool:
    """Verifica se a linha seguinte é protegida e NÃO deve ser unida à anterior."""
    s = line.strip()
    if not s:
        return True
    if s.startswith(("#", "- ", "* ", "> ", "|", "```")):
        return True
    if s == "---" or s == "***":
        return True
    if re.match(
        r"^([a-z]\)|[a-z]\.|[ivxlc]+\)|[IVXLC]+\)|\d+\)|\d+\.|[IVXLC]+\s*[-–—]\s+|§\s*\d+)\s*",
        s,
    ):
        return True
    # Seções numeradas (N. TÍTULO) são sempre protegidas
    if re.match(r"^\d+\.\s+[A-ZÁÉÍÓÚÀÂÊÔÃÕÇ]", s):
        return True
    # Seções com numeração romana também são protegidas
    if re.match(r"^[IVXLC]+\s*[-–—.]\s+[A-ZÁÉÍÓÚÀÂÊÔÃÕÇ]", s) and s.upper() == s:
        return True
    if s.isupper() and len(s) < 100:
        return True
    return False


_TRAILING_PREPOSITIONS = re.compile(
    r"\b(?:de|da|do|das|dos|na|no|nas|nos|em|com|que|e|ou|para|por|ao|à|aos|às)\s*$",
    re.IGNORECASE,
)


def _ends_sentence(line: str) -> bool:
    """Verifica se a linha termina com pontuação de fim de sentença."""
    s = line.rstrip()
    if not s:
        return True
    return s[-1] in ".!?;"


def _ends_with_preposition(line: str) -> bool:
    """Verifica se a linha termina com preposição/conjunção (continuação obrigatória)."""
    return bool(_TRAILING_PREPOSITIONS.search(line.rstrip()))


def rejoin_broken_paragraphs(text: str) -> str:
    """Junta linhas quebradas por extração de PDF em parágrafos contínuos."""
    text = unicodedata.normalize("NFC", text)
    lines = text.split("\n")
    result = []
    buffer = ""

    for i, line in enumerate(lines):
        stripped = line.strip()

        if _is_block_boundary(stripped):
            if buffer:
                result.append(buffer)
                buffer = ""
            result.append(line)
            continue

        if re.match(r"^([a-z]\)|[a-z]\.|[ivxlc]+\)|[IVXLC]+\)|\d+\)|\d+\.|[IVXLC]+\s*[-–—]\s+|§\s*\d+)\s*", stripped):
            if buffer:
                result.append(buffer)
                buffer = ""
            buffer = stripped
            continue

        # Seções numeradas (N. TÍTULO EM MAIÚSCULAS) nunca são merged
        if re.match(r"^\d+\.\s+[A-ZÁÉÍÓÚÀÂÊÔÃÕÇ]", stripped) and stripped.upper() == stripped:
            if buffer:
                result.append(buffer)
                buffer = ""
            result.append(stripped)
            continue

        # Seções com numeração romana (I –, II –) nunca são merged
        if re.match(r"^[IVXLC]+\s*[-–—.]\s+[A-ZÁÉÍÓÚÀÂÊÔÃÕÇ]", stripped) and stripped.upper() == stripped:
            if buffer:
                result.append(buffer)
                buffer = ""
            result.append(stripped)
            continue

        if not buffer:
            buffer = stripped
            continue

        if _ends_with_preposition(buffer):
            buffer = buffer + " " + stripped
            continue

        if not _ends_sentence(buffer) and not _is_next_line_protected(stripped):
            buffer = buffer + " " + stripped
        else:
            result.append(buffer)
            buffer = stripped

    if buffer:
        result.append(buffer)

    return "\n".join(result)


def remove_ereader_boilerplate(text: str) -> str:
    """Remove blocos de instruções de e-reader/epub do início do documento."""
    lines = text.split("\n")
    if len(lines) < 5:
        return text

    scan_limit = min(150, len(lines))
    first_keyword_line = -1
    last_keyword_line = -1
    keyword_count = 0

    for i in range(scan_limit):
        lower = lines[i].strip().lower()
        if not lower:
            continue
        if any(kw in lower for kw in EREADER_KEYWORDS):
            keyword_count += 1
            if first_keyword_line == -1:
                first_keyword_line = i
            last_keyword_line = i

    if keyword_count < 3 or first_keyword_line == -1:
        return text

    cut_start = first_keyword_line
    cut_end = last_keyword_line + 1

    while cut_end < len(lines):
        stripped = lines[cut_end].strip()
        if stripped and len(stripped) > 40:
            lower = stripped.lower()
            if not any(kw in lower for kw in EREADER_KEYWORDS):
                break
        if not stripped or len(stripped) < 40:
            cut_end += 1
            continue
        break

    logger.info(
        "Removidas linhas %d-%d de boilerplate de e-reader (%d keywords)",
        cut_start,
        cut_end,
        keyword_count,
    )
    return "\n".join(lines[:cut_start] + lines[cut_end:])


def normalize_legal_citations(text: str) -> str:
    """Normaliza citações jurídicas para formato padronizado."""
    text = re.sub(
        r"\b[Aa][Rr][Tt](?:[Ii][Gg][Oo])?\s*\.?\s*(\d)",
        r"Art. \1",
        text,
    )
    text = re.sub(
        r"\b[Pp][Aa][Rr](?:[ÁáAa][Gg][Rr][Aa][Ff][Oo])?\.?\s*(?=\d|[Úú]nico)",
        "§ ",
        text,
    )
    text = re.sub(r"§\s*§", "§", text)
    text = re.sub(r"(Art\.)\s*(\d)", r"\1 \2", text)
    text = re.sub(r"(§)\s*(\d)", r"\1 \2", text)
    text = re.sub(r"(Art\.\s*\d+[º°]?)\s+,", r"\1,", text)
    text = re.sub(r"(Art\.\s*\d+)\s*[oO](?=\s|,|$|\.)", r"\1º", text)
    text = re.sub(r"\b[Aa]linea\b", "alínea", text)
    return text


def _latin_ratio(text: str) -> float:
    """Calcula a proporção de caracteres latinos + espaço em uma string."""
    if not text:
        return 1.0
    latin_count = 0
    total = 0
    for ch in text:
        if ch.isspace():
            continue
        total += 1
        cat = unicodedata.category(ch)
        if cat.startswith("L"):
            try:
                script = unicodedata.name(ch, "")
                if any(w in script for w in ("LATIN", "DIGIT", "SPACE", "FULL STOP",
                        "COMMA", "SEMICOLON", "COLON", "QUOTATION", "APOSTROPHE", "HYPHEN")):
                    latin_count += 1
                elif ord(ch) < 0x024F:
                    latin_count += 1
            except ValueError:
                pass
        elif cat.startswith(("N", "P", "S", "Z")):
            latin_count += 1
    return latin_count / total if total > 0 else 1.0


def remove_corrupted_glyphs(text: str) -> str:
    """Remove caracteres não-latinos corrompidos do texto."""
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if len(stripped) < 3:
            cleaned.append(line)
            continue

        non_latin_count = 0
        letter_count = 0
        for ch in stripped:
            if ch.isspace():
                continue
            cat = unicodedata.category(ch)
            if cat.startswith("L"):
                letter_count += 1
                if ord(ch) > 0x024F:
                    non_latin_count += 1

        if non_latin_count == 0:
            cleaned.append(line)
            continue

        if letter_count == 0:
            cleaned.append(line)
            continue

        ratio = non_latin_count / letter_count

        if ratio > 0.3:
            logger.debug("Removida linha com glyphs corrompidos: %s...", stripped[:40])
            continue

        clean_line = []
        for ch in line:
            if ord(ch) > 0x024F and unicodedata.category(ch).startswith("L"):
                continue
            clean_line.append(ch)
        result_line = "".join(clean_line)
        result_line = re.sub(r" +", " ", result_line)
        cleaned.append(result_line)
            return "\n".join(cleaned)
    return "\n".join(cleaned)
