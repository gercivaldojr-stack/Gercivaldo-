"""
Pipeline principal de conversão de documentos jurídicos para Markdown.
Orquestra extração, limpeza, heurísticas e separação de peças.
"""

import logging
from dataclasses import dataclass, field

from .cleaning import clean_text
from .extractors import extract_text
from .legal_heuristics import apply_legal_heuristics, generate_toc
from .piece_separator import format_separated_pieces, separate_pieces
from .metadata import generate_frontmatter

logger = logging.getLogger(__name__)


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
    extract_full_metadata: bool = True,
    separate_items: bool = True,
    mark_internal_notes: bool = True,
) -> ConversionResult:
    """Converte um documento jurídico para Markdown estruturado.

    Args:
        file_path: Caminho do arquivo no disco.
        file_bytes: Conteúdo do arquivo em bytes.
        filename: Nome original do arquivo.
        mode: 'forense' ou 'doutrina'.
        separate: Se True, tenta separar peças processuais.
        remove_headers_footers: Se True, remove cabeçalhos/rodapés repetidos.
        extract_full_metadata: Se True (modo forense), extrai autor, réu, comarca, etc.
        separate_items: Se True (modo forense), separa itens enumerados.
        mark_internal_notes: Se True (modo forense), demarca notas internas.

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

        # 3. Heurísticas jurídicas (inclui M2 e M3)
        logger.info("Aplicando heurísticas jurídicas (modo: %s)...", mode)
        structured = apply_legal_heuristics(
            cleaned,
            mode=mode,
            separate_items=separate_items,
            mark_internal_notes=mark_internal_notes,
        )

        # 3b. Frontmatter YAML (inclui M1)
        frontmatter = generate_frontmatter(
            structured,
            filename=result.filename,
            mode=mode,
            extract_full_metadata=extract_full_metadata,
        )

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
    extract_full_metadata: bool = True,
    separate_items: bool = True,
    mark_internal_notes: bool = True,
) -> list[ConversionResult]:
    """Converte múltiplos documentos em lote.

    Args:
        files: Lista de dicts com 'file_bytes' e 'filename'.
        mode: Modo de heurísticas.
        separate: Se True, separa peças.
        remove_headers_footers: Se True, remove cabeçalhos/rodapés.
        extract_full_metadata: Se True, extrai metadados processuais.
        separate_items: Se True, separa itens enumerados.
        mark_internal_notes: Se True, demarca notas internas.

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
            extract_full_metadata=extract_full_metadata,
            separate_items=separate_items,
            mark_internal_notes=mark_internal_notes,
        )
        results.append(result)

    return results
