"""
Módulo de heurísticas jurídicas para estruturação de texto.
Dois modos: forense (peças processuais) e doutrina (livros/artigos).
"""

import logging
import re

logger = logging.getLogger(__name__)

# ============================================================
# Padrões de headings jurídicos — modo forense
# ============================================================

# H1: títulos de peças processuais (tipo do documento)
FORENSE_H1_PATTERNS = [
    r"^(PETIÇÃO\s+INICIAL.*)",
    r"^(CONTESTAÇÃO.*)",
    r"^(SENTENÇA.*)",
    r"^(ACÓRDÃO.*)",
    r"^(RECURSO\s+.*)",
    r"^(AGRAVO\s+.*)",
    r"^(APELAÇÃO.*)",
    r"^(MANDADO\s+DE\s+SEGURANÇA.*)",
    r"^(HABEAS\s+CORPUS.*)",
]

# H2 de endereçamento (não são títulos de peça, são cabeçalhos de cortesia)
FORENSE_ENDERECAMENTO_PATTERNS = [
    r"^(EXCELENTÍSSIM[OA]\s+SENHOR[A]?\s+.*)",
    r"^(AO\s+JUÍZ[OA]?\s+.*)",
    r"^(AO\s+DOUTOR\s+JUIZ.*)",
    r"^(AO\s+MERITÍSSIMO\s+.*)",
    r"^(AO\s+MM\.?\s+JUIZ.*)",
]

FORENSE_H2_PATTERNS = [
    r"^(I+\s*[-–—.]\s*DOS?\s+FATOS?.*)",
    r"^(I+\s*[-–—.]\s*DO\s+DIREITO.*)",
    r"^(I+\s*[-–—.]\s*D[AO]S?\s+FUNDAMENT.*)",
    r"^(I+\s*[-–—.]\s*D[AO]S?\s+PEDIDO.*)",
    r"^(I+\s*[-–—.]\s*D[AO]\s+MÉRITO.*)",
    r"^(I+\s*[-–—.]\s*PRELIMINAR.*)",
    r"^(DOS?\s+FATOS?)\s*$",
    r"^(DO\s+DIREITO)\s*$",
    r"^(D[AO]S?\s+FUNDAMENT\w*)\s*$",
    r"^(D[AO]S?\s+PEDIDOS?)\s*$",
    r"^(DO\s+MÉRITO)\s*$",
    r"^(PRELIMINAR\w*)\s*$",
    r"^(FUNDAMENTAÇÃO\s*JURÍDICA?)\s*$",
    r"^(FUNDAMENTAÇÃO)\s*$",
    r"^(RELATÓRIO)\s*$",
    r"^(DISPOSITIVO)\s*$",
    r"^(EMENTA)\s*$",
    r"^(VOTO)\s*$",
    r"^(D[AO]S?\s+PROVAS?)\s*$",
    r"^(D[AO]\s+TUTELA\s+.*)",
    r"^(CLÁUSULA\s+\w+.*)",
]

# FIX: Art. removido de FORENSE_H3_PATTERNS.
# Artigos de lei citados em peças processuais são corpo do texto,
# não headings. O ### criava hierarquia indevida fragmentando a leitura.
FORENSE_H3_PATTERNS = []

# Padrões de subseções forenses (Da/Do/Das/Dos + substantivo com maiúscula)
# Ex: "Da responsabilidade objetiva do Réu", "Do dano moral in re ipsa"
FORENSE_H3_SUBSECTION_PATTERNS = [
    r"^(Da\s+[a-záéíóúàâêôãõç].*)",
    r"^(Do\s+[a-záéíóúàâêôãõç].*)",
    r"^(Das\s+[a-záéíóúàâêôãõç].*)",
    r"^(Dos\s+[a-záéíóúàâêôãõç].*)",
    r"^(Doe?\s+[A-ZÁÉÍÓÚÀÂÊÔÃÕÇ][a-záéíóúàâêôãõç].*)",
]

# Padrões de enumeração que NÃO devem virar heading (são itens de lista)
ENUMERATION_PATTERNS = [
    r"^[a-z]\)\s+",        # a) texto, b) texto
    r"^[a-z]\.\s+",        # a. texto, b. texto
    r"^[ivxlc]+\)\s+",     # i) texto, ii) texto
    r"^[IVXLC]+\)\s+",     # I) texto, II) texto
    r"^\d+\)\s+",           # 1) texto, 2) texto
    r"^\d+\.\s+",           # 1. texto, 2. texto
]

# ============================================================
# Padrões de headings jurídicos — modo doutrina
# ============================================================

DOUTRINA_H1_PATTERNS = [
    r"^(PARTE\s+[IVXLC]+\s*[-–—:]?\s*.*)",
    r"^(CAPÍTULO\s+[IVXLC\d]+\s*[-–—:]?\s*.*)",
    r"^(TÍTULO\s+[IVXLC\d]+\s*[-–—:]?\s*.*)",
    r"^(LIVRO\s+[IVXLC\d]+\s*[-–—:]?\s*.*)",
]

