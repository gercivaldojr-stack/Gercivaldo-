"""
Pipeline principal de conversão de documentos jurídicos para Markdown.
Orquestra extração, limpeza, heurísticas e separação de peças.
"""

import logging
import re
from dataclasses import dataclass, field

from .cleaning import clean_text
from .extractors import extract_text
from .legal_heuristics import apply_legal_heuristics, generate_toc
from .metadata import extract_procedural_metadata, generate_frontmatter, _strip_md_formatting
from .piece_separator import format_separated_pieces, separate_pieces

logger = logging.getLogger(__name__)

MIN_CONSECUTIVE_HEADINGS_FOR_TOC = 5


def _strip_existing_frontmatter(text: str) -> str:
    """Remove frontmatter YAML, sumário embutido e lixo residual do original.

    Remove:
    - Blocos entre --- no início do texto (frontmatter YAML padrão)
    - Linhas de YAML inline soltas (titulo:, data:, status:, etc.)
    - Blocos ## Sumário / ## Índice seguidos de listas - [...] até linha em branco
    - Blocos de TOC malformado: 3+ linhas consecutivas com "- [" sem "](#"
    """
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

    # Pass extra: detectar bloco de TOC residual (N+ headings consecutivos
    # sem corpo). Preserva o ÚLTIMO heading antes do body (é o real).
    cleaned = []
    heading_run = 0
    heading_start = -1
    last_heading_start = -1
    for line in result:
        stripped = line.strip()
        is_heading = bool(re.match(r'^#{1,6}\s+', stripped))
        is_blank = not stripped

        if is_heading:
            if heading_run == 0:
                heading_start = len(cleaned)
            last_heading_start = len(cleaned)
            heading_run += 1
            cleaned.append(line)
        elif is_blank and heading_run > 0:
            cleaned.append(line)
        else:
            if heading_run >= MIN_CONSECUTIVE_HEADINGS_FOR_TOC:
                # Remove os N-1 primeiros headings (TOC), preserva último
                # que é o heading real seguido de body
                cleaned = cleaned[:heading_start] + cleaned[last_heading_start:]
                logger.info(
                    "Removido bloco TOC residual (%d headings, "
                    "preservado o último)",
                    heading_run - 1,
                )
            heading_run = 0
            cleaned.append(line)

    if heading_run >= MIN_CONSECUTIVE_HEADINGS_FOR_TOC:
        cleaned = cleaned[:heading_start]

    return "\n".join(cleaned)


