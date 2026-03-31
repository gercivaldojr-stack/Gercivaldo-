"""
Pipeline principal de conversão de documentos jurídicos para Markdown.
Orquestra extração, limpeza, heurísticas e separação de peças.
"""

import logging
from dataclasses import dataclass, field

from .cleaning import clean_text
from .extractors import extract_text
from .legal_heuristics import (
    apply_legal_heuristics,
    _fix_heading_hierarchy,
    _format_enumeration_as_list,
)
from .metadata import generate_frontmatter
from .piece_separator import format_separated_pieces, separate_pieces

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
) -> ConversionResult:
    """Converte um documento jurídico para Markdown estruturado.

    Args:
        file_path: Caminho do arquivo no disco.
        file_bytes: Conteúdo do arquivo em bytes.
        filename: Nome original do arquivo.
        mode: 'forense' ou 'doutrina'.
        separate: Se True, tenta separar peças processuais.
        remove_headers_footers: Se True, remove cabeçalhos/rodapés repetidos.

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
        structured = apply_legal_heuristics(cleaned, mode=mode)

        # 3b. Pós-processamento forense
        if mode == "forense":
            structured = _fix_heading_hierarchy(structured)
            structured = _format_enumeration_as_list(structured)

        # 4. Separação de peças (opcional) — antes do frontmatter
        if separate:
            logger.info("Separando peças processuais...")
            pieces = separate_pieces(structured)
            result.pieces = pieces
            result.stats["pieces_count"] = len(pieces)

            if len(pieces) > 1:
                final_content = format_separated_pieces(pieces)
            else:
                final_content = structured
        else:
            final_content = structured

        # 5. Frontmatter YAML — prepend ao resultado final
        frontmatter = generate_frontmatter(structured, filename=result.filename)
        result.markdown = frontmatter + "\n\n" + final_content

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
) -> list[ConversionResult]:
    """Converte múltiplos documentos em lote.

    Args:
        files: Lista de dicts com 'file_bytes' e 'filename'.
        mode: Modo de heurísticas.
        separate: Se True, separa peças.
        remove_headers_footers: Se True, remove cabeçalhos/rodapés.

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
        )
        results.append(result)

    return results