DOUTRINA_H2_PATTERNS = [
    r"^(SEÇÃO\s+[IVXLC\d]+\s*[-–—:]?\s*.*)",
    r"^(SUBSEÇÃO\s+[IVXLC\d]+\s*[-–—:]?\s*.*)",
    r"^(\d+\.\s+[A-ZÁÉÍÓÚÀÂÊÔÃÕÇ].*)",
]

DOUTRINA_H3_PATTERNS = [
    r"^(\d+\.\d+\.?\s+.*)",
    r"^(\d+\.\d+\.\d+\.?\s+.*)",
]

# Padrão de linhas de sumário a remover
SUMARIO_PATTERNS = [
    r"^(SUMÁRIO|ÍNDICE|CONTEÚDO)\s*$",
    r"^\d+\.\s+.*\.{2,}\s*\d+\s*$",  # "1. Introdução ......... 15"
    r"^[IVXLC]+\s*[-–—.]\s+.*\.{2,}\s*\d+\s*$",
]


def generate_toc(text: str) -> str:
    """Gera um índice/sumário automático a partir dos headings Markdown.

    Percorre o texto procurando linhas com #, ## e ### e gera uma lista
    de links Markdown com indentação hierárquica.

    Args:
        text: Texto Markdown com headings aplicados.

    Returns:
        Bloco Markdown do sumário, ou string vazia se < 2 headings.
    """
    headings = []
    for line in text.split("\n"):
        stripped = line.strip()
        match = re.match(r"^(#{1,3})\s+(.+)$", stripped)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            headings.append((level, title))

    if len(headings) < 2:
        return ""

    # Gerar slug para link âncora (compatível com GitHub/Streamlit Markdown)
    def _slugify(title: str) -> str:
        slug = title.lower()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[\s]+", "-", slug.strip())
        return slug

    toc_lines = ["## Sumário", ""]
    for level, title in headings:
        indent = "  " * (level - 1)
        slug = _slugify(title)
        toc_lines.append(f"{indent}- [{title}](#{slug})")

    toc_lines.append("")
    return "\n".join(toc_lines)


def apply_legal_heuristics(text: str, mode: str = "forense") -> str:
    """Aplica heurísticas jurídicas ao texto para gerar headings Markdown.

    Args:
        text: Texto limpo.
        mode: 'forense' para peças processuais, 'doutrina' para livros/artigos.

    Returns:
        Texto com headings Markdown aplicados.
    """
    if not text or not text.strip():
        return ""

    if mode == "doutrina":
        text = remove_sumario(text)

    lines = text.split("\n")
    result = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            result.append("")
            continue

        # Não modificar linhas que já são headings markdown
        if stripped.startswith("#"):
            result.append(line)
            continue

        if mode == "forense":
            converted = _apply_forense(stripped)
        else:
            converted = _apply_doutrina(stripped)

        result.append(converted)

    structured = "\n".join(result)
    structured = detect_blockquotes(structured)
    return structured


def _is_enumeration(line: str) -> bool:
    """Verifica se a linha é um item de enumeração (a), b), 1., etc.)."""
    return any(re.match(p, line) for p in ENUMERATION_PATTERNS)


def _apply_forense(line: str) -> str:
    """Aplica padrões forenses a uma linha."""
    upper_line = line.upper().strip()

    # H1: títulos de peças processuais
    for pattern in FORENSE_H1_PATTERNS:
        if re.match(pattern, upper_line, re.IGNORECASE):
            return f"# {line}"

    # H2: endereçamento ao juiz
    for pattern in FORENSE_ENDERECAMENTO_PATTERNS:
        if re.match(pattern, upper_line, re.IGNORECASE):
            return f"## {line}"

    # H2: seções principais (DOS FATOS, DO DIREITO, etc.)
    for pattern in FORENSE_H2_PATTERNS:
        if re.match(pattern, upper_line, re.IGNORECASE):
            return f"## {line}"

    # Ignorar itens de enumeração — nunca viram heading
    if _is_enumeration(line):
        return line

    # H3: subseções Da/Do/Das/Dos (linhas curtas, < 100 chars)
    if len(line) < 100:
        for pattern in FORENSE_H3_SUBSECTION_PATTERNS:
            if re.match(pattern, line):
                return f"### {line}"

        # H3: artigos de lei (apenas se FORENSE_H3_PATTERNS não estiver vazio)
        for pattern in FORENSE_H3_PATTERNS:
            if re.match(pattern, line, re.IGNORECASE):
                if len(line) > 200:
                    return line
                return f"### {line}"

    return line


def _apply_doutrina(line: str) -> str:
    """Aplica padrões de doutrina a uma linha."""
    upper_line = line.upper().strip()

    for pattern in DOUTRINA_H1_PATTERNS:
        if re.match(pattern, upper_line, re.IGNORECASE):
            return f"# {line}"

    for pattern in DOUTRINA_H2_PATTERNS:
        if re.match(pattern, upper_line, re.IGNORECASE):
            return f"## {line}"

    for pattern in DOUTRINA_H3_PATTERNS:
        if re.match(pattern, line):
            if len(line) > 200:
                return line
            return f"### {line}"

    return line