@dataclass
class ConversionResult:
    """Resultado da conversão de um documento."""
    markdown: str = ""
    html: str | None = None
    docx_bytes: bytes | None = None
    pieces: list[dict] = field(default_factory=list)
    filename: str = ""
    mode: str = "forense"
    output_format: str = "md"
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
    preserve_inline_formatting: bool = True,
    generate_toc_flag: bool = False,
    ocr_enabled: bool = False,
    ocr_lang: str = "por",
    ocr_threshold: int = 30,
    page_range: str | None = None,
    chunk_size: int | None = None,
    detect_columns: bool = True,
    output_format: str = "md",
    max_workers: int | None = None,
    ocr_cache_enabled: bool = False,
    ocr_cache_dir: str | None = None,
    rag_optimize: bool = False,
    strip_footnotes_flag: bool = True,
    strip_artifacts_flag: bool = True,
    strip_references_flag: bool = True,
) -> ConversionResult:
    """Converte um documento jurídico para Markdown estruturado.

    Args:
        file_path: Caminho do arquivo no disco.
        file_bytes: Conteúdo do arquivo em bytes.
        filename: Nome original do arquivo.
        mode: 'forense' ou 'doutrina'.
        separate: Se True, tenta separar peças processuais.
        remove_headers_footers: Se True, remove cabeçalhos/rodapés repetidos.
        detect_citations: Se True, detecta citações jurisprudenciais.
        extract_metadata: Se True, extrai metadados expandidos da peça.
        extract_procedural: Se True, extrai metadados processuais.
        separate_enums: Se True, separa itens enumerados com ;.
        wrap_notes: Se True, demarca notas internas em blockquote.
        ocr_enabled: Se True, aplica OCR seletivo por página.
        ocr_lang: Idioma do Tesseract (padrão: por).
        ocr_threshold: Mínimo de chars para considerar página com texto.
        page_range: Páginas 1-based (ex: "1-50"). Apenas PDF.
        chunk_size: Páginas por chunk. None = tudo de uma vez.
        detect_columns: Se True, detecta PDFs com 2 colunas.
        output_format: "md", "html" ou "docx".

    Returns:
        ConversionResult com o Markdown e opcionalmente HTML/DOCX.
    """
    result = ConversionResult(
        filename=filename or file_path or "unknown",
        mode=mode,
        output_format=output_format,
    )

    try:
        # 1. Extração
        logger.info("Extraindo texto de: %s", result.filename)
        raw_text = extract_text(
            file_path=file_path, file_bytes=file_bytes, filename=filename,
            preserve_inline_formatting=preserve_inline_formatting,
            ocr_enabled=ocr_enabled,
            ocr_lang=ocr_lang,
            ocr_threshold=ocr_threshold,
            page_range=page_range,
            chunk_size=chunk_size,
            detect_columns=detect_columns,
            max_workers=max_workers,
            ocr_cache_enabled=ocr_cache_enabled,
            ocr_cache_dir=ocr_cache_dir,
            stats=result.stats,
        )

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

        # 3a-TABLE. Normalização de tabelas (merged cells, colunas duplicadas)
        from .table_normalizer import normalize_tables
        structured = normalize_tables(structured)

        # 3a-HEAD. Validação e normalização de hierarquia de headings
        from .heading_validator import normalize_heading_hierarchy
        structured = normalize_heading_hierarchy(structured)

        # 3a-RAG. Otimização semântica para bases RAG (opt-in)
        if rag_optimize:
            from .rag_optimizer import optimize_for_rag
            structured = optimize_for_rag(
                structured, filename=result.filename,
            )
            logger.info("Otimização RAG aplicada")

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
                    safe_value = _strip_md_formatting(str(value)).replace('"', '\\"')
                    extra_lines.append(f'{key}: "{safe_value}"')
                # Insert before closing ---
                fm_lines = frontmatter.split("\n")
                fm_lines = fm_lines[:-1] + extra_lines + [fm_lines[-1]]
                frontmatter = "\n".join(fm_lines)

        # D10-fix: inserir H1 se o doc não possui heading #
        has_h1 = any(
            ln.strip().startswith('# ')
            and not ln.strip().startswith('## ')
            for ln in structured.split('\n')
        )
        if not has_h1:
            # Extrair título do frontmatter
            titulo_m = re.search(r'titulo:\s*"(.+?)"', frontmatter)
            if titulo_m:
                h1_line = f"# {titulo_m.group(1)}\n\n"
            else:
                h1_line = ""
        else:
            h1_line = ""

        # 3c. Sumário automático (apenas se habilitado)
        if generate_toc_flag:
            toc = generate_toc(structured)
            if toc:
                structured = (
                    frontmatter + "\n\n" + h1_line + toc + "\n" + structured
                )
            else:
                structured = frontmatter + "\n\n" + h1_line + structured
        else:
            structured = frontmatter + "\n\n" + h1_line + structured

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

        # 4b. Limpeza final de artefatos (metadados espúrios, headers/footers)
        from .artifact_cleaner import clean_artifacts
        result.markdown = clean_artifacts(result.markdown)

        # 4c. Reconciliação de footnotes órfãs (defect-3)
        from .footnote_relocator import relocate_orphan_footnotes
        result.markdown = relocate_orphan_footnotes(result.markdown)

        # 4d. Remoção seletiva de conteúdo (content_stripper)
        from .content_stripper import (
            fix_malformed_urls,
            strip_conversion_artifacts,
            strip_footnotes,
            strip_inline_biblio_references,
            strip_reference_blocks,
            strip_ui_text,
        )
        # Sempre aplicar: URL fix, UI text, biblio inline
        result.markdown = fix_malformed_urls(result.markdown)
        result.markdown = strip_ui_text(result.markdown)
        if strip_references_flag:
            result.markdown = strip_inline_biblio_references(result.markdown)
        if strip_footnotes_flag:
            result.markdown = strip_footnotes(result.markdown)
        if strip_artifacts_flag:
            result.markdown = strip_conversion_artifacts(result.markdown)
        if strip_references_flag:
            result.markdown = strip_reference_blocks(result.markdown)

        # 4e. Polimento final de Markdown (md_polish)
        from .md_polish import polish_markdown
        result.markdown = polish_markdown(result.markdown)

        result.stats["chars_final"] = len(result.markdown)
        result.stats["lines_final"] = result.markdown.count("\n")

        # 5. Exportação para formatos alternativos
        if output_format == "html":
            from .html_exporter import markdown_to_html
            result.html = markdown_to_html(result.markdown)
            logger.info("HTML gerado: %d chars", len(result.html))
        elif output_format == "docx":
            from .docx_exporter import markdown_to_docx
            result.docx_bytes = markdown_to_docx(result.markdown)
            logger.info("DOCX gerado: %d bytes", len(result.docx_bytes))

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
    preserve_inline_formatting: bool = True,
    generate_toc_flag: bool = False,
    ocr_enabled: bool = False,
    ocr_lang: str = "por",
    ocr_threshold: int = 30,
    page_range: str | None = None,
    chunk_size: int | None = None,
    detect_columns: bool = True,
    output_format: str = "md",
    max_workers: int | None = None,
    rag_optimize: bool = False,
    strip_footnotes_flag: bool = True,
    strip_artifacts_flag: bool = True,
    strip_references_flag: bool = True,
) -> list[ConversionResult]:
    """Converte múltiplos documentos em lote.

    Args:
        files: Lista de dicts com 'file_bytes' e 'filename'.
        max_workers: Workers paralelos. None/0 = sequencial.
        Demais args: mesmos de convert_document.

    Returns:
        Lista de ConversionResult.
    """
    if max_workers and max_workers != 1 and len(files) > 1:
        from .parallel import convert_batch_parallel
        return convert_batch_parallel(
            files=files,
            max_workers=max_workers,
            mode=mode,
            separate=separate,
            remove_headers_footers=remove_headers_footers,
            detect_citations=detect_citations,
            extract_metadata=extract_metadata,
            extract_procedural=extract_procedural,
            separate_enums=separate_enums,
            wrap_notes=wrap_notes,
            preserve_inline_formatting=preserve_inline_formatting,
            generate_toc_flag=generate_toc_flag,
            ocr_enabled=ocr_enabled,
            ocr_lang=ocr_lang,
            ocr_threshold=ocr_threshold,
            page_range=page_range,
            chunk_size=chunk_size,
            detect_columns=detect_columns,
            output_format=output_format,
            rag_optimize=rag_optimize,
            strip_footnotes_flag=strip_footnotes_flag,
            strip_artifacts_flag=strip_artifacts_flag,
            strip_references_flag=strip_references_flag,
        )

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
            preserve_inline_formatting=preserve_inline_formatting,
            generate_toc_flag=generate_toc_flag,
            ocr_enabled=ocr_enabled,
            ocr_lang=ocr_lang,
            ocr_threshold=ocr_threshold,
            page_range=page_range,
            chunk_size=chunk_size,
            detect_columns=detect_columns,
            output_format=output_format,
            max_workers=max_workers,
            rag_optimize=rag_optimize,
            strip_footnotes_flag=strip_footnotes_flag,
            strip_artifacts_flag=strip_artifacts_flag,
            strip_references_flag=strip_references_flag,
        )
        results.append(result)

    return results
