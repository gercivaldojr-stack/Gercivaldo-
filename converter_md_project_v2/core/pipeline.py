"""
Pipeline principal de conversão de documentos jurídicos para Markdown.
Orquestra extração, limpeza, heurísticas e separação de peças.
"""

import logging
from dataclasses import dataclass, field

from .cleaning import clean_text
from .extractors import extract_text
from .legal_heuristics import apply_legal_heuristics, generate_toc
from .metadata import extract_procedural_metadata, generate_frontmatter
from .piece_separator import format_separated_pieces, separate_pieces

logger = logging.getLogger(__name__)


def _strip_existing_frontmatter(text: str) -> str:
    """Remove frontmatter YAML, sumário embutido e lixo residual do original.

    Remove:
    - Blocos entre --- no início do texto (frontmatter YAML padrão)
    - Linhas de YAML inline soltas (titulo:, data:, status:, etc.)
    - Blocos ## Sumário / ## Índice seguidos de listas - [...] até linha em branco
    - Blocos de TOC malformado: 3+ linhas consecutivas com "- [" sem "](#"
    """
    import re
    lines = text.split("\n")
    result = []
    i = 0

    _yaml_inline_re = re.compile(
        r"^(?:titulo|data|status|convertido_em|proad|orgao_emissor|tipo_peca"
        r"|paciente|autor|reu|impetrante|autoridade_coatora|pedido_liminar"
        r"|processo_origem|comarca|acoes_cumuladas)\s*:", re.IGNORECASE
    )

    # Pular frontmatter YAML no início (bloco entre ---)
    if lines and lines[0].strip() == "---":
        i = 1
        while i < len(lines):
            if lines[i].strip() == "---":
                i += 1
                break
            i += 1

    # Processar resto do texto
    while i < len(lines):
        stripped = lines[i].strip()

        # Detectar sumário embutido com heading
        if re.match(r"^#{1,3}\s+(?:Sumário|Índice|SUMÁRIO|ÍNDICE)\s*$", stripped):
            i += 1
            while i < len(lines):
                s = lines[i].strip()
                if s.startswith("- [") or s.startswith("  - [") or s.startswith("    - [") or not s:
                    i += 1
                    if not s:
                        break
                else:
                    break
            continue

        # Remover linhas de YAML inline soltas (fora de bloco ---)
        if _yaml_inline_re.match(stripped):
            i += 1
            continue

        # Remover linhas que parecem YAML genérico (chave: "valor")
        if re.match(r"^\w+:\s+[\"'].*[\"']\s*\w*:\s*[\"']", stripped):
            i += 1
            continue

        # Detectar TOC malformado: 3+ linhas "- [" sem "](#"
        if stripped.startswith("- [") and "](#" not in stripped:
            malformed_start = i
            j = i
            while j < len(lines) and lines[j].strip().startswith("- ["):
                j += 1
            if j - malformed_start >= 3:
                # 3+ linhas de TOC malformado — pular todas
                i = j
                # Pular linhas em branco após o bloco
                while i < len(lines) and not lines[i].strip():
                    i += 1
                continue

        result.append(lines[i])
        i += 1

    return "\n".join(result)


@dataclass
class ConversionResult:
    """Resultado da conversão de um documento."""
    markdown: str = ""
    pieces: list[dict] = field(default_factory=list)
    filename: str = ""
    mode: str = "forense"
    success: bool = True
    error: str = ""
    stats: dict = field(default_factory=dict)


