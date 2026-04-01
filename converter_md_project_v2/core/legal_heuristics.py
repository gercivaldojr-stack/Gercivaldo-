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
    r"^[IVXLC]+\s*[-–—]\s+",  # I — texto, II – texto (alíneas romanas com travessão)
    r"^\d+\)\s+",           # 1) texto, 2) texto
    r"^\d+\.\d+\.?\s+",    # 1.1 texto, 1.2. texto (subseções numéricas no modo forense)
]

# Padrões de seções numeradas forense: \d+\.\s+MAIÚSCULAS → H2
FORENSE_NUMBERED_H2_PATTERN = re.compile(
    r"^(\d+)\.\s+([A-ZÁÉÍÓÚÀÂÊÔÃÕÇ][A-ZÁÉÍÓÚÀÂÊÔÃÕÇ\s]{2,})$"
)

# Padrões de subseções numeradas forense: \d+\.\d+ → H3
FORENSE_NUMBERED_H3_PATTERN = re.compile(
    r"^(\d+\.\d+\.?)\s+(.*)"
)

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


def apply_legal_heuristics(
    text: str,
    mode: str = "forense",
    detect_citations: bool = True,
    separate_enums: bool = False,
    wrap_notes: bool = False,
) -> str:
    """Aplica heurísticas jurídicas ao texto para gerar headings Markdown.

    Args:
        text: Texto limpo.
        mode: 'forense' para peças processuais, 'doutrina' para livros/artigos.
        detect_citations: Se True, detecta citações jurisprudenciais como blockquote (P7).
        separate_enums: Se True, separa itens enumerados com ; em lista (M2).
        wrap_notes: Se True, demarca notas internas em blockquote (M3).

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
    # Citações jurisprudenciais apenas no modo forense (quando habilitado)
    citations_enabled = detect_citations and mode == "forense"
    structured = detect_blockquotes(structured, detect_citations=citations_enabled)

    # M2: Separar itens enumerados (modo forense)
    if separate_enums and mode == "forense":
        structured = separate_enumerated_items(structured)

    # M3: Demarcar notas internas (modo forense)
    if wrap_notes and mode == "forense":
        structured = wrap_internal_notes(structured)

    return structured


def _is_enumeration(line: str) -> bool:
    """Verifica se a linha é um item de enumeração (a), b), 1., I —, 1.1, etc.).

    NÃO considera enumeração se for seção numerada com título em MAIÚSCULAS
    (ex: '1. DOS FATOS' → é heading, não enumeração).
    """
    for p in ENUMERATION_PATTERNS:
        if re.match(p, line):
            # Exceção: \d+\.\s+MAIÚSCULAS é seção numerada, não enumeração
            if re.match(r"^\d+\.\s+[A-ZÁÉÍÓÚÀÂÊÔÃÕÇ][A-ZÁÉÍÓÚÀÂÊÔÃÕÇ\s]{2,}$", line.strip()):
                return False
            return True
    return False


def _apply_forense(line: str) -> str:
    """Aplica padrões forenses a uma linha."""
    upper_line = line.upper().strip()

    # H1: títulos de peças processuais
    for pattern in FORENSE_H1_PATTERNS:
        if re.match(pattern, upper_line, re.IGNORECASE):
            return f"# {line}"

    # H2: endereçamento ao juiz (EXCELENTÍSSIMO → H2)
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

    # M5: Seções numeradas \d+\.\s+MAIÚSCULAS → H2
    if FORENSE_NUMBERED_H2_PATTERN.match(line.strip()):
        return f"## {line}"

    # M5: Subseções numeradas \d+\.\d+ → H3 (somente linhas curtas)
    if len(line) < 100 and FORENSE_NUMBERED_H3_PATTERN.match(line.strip()):
        return f"### {line}"

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


# P7: Padrão para citações jurisprudenciais inline
# Detecta parágrafos começando com "No HC ...", "No AgRg no RHC ...", etc.
_JURISPRUDENCE_CITATION_START = re.compile(
    r"^No\s+(?:HC|RHC|AgRg\s+no\s+(?:RHC|AREsp|REsp)|REsp|ARE|AREsp|ADI|ADPF|RE|"
    r"EREsp|PEDILEF|AgInt\s+no\s+(?:AREsp|REsp)|RMS|CC)\s+[\d./-]+",
    re.IGNORECASE,
)


def detect_blockquotes(text: str, detect_citations: bool = True) -> str:
    """Detecta e formata blocos de citação jurídica como blockquotes Markdown.

    Detecta três tipos:
    1. Ementas: bloco iniciado por "EMENTA" até a próxima linha em branco dupla
       ou próximo heading.
    2. Citações longas com atribuição a tribunais: bloco entre aspas ou
       seguido de referência a tribunal (STF, STJ, TJ...).
    3. Citações jurisprudenciais inline: parágrafos que começam com
       "No HC/REsp/AgRg..." referenciando julgados específicos (P7).

    Args:
        text: Texto com headings aplicados.
        detect_citations: Se True, detecta citações jurisprudenciais (tipo 3).
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

        # --- Tipo 3: Citação jurisprudencial inline (P7) ---
        if detect_citations and _JURISPRUDENCE_CITATION_START.match(stripped):
            citation_lines = [stripped]
            i += 1
            # Coletar linhas do mesmo parágrafo (sem linha em branco)
            while i < len(lines):
                s = lines[i].strip()
                if not s or s.startswith("#"):
                    break
                # Se próxima linha é outra citação ou texto normal, parar
                if _JURISPRUDENCE_CITATION_START.match(s):
                    break
                citation_lines.append(s)
                i += 1

            logger.debug(
                "Detectada citação jurisprudencial: %s...",
                citation_lines[0][:60],
            )
            for cl in citation_lines:
                result.append(f"> {cl}")
            result.append("")
            continue

        result.append(line)
        i += 1

    return "\n".join(result)


