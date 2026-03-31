"""
Módulo de limpeza e normalização de texto extraído.
Remove artefatos de OCR, hifenização, cabeçalhos/rodapés repetidos, ruído,
boilerplate de e-reader e glyphs corrompidos.
"""

import logging
import re
import unicodedata
from collections import Counter

logger = logging.getLogger(__name__)

# Palavras-chave de instruções de e-reader/epub a remover no início do documento
EREADER_KEYWORDS = [
    "escolher fonte", "alterar layout", "luminosidade",
    "fazer buscas", "anotar trechos", "menu",
    "marca-texto", "marcador", "bookmark",
    "aumentar fonte", "diminuir fonte", "tamanho da fonte",
    "modo noturno", "modo de leitura",
    "configurações de leitura", "opções de visualização",
    "deslize para", "toque para", "toque na tela",
    "arraste", "pinça para zoom",
    "sumário interativo", "índice interativo",
    "navegação", "barra de progresso",
    "epub", "e-reader", "e-book", "ebook",
    "kindle", "kobo", "google play livros", "apple books",
    "this ebook", "digital rights", "drm",
    "choose font", "adjust layout", "brightness",
    "search text", "annotate", "highlight",
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

    text = fix_hyphenation(text)
    text = normalize_whitespace(text)
    text = remove_corrupted_glyphs(text)
    text = remove_ocr_noise(text)
    text = remove_ereader_boilerplate(text)

    if remove_headers_footers:
        text = remove_repeated_headers_footers(text)

    text = rejoin_broken_paragraphs(text)
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

    Remove quebras de linha excessivas (> 2 em sequência).
    A junção de linhas quebradas é feita por rejoin_broken_paragraphs.
    """
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text


def _is_block_boundary(line: str) -> bool:
    """Verifica se a linha é um delimitador de bloco que não deve ser unido."""
    s = line.strip()
    if not s:
        return True
    # Headings markdown
    if s.startswith("#"):
        return True
    # Listas markdown explícitas (*, >) mas NÃO travessão (-) que é comum em texto jurídico
    if s.startswith(("* ", "> ", "```")):
        return True
    # Separadores markdown
    if s == "---" or s == "***":
        return True
        # FIX: Linhas em maiúsculas curtas com < 4 palavras são provavelmente
            # fragmentos de ementa, não headings reais — permitir rejunção
                if s.isupper() and len(s) < 100 and len(s.split()) >= 4:
                        return True
    return False


def _ends_sentence(line: str) -> bool:
    """Verifica se a linha termina com pontuação de fim de sentença."""
    s = line.rstrip()
    if not s:
        return True
    # Pontuação forte de final de sentença
    return s[-1] in ".!?;:"


def rejoin_broken_paragraphs(text: str) -> str:
    """Junta linhas quebradas por extração de PDF em parágrafos contínuos.

    Heurística: uma linha que NÃO termina com pontuação final e é seguida
    por outra linha de texto (sem linha em branco entre elas) faz parte do
    mesmo parágrafo. A junção é feita com espaço.

    Linhas protegidas (nunca unidas):
    - Headings markdown (#)
    - Linhas em branco
    - Listas (-, *, >)
    - Linhas todas em maiúsculas (prováveis headings jurídicos)
    - Linhas que começam com enumeração (a), b), 1., Art.)
    """
    lines = text.split("\n")
    result = []
    buffer = ""

    for line in lines:
        stripped = line.strip()

        # Se é um delimitador, flush o buffer e preservar
        if _is_block_boundary(stripped):
            if buffer:
                result.append(buffer)
                buffer = ""
            result.append(line)
            continue

        # Se a linha atual começa com padrão de enumeração, flush e iniciar novo
        if re.match(r"^([a-z]\)|[a-z]\.|[ivxlc]+\)|[IVXLC]+\)|\d+\)|\d+\.|[IVXLC]+\s*[-–—]\s+|§\s*\d+)\s*", stripped):
            if buffer:
                result.append(buffer)
                buffer = ""
            buffer = stripped
            continue

        # Se o buffer está vazio, começar acumulando
        if not buffer:
            buffer = stripped
            continue

        # Se o buffer não termina com pontuação final, unir
        if not _ends_sentence(buffer):
            buffer = buffer + " " + stripped
        else:
            # Buffer termina com pontuação — é parágrafo completo
            result.append(buffer)
            buffer = stripped

    if buffer:
        result.append(buffer)

    return "\n".join(result)


def remove_ereader_boilerplate(text: str) -> str:
    """Remove blocos de instruções de e-reader/epub do início do documento.

    Analisa as primeiras 150 linhas. Se encontrar 3+ linhas com keywords
    típicas de leitor digital, remove desde a primeira keyword até a
    última, incluindo linhas em branco e linhas curtas ao redor.
    """
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

    # Cortar desde a primeira keyword line até após a última
    cut_start = first_keyword_line
    cut_end = last_keyword_line + 1

    # Avançar cut_end para incluir linhas residuais curtas após o bloco
    while cut_end < len(lines):
        stripped = lines[cut_end].strip()
        # Parar quando encontrar conteúdo real (linha longa sem keywords)
        if stripped and len(stripped) > 40:
            lower = stripped.lower()
            if not any(kw in lower for kw in EREADER_KEYWORDS):
                break
        # Linhas em branco ou curtas: incluir na remoção
        if not stripped or len(stripped) < 40:
            cut_end += 1
            continue
        break

    logger.info(
        "Removidas linhas %d-%d de boilerplate de e-reader (%d keywords)",
        cut_start, cut_end, keyword_count,
    )
    return "\n".join(lines[:cut_start] + lines[cut_end:])


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
        # Letras latinas (L*), números (N*), pontuação (P*), símbolos comuns (S*)
        if cat.startswith("L"):
            # Verificar se é script latino ou comum
            try:
                script = unicodedata.name(ch, "")
                if any(w in script for w in ("LATIN", "DIGIT", "SPACE", "FULL STOP",
                                              "COMMA", "SEMICOLON", "COLON",
                                              "QUOTATION", "APOSTROPHE", "HYPHEN")):
                    latin_count += 1
                elif ord(ch) < 0x024F:  # Bloco Latin Extended
                    latin_count += 1
                else:
                    pass  # Não-latino
            except ValueError:
                pass
        elif cat.startswith(("N", "P", "S", "Z")):
            latin_count += 1
    return latin_count / total if total > 0 else 1.0


def remove_corrupted_glyphs(text: str) -> str:
    """Remove caracteres não-latinos corrompidos do texto.

    Dois modos de atuação:
    1. Linhas com >30% de letras não-latinas: remove a linha inteira.
    2. Linhas mistas: remove apenas os caracteres não-latinos inline,
       preservando o texto latino ao redor.

    Preserva acentuação portuguesa (À-ÿ) e caracteres latinos normais.
    """
    lines = text.split("\n")
    cleaned = []

    for line in lines:
        stripped = line.strip()

        if len(stripped) < 3:
            cleaned.append(line)
            continue

        # Contar chars não-latinos na linha
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

        # Linha majoritariamente non-latin: remover inteira
        if ratio > 0.3:
            logger.debug("Removida linha com glyphs corrompidos: %s...", stripped[:40])
            continue

        # Linha mista: remover apenas os chars non-latin inline
        clean_line = []
        for ch in line:
            if ord(ch) > 0x024F and unicodedata.category(ch).startswith("L"):
                continue  # Pular glyph non-latin
            clean_line.append(ch)
        result_line = "".join(clean_line)
        # Limpar espaços duplos gerados pela remoção
        result_line = re.sub(r"  +", " ", result_line)
        cleaned.append(result_line)

    return "\n".join(cleaned)