def remove_sumario(text: str) -> str:
    """Remove seções de sumário/índice do texto de doutrina."""
    lines = text.split("\n")
    result = []
    in_sumario = False
    blank_count = 0

    for line in lines:
        stripped = line.strip()

        # Detectar início de sumário
        if any(re.match(p, stripped, re.IGNORECASE) for p in SUMARIO_PATTERNS[:1]):
            in_sumario = True
            logger.info("Sumário detectado e removido")
            continue

        if in_sumario:
            # Linhas típicas de sumário (com pontos de preenchimento)
            if re.match(r".*\.{2,}\s*\d+\s*$", stripped):
                continue

            # Linhas numeradas simples de sumário
            if re.match(r"^\d+(\.\d+)*\.?\s+\S+", stripped) and len(stripped) < 80:
                continue

            # Duas linhas em branco seguidas encerram o sumário
            if not stripped:
                blank_count += 1
                if blank_count >= 2:
                    in_sumario = False
                    blank_count = 0
                continue
            else:
                blank_count = 0

            # Linha longa provavelmente é conteúdo real
            if len(stripped) > 80:
                in_sumario = False

        if not in_sumario:
            result.append(line)

    return "\n".join(result)


# ============================================================
# P5: Detecção de blockquotes (ementas e citações jurídicas)
# ============================================================

# Padrões que iniciam um bloco de citação/ementa
_BLOCKQUOTE_START_PATTERNS = [
    re.compile(r"^(?:#{1,6}\s+)?EMENTA\s*[:.]?\s*$", re.IGNORECASE),
    re.compile(r"^(?:#{1,6}\s+)?EMENTA\s*[-–—:.]", re.IGNORECASE),
]

# Padrões que indicam atribuição de citação jurisprudencial
_CITATION_ATTR_PATTERNS = [
    re.compile(
        r"\(\s*(?:STF|STJ|TST|TJ[A-Z]{2}|TRF|TRT|TSE)\b.*?\)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\(\s*(?:RE|REsp|HC|MS|ADI|ADPF|AgRg|AI|RMS)\s+[\d./-]+",
        re.IGNORECASE,
    ),
]


def detect_blockquotes(text: str) -> str:
    """Detecta e formata blocos de citação jurídica como blockquotes Markdown.

    Detecta dois tipos:
    1. Ementas: bloco iniciado por "EMENTA" até a próxima linha em branco dupla
       ou próximo heading.
    2. Citações longas com atribuição a tribunais: bloco entre aspas ou
       seguido de referência a tribunal (STF, STJ, TJ...).
    """
    lines = text.split("\n")
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # --- Tipo 1: Bloco de ementa ---
        is_ementa_start = any(p.match(stripped) for p in _BLOCKQUOTE_START_PATTERNS)
        if is_ementa_start:
            # Coletar linhas da ementa
            ementa_lines = [stripped]
            i += 1
            blank_count = 0
            while i < len(lines):
                s = lines[i].strip()
                # Parar em: heading, linha em branco dupla, ou início de nova seção
                if s.startswith("#"):
                    break
                if not s:
                    blank_count += 1
                    if blank_count >= 2:
                        break
                    i += 1
                    continue
                blank_count = 0
                ementa_lines.append(s)
                i += 1

            # Formatar como blockquote
            for el in ementa_lines:
                result.append(f"> {el}")
            result.append("")
            continue

        # --- Tipo 2: Citação entre aspas com atribuição a tribunal ---
        if stripped.startswith(("\u201c", '"')) and len(stripped) > 50:
            # Coletar bloco de citação até fechar aspas
            quote_lines = [stripped]
            has_closing = "\u201d" in stripped or (
                stripped.startswith('"') and stripped.count('"') >= 2
            )
            i += 1

            if not has_closing:
                while i < len(lines):
                    s = lines[i].strip()
                    if not s:
                        break
                    quote_lines.append(s)
                    if "\u201d" in s or s.endswith('"'):
                        has_closing = True
                        i += 1
                        break
                    i += 1

            # Verificar atribuição a tribunal na última linha ou próxima
            full_quote = " ".join(quote_lines)
            has_attribution = any(
                p.search(full_quote) for p in _CITATION_ATTR_PATTERNS
            )
            # Checar próxima linha para atribuição
            if not has_attribution and i < len(lines):
                next_line = lines[i].strip()
                if any(p.search(next_line) for p in _CITATION_ATTR_PATTERNS):
                    has_attribution = True
                    quote_lines.append(next_line)
                    i += 1

            if has_attribution and has_closing:
                for ql in quote_lines:
                    result.append(f"> {ql}")
                result.append("")
                continue
            else:
                # Não é citação jurídica, manter original
                result.extend(quote_lines)
                continue

        result.append(line)
        i += 1

    return "\n".join(result)