def convert_document(
    file_path: str | None = None,
    file_bytes: bytes | None = None,
    filename: str | None = None,
    mode: str = "forense",
    separate: bool = False,
    remove_headers_footers: bool = True,
    detect_citations: bool = True,
    extract_metadata: bool = False,
    extract_procedural: bool = False,
    separate_enums: bool = False,
    wrap_notes: bool = False,
) -> ConversionResult:
    """Converte um documento jurídico para Markdown estruturado.

    Args:
        file_path: Caminho do arquivo no disco.
        file_bytes: Conteúdo do arquivo em bytes.
        filename: Nome original do arquivo.
        mode: 'forense' ou 'doutrina'.
        separate: Se True, tenta separar peças processuais.
        remove_headers_footers: Se True, remove cabeçalhos/rodapés repetidos.
        detect_citations: Se True, detecta citações jurisprudenciais como blockquote (P7).
        extract_metadata: Se True, extrai metadados expandidos da peça (P8).
        extract_procedural: Se True, extrai metadados processuais (M1 v4.1).
        separate_enums: Se True, separa itens enumerados com ; (M2 v4.1).
        wrap_notes: Se True, demarca notas internas em blockquote (M3 v4.1).

    Returns:
        ConversionResult com o Markdown e metadados.
    """
    result = ConversionResult(filename=filename or file_path or "unknown", mode=mode)

    try:
        # 1. Extração
        logger.info("Extraindo texto de: %s", result.filename)
        raw_text = extract_text(file_path=file_path, file_bytes=file_bytes, filename=filename)

        if not raw_text.strip():
            result.error = "Documento vazio ou sem texto extraível."
            result.success = False
            return result

        result.stats["chars_raw"] = len(raw_text)
        result.stats["lines_raw"] = raw_text.count("\n")

        # 2. Limpeza
        logger.info("Limpando texto...")
        cleaned = clean_text(raw_text, remove_headers_footers=remove_headers_footers)
        result.stats["chars_cleaned"] = len(cleaned)

        # 3. Heurísticas jurídicas
        logger.info("Aplicando heurísticas jurídicas (modo: %s)...", mode)
        structured = apply_legal_heuristics(
            cleaned, mode=mode, detect_citations=detect_citations,
            separate_enums=separate_enums, wrap_notes=wrap_notes,
        )

        # 3a. Remover frontmatter/sumário/TOC residual do arquivo original
        structured = _strip_existing_frontmatter(structured)

        # 3b. Frontmatter YAML (com metadados expandidos P8 + processuais M1)
        frontmatter = generate_frontmatter(
            structured, filename=result.filename, extract_metadata=extract_metadata,
        )

        # M1: Metadados processuais (apenas modo forense)
        if extract_procedural and mode == "forense":
            proc_meta: dict = {}
            extract_procedural_metadata(structured, proc_meta)
            if proc_meta:
                extra_lines = []
                for key, value in proc_meta.items():
                    safe_value = str(value).replace('"', '\\"')
                    extra_lines.append(f'{key}: "{safe_value}"')
                # Insert before closing ---
                fm_lines = frontmatter.split("\n")
                fm_lines = fm_lines[:-1] + extra_lines + [fm_lines[-1]]
                frontmatter = "\n".join(fm_lines)

        # 3c. Sumário automático (P6)
        toc = generate_toc(structured)
        if toc:
            structured = frontmatter + "\n\n" + toc + "\n" + structured
        else:
            structured = frontmatter + "\n\n" + structured

        # 4. Separação de peças (opcional)
        if separate:
            logger.info("Separando peças processuais...")
            pieces = separate_pieces(structured)
            result.pieces = pieces
            result.stats["pieces_count"] = len(pieces)

            if len(pieces) > 1:
                result.markdown = format_separated_pieces(pieces)
            else:
                result.markdown = structured
        else:
            result.markdown = structured

        result.stats["chars_final"] = len(result.markdown)
        result.stats["lines_final"] = result.markdown.count("\n")
        logger.info("Conversão concluída: %s", result.filename)

    except Exception as e:
        logger.error("Erro na conversão de %s: %s", result.filename, e)
        result.success = False
        result.error = str(e)

    return result


def convert_batch(
    files: list[dict],
    mode: str = "forense",
    separate: bool = False,
    remove_headers_footers: bool = True,
    detect_citations: bool = True,
    extract_metadata: bool = False,
    extract_procedural: bool = False,
    separate_enums: bool = False,
    wrap_notes: bool = False,
) -> list[ConversionResult]:
    """Converte múltiplos documentos em lote.

    Args:
        files: Lista de dicts com 'file_bytes' e 'filename'.
        mode: Modo de heurísticas.
        separate: Se True, separa peças.
        remove_headers_footers: Se True, remove cabeçalhos/rodapés.
        detect_citations: Se True, detecta citações jurisprudenciais (P7).
        extract_metadata: Se True, extrai metadados expandidos (P8).
        extract_procedural: Se True, extrai metadados processuais (M1 v4.1).
        separate_enums: Se True, separa itens enumerados (M2 v4.1).
        wrap_notes: Se True, demarca notas internas (M3 v4.1).

    Returns:
        Lista de ConversionResult.
    """
    results = []
    total = len(files)

    for i, file_info in enumerate(files):
        logger.info("Processando arquivo %d/%d: %s", i + 1, total, file_info.get("filename", "?"))
        result = convert_document(
            file_bytes=file_info.get("file_bytes"),
            filename=file_info.get("filename"),
            mode=mode,
            separate=separate,
            remove_headers_footers=remove_headers_footers,
            detect_citations=detect_citations,
            extract_metadata=extract_metadata,
            extract_procedural=extract_procedural,
            separate_enums=separate_enums,
            wrap_notes=wrap_notes,
        )
        results.append(result)

    return results
