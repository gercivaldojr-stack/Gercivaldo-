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
    r"^(AÇÃO\s+\w+.*)",
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

FORENSE_H3_PATTERNS = []

# Padrões de subseções forenses (Da/Do/Das/Dos + substantivo)
FORENSE_H3_SUBSECTION_PATTERNS = [
    r"^(Da\s+[a-záéíóúàâêôãõç].*)",
    r"^(Do\s+[a-záéíóúàâêôãõç].*)",
    r"^(Das\s+[a-záéíóúàâêôãõç].*)",
    r"^(Dos\s+[a-záéíóúàâêôãõç].*)",
    r"^(Doe?\s+[A-ZÁÉÍÓÚÀÂÊÔÃÕÇ][a-záéíóúàâêôãõç].*)",
]

# Padrões de enumeração que NÃO devem virar heading (são itens de lista)
ENUMERATION_PATTERNS = [
    r"^[a-z]\)\s+",         # a) texto, b) texto
    r"^[a-z]\.\s+",         # a. texto, b. texto
    r"^[ivxlc]+\)\s+",      # i) texto, ii) texto
    r"^[IVXLC]+\)\s+",      # I) texto, II) texto
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
    r"^\d+\.\s+.*\.{2,}\s*\d+\s*$",
    r"^[IVXLC]+\s*[-–—.]\s+.*\.{2,}\s*\d+\s*$",
]


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

    return "\n".join(result)


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

    # H3: artigos de lei (se FORENSE_H3_PATTERNS não estiver vazio)
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


def _fix_heading_hierarchy(text: str) -> str:
    """Garante que o primeiro heading do documento é H1.

    Se o primeiro heading encontrado for ## ou ###, e não houver # antes dele,
    promove-o para # H1. Isso evita documentos começando com H2 (ex: endereçamento)
    sem título de peça acima.
    """
    lines = text.split("\n")
    first_heading_idx = None
    has_h1_before = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            has_h1_before = True
            break
        if stripped.startswith("## ") or stripped.startswith("### "):
            first_heading_idx = i
            break

    # Se o primeiro heading é ## ou ### sem H1 antes, promover para H1
    if first_heading_idx is not None and not has_h1_before:
        line = lines[first_heading_idx].strip()
        if line.startswith("### "):
            lines[first_heading_idx] = "# " + line[4:]
        elif line.startswith("## "):
            lines[first_heading_idx] = "# " + line[3:]
        logger.info("Promovido primeiro heading para H1: %s", lines[first_heading_idx][:60])

    return "\n".join(lines)


def _format_enumeration_as_list(text: str) -> str:
    """Converte itens de enumeração em listas markdown.

    Transforma padrões como:
        a) texto   ->  - **a)** texto
        b) texto   ->  - **b)** texto
        1. texto   ->  - **1.** texto
    """
    lines = text.split("\n")
    result = []

    for line in lines:
        stripped = line.strip()

        # Padrão letra) ou letra.
        m = re.match(r"^([a-z]\))\s+(.*)", stripped)
        if m:
            result.append(f"- **{m.group(1)}** {m.group(2)}")
            continue

        m = re.match(r"^([a-z]\.)\s+(.*)", stripped)
        if m:
            result.append(f"- **{m.group(1)}** {m.group(2)}")
            continue

        # Padrão número)
        m = re.match(r"^(\d+\))\s+(.*)", stripped)
        if m:
            result.append(f"- **{m.group(1)}** {m.group(2)}")
            continue

        result.append(line)

    return "\n".join(result)


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