# ============================================================
# M2: Separação de itens enumerados (v4.1)
# ============================================================

# Padrão: texto terminando em : seguido de itens separados por ;
_ENUM_SEMICOLON_RE = re.compile(r";\s*$")


def separate_enumerated_items(text: str) -> str:
    """Separa itens enumerados por ponto-e-vírgula em lista Markdown (v4.1 M2).

    Padrão 1: Frase terminada em ':' seguida de itens com ';' no final
    → cada item vira '- item' em lista Markdown.

    Padrão 2: Linhas soltas terminadas com ';'
    → insere linha em branco entre cada item para melhor legibilidade.
    """
    lines = text.split("\n")
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Detectar introdução de lista (frase terminando em :)
        if stripped.endswith(":") and len(stripped) > 10 and not stripped.startswith("#"):
            result.append(line)
            i += 1
            # Coletar itens subsequentes com ;
            items_found = []
            while i < len(lines):
                s = lines[i].strip()
                if not s:
                    break
                if s.startswith("#") or s.startswith(">"):
                    break
                # Item terminando com ; ou . (último item)
                items_found.append(s)
                if not _ENUM_SEMICOLON_RE.search(s):
                    # Último item (sem ;) — incluir e parar
                    i += 1
                    break
                i += 1

            if len(items_found) >= 2 and any(
                _ENUM_SEMICOLON_RE.search(it) for it in items_found
            ):
                # Converter para lista Markdown
                result.append("")
                for item in items_found:
                    # Remover alíneas já existentes (a), b), etc.)
                    clean_item = re.sub(r"^[a-z]\)\s*", "", item)
                    clean_item = re.sub(r"^[ivxlc]+\)\s*", "", clean_item, flags=re.IGNORECASE)
                    result.append(f"- {clean_item}")
                result.append("")
                logger.debug(
                    "M2: %d itens enumerados separados após '%s'",
                    len(items_found), stripped[:40],
                )
            else:
                # Não é lista, manter original
                result.extend(items_found)
            continue

        # Padrão 2: Linhas soltas com ;
        if _ENUM_SEMICOLON_RE.search(stripped) and len(stripped) > 15:
            result.append(line)
            # Verificar se próxima linha também termina com ;
            if i + 1 < len(lines) and _ENUM_SEMICOLON_RE.search(lines[i + 1].strip()):
                result.append("")  # Linha em branco entre itens
            i += 1
            continue

        result.append(line)
        i += 1

    return "\n".join(result)


# ============================================================
# M3: Notas internas — envolver em blockquote (v4.1)
# ============================================================

_INTERNAL_NOTE_PATTERNS = [
    re.compile(r"^(?:#{1,6}\s+)?Observa[çc][oõ]es?\s+finais?\s+de\s+uso", re.IGNORECASE),
    re.compile(r"^(?:#{1,6}\s+)?Nota\s+de\s+adequa[çc][aã]o", re.IGNORECASE),
    re.compile(r"^(?:#{1,6}\s+)?Instru[çc][oõ]es?\s+para\s+protocolo", re.IGNORECASE),
    re.compile(r"^(?:#{1,6}\s+)?Nota\s+interna", re.IGNORECASE),
    re.compile(r"^(?:#{1,6}\s+)?Observa[çc][oõ]es?\s+ao\s+advogado", re.IGNORECASE),
    re.compile(r"^(?:#{1,6}\s+)?Instru[çc][oõ]es?\s+ao\s+cliente", re.IGNORECASE),
]


def wrap_internal_notes(text: str) -> str:
    """Detecta e demarca seções de notas internas como blockquote (v4.1 M3).

    Detecta seções como:
    - "Observações finais de uso"
    - "Nota de adequação"
    - "Instruções para protocolo"

    Envolve o conteúdo em blockquote com aviso.
    """
    lines = text.split("\n")
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Detectar início de nota interna
        is_note_start = any(p.match(stripped) for p in _INTERNAL_NOTE_PATTERNS)
        if is_note_start:
            note_lines = [stripped]
            i += 1
            blank_count = 0

            # Coletar conteúdo da nota até fim do documento ou próximo heading
            while i < len(lines):
                s = lines[i].strip()
                # Parar em heading (exceto se faz parte da nota)
                if s.startswith("#") and not any(p.match(s) for p in _INTERNAL_NOTE_PATTERNS):
                    break
                if not s:
                    blank_count += 1
                    if blank_count >= 3:
                        break
                    i += 1
                    continue
                blank_count = 0
                note_lines.append(s)
                i += 1

            # Formatar como blockquote com aviso
            result.append("")
            result.append("> **Nota interna** — nao integra a peca processual.")
            result.append(">")
            for nl in note_lines:
                result.append(f"> {nl}")
            result.append("")
            logger.debug("M3: Nota interna detectada: %s", note_lines[0][:50])
            continue

        result.append(line)
        i += 1

    return "\n".join(result)
