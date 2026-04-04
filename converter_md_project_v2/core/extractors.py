"""
Módulo de extração de texto de diferentes formatos de documentos.
Suporta: PDF, DOCX, TXT, Markdown.

Inclui:
- Extração nativa rápida via PyMuPDF
- OCR seletivo por página (apenas páginas com pouco texto nativo)
- Processamento em chunks para PDFs grandes (economia de RAM)
- Remoção de cabeçalhos/rodapés por análise de bbox
"""

import logging
import os
import re
import tempfile
from collections import Counter
from pathlib import Path

import chardet

logger = logging.getLogger(__name__)

# Padrões que identificam rodapés/cabeçalhos de escritório
_FOOTER_PATTERNS = [
    re.compile(r"CEP\s*\d{5}-?\d{3}", re.IGNORECASE),
    re.compile(r"\(\d{2}\)\s*\d[\s.\-]*\d{3,4}[\s.\-]*\d{4}"),
    re.compile(r"Página\s*\d+", re.IGNORECASE),
    re.compile(r"Pág\.\s*\d+", re.IGNORECASE),
    re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
]


def extract_text(
    file_path: str = None,
    file_bytes: bytes | None = None,
    filename: str | None = None,
    preserve_inline_formatting: bool = True,
    ocr_enabled: bool = False,
    ocr_lang: str = "por",
    ocr_threshold: int = 30,
    page_range: str | None = None,
    chunk_size: int | None = None,
) -> str:
    """Extrai texto de um arquivo com base na extensão.

    Args:
        file_path: Caminho do arquivo no disco.
        file_bytes: Conteúdo do arquivo em bytes.
        filename: Nome original do arquivo.
        preserve_inline_formatting: Se True, preserva bold/italic do DOCX como Markdown.
        ocr_enabled: Se True, aplica OCR seletivo em páginas com pouco texto nativo.
        ocr_lang: Idioma do Tesseract para OCR (padrão: por = português).
        ocr_threshold: Mínimo de chars para considerar página com texto suficiente.
        page_range: Intervalo de páginas (ex: "10-50", "1,5,10-20"). Apenas para PDF.
        chunk_size: Páginas por chunk para PDFs grandes. None = processar tudo de vez.

    Returns:
        Texto extraído como string.
    """
    if file_bytes is not None and filename:
        ext = Path(filename).suffix.lower()
    elif file_path:
        ext = Path(file_path).suffix.lower()
    else:
        raise ValueError("Forneça file_path ou (file_bytes + filename)")

    extractors = {
        ".pdf": _extract_pdf,
        ".docx": _extract_docx,
        ".txt": _extract_txt,
        ".md": _extract_md,
    }

    extractor = extractors.get(ext)
    if not extractor:
        raise ValueError(f"Formato não suportado: {ext}. Use: {', '.join(extractors.keys())}")

    try:
        kwargs = {"preserve_inline_formatting": preserve_inline_formatting}
        if ext == ".pdf":
            kwargs.update(
                ocr_enabled=ocr_enabled,
                ocr_lang=ocr_lang,
                ocr_threshold=ocr_threshold,
                page_range=page_range,
                chunk_size=chunk_size,
            )

        if file_bytes is not None:
            return extractor(file_bytes=file_bytes, file_path=None, **kwargs)
        else:
            with open(file_path, "rb") as f:
                raw = f.read()
            return extractor(file_bytes=raw, file_path=file_path, **kwargs)
    except Exception as e:
        logger.error("Erro ao extrair texto de %s: %s", filename or file_path, e)
        raise


# ============================================================
# PDF extraction with table support and footer removal via bbox
# ============================================================

def _is_footer_text(text: str) -> bool:
    """Verifica se um texto corresponde a padrões de rodapé."""
    return any(p.search(text) for p in _FOOTER_PATTERNS)


def _detect_hf_zones(doc) -> set[tuple[int, int]]:
    """Detecta zonas de cabeçalho/rodapé analisando posições y repetidas.

    Retorna set de (page_index, block_index) a remover.
    """
    total_pages = len(doc)
    if total_pages < 3:
        return set()

    # Coletar y-positions arredondadas de cada bloco de texto por página
    # key = y_rounded, value = list of (page_idx, block_idx, text)
    y_positions: dict[int, list[tuple[int, int, str]]] = {}

    for page_idx in range(total_pages):
        page = doc[page_idx]
        page_height = page.rect.height
        blocks = page.get_text("dict")["blocks"]
        for blk_idx, block in enumerate(blocks):
            if block["type"] != 0:  # apenas texto
                continue
            bbox = block["bbox"]
            y_top = bbox[1]
            y_bottom = bbox[3]

            # Só considerar zonas de margem (topo 12% ou rodapé 12% da página)
            in_header_zone = y_top < page_height * 0.12
            in_footer_zone = y_bottom > page_height * 0.88
            if not in_header_zone and not in_footer_zone:
                continue

            # Extrair texto do bloco
            block_text = ""
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    block_text += span.get("text", "")
            block_text = block_text.strip()
            if not block_text:
                continue

            # Arredondar y para agrupar blocos na mesma posição
            y_key = round(y_top / 5) * 5
            y_positions.setdefault(y_key, []).append((page_idx, blk_idx, block_text))

    # Identificar y-positions que aparecem em >=50% das páginas
    remove_set: set[tuple[int, int]] = set()
    threshold = total_pages * 0.5

    for y_key, entries in y_positions.items():
        pages_with_this_y = {e[0] for e in entries}
        if len(pages_with_this_y) >= threshold:
            for page_idx, blk_idx, text in entries:
                remove_set.add((page_idx, blk_idx))
                logger.debug("Removendo bloco hf: página %d, y=%d, text='%s'", page_idx, y_key, text[:50])

    # Também remover blocos com padrões de rodapé mesmo sem repetição de y
    for page_idx in range(total_pages):
        page = doc[page_idx]
        page_height = page.rect.height
        blocks = page.get_text("dict")["blocks"]
        for blk_idx, block in enumerate(blocks):
            if block["type"] != 0:
                continue
            bbox = block["bbox"]
            y_bottom = bbox[3]
            # Apenas em zona de rodapé
            if y_bottom <= page_height * 0.85:
                continue
            block_text = ""
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    block_text += span.get("text", "")
            block_text = block_text.strip()
            if block_text and _is_footer_text(block_text):
                remove_set.add((page_idx, blk_idx))

    return remove_set


def _table_to_markdown(table) -> str:
    """Converte uma tabela PyMuPDF para formato Markdown."""
    try:
        data = table.extract()
    except Exception:
        return ""

    if not data or not data[0]:
        return ""

    lines = []
    # Header
    header = [str(cell or "").strip().replace("\n", " ") for cell in data[0]]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join("---" for _ in header) + " |")
    # Rows
    for row in data[1:]:
        cells = [str(cell or "").strip().replace("\n", " ") for cell in row]
        # Pad se necessário
        while len(cells) < len(header):
            cells.append("")
        lines.append("| " + " | ".join(cells[:len(header)]) + " |")

    return "\n".join(lines)


def _parse_page_range(spec: str, total_pages: int) -> list[int]:
    """Converte spec como '1,5,10-20' em lista de indices (0-based)."""
    pages = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            start = max(0, int(start))
            end = min(int(end), total_pages - 1)
            pages.update(range(start, end + 1))
        else:
            p = int(part)
            if 0 <= p < total_pages:
                pages.add(p)
    return sorted(pages)


def _ocr_page(page, lang: str = "por") -> str:
    """Aplica OCR em uma página PDF via pytesseract.

    Renderiza a página como imagem em resolução moderada (200 DPI)
    para equilibrar qualidade e uso de memória.
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        logger.warning("pytesseract ou Pillow nao instalado. OCR desabilitado.")
        return ""

    try:
        # 200 DPI: bom equilíbrio entre qualidade OCR e uso de memória
        mat = page.get_pixmap(dpi=200)
        img = Image.frombytes("RGB", (mat.width, mat.height), mat.samples)
        text = pytesseract.image_to_string(img, lang=lang)
        # Liberar memória imediatamente
        del mat, img
        return text
    except Exception as e:
        logger.warning("OCR falhou na pagina: %s", e)
        return ""


def _extract_pdf(
    file_bytes: bytes,
    file_path: str | None = None,
    ocr_enabled: bool = False,
    ocr_lang: str = "por",
    ocr_threshold: int = 30,
    page_range: str | None = None,
    chunk_size: int | None = None,
    **kwargs,
) -> str:
    """Extrai texto de PDF usando PyMuPDF (fitz), com:
    - Extração de tabelas via find_tables() com fallback para texto puro
    - Remoção de cabeçalhos/rodapés via análise de bbox
    - OCR seletivo: só aplica OCR em páginas com menos de ocr_threshold chars
    - Suporte a page_range e chunk_size para PDFs grandes
    """
    import fitz

    text_parts = []
    tmp_path = None

    try:
        if file_path and os.path.exists(file_path):
            doc = fitz.open(file_path)
        else:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            tmp.write(file_bytes)
            tmp.close()
            tmp_path = tmp.name
            doc = fitz.open(tmp_path)

        total_pages = len(doc)
        logger.info("PDF com %d páginas", total_pages)

        # Determinar quais páginas processar
        if page_range:
            pages_to_process = _parse_page_range(page_range, total_pages)
            logger.info("Processando %d de %d páginas (range: %s)", len(pages_to_process), total_pages, page_range)
        else:
            pages_to_process = list(range(total_pages))

        # P3: Detectar zonas de cabeçalho/rodapé
        remove_set = _detect_hf_zones(doc)
        if remove_set:
            logger.info("Detectados %d blocos de cabeçalho/rodapé para remoção", len(remove_set))

        ocr_count = 0

        for i in pages_to_process:
            page = doc[i]
            try:
                page_parts = []

                # P1: Tentar extrair tabelas
                tables = []
                table_rects = []
                try:
                    found_tables = page.find_tables()
                    if found_tables and found_tables.tables:
                        for tbl in found_tables.tables:
                            md_table = _table_to_markdown(tbl)
                            if md_table:
                                tables.append(md_table)
                                table_rects.append(tbl.bbox)
                except Exception as e:
                    logger.debug("find_tables() falhou na página %d: %s", i + 1, e)

                # Extrair texto via dict para ter controle de bbox
                blocks = page.get_text("dict")["blocks"]
                for blk_idx, block in enumerate(blocks):
                    if block["type"] != 0:
                        continue

                    # P3: Pular blocos identificados como header/footer
                    if (i, blk_idx) in remove_set:
                        continue

                    # P1: Pular blocos que estão dentro de áreas de tabela
                    blk_bbox = block["bbox"]
                    in_table = False
                    for trect in table_rects:
                        if (blk_bbox[1] >= trect[1] - 2 and blk_bbox[3] <= trect[3] + 2
                                and blk_bbox[0] >= trect[0] - 2 and blk_bbox[2] <= trect[2] + 2):
                            in_table = True
                            break
                    if in_table:
                        continue

                    block_text = ""
                    for line in block.get("lines", []):
                        line_text = ""
                        for span in line.get("spans", []):
                            line_text += span.get("text", "")
                        if line_text.strip():
                            block_text += line_text + "\n"

                    if block_text.strip():
                        page_parts.append(block_text.strip())

                # Inserir tabelas Markdown na saída da página
                for md_table in tables:
                    page_parts.append("\n" + md_table + "\n")

                page_text = "\n".join(page_parts)

                # OCR seletivo: se a página tem pouco texto nativo, tentar OCR
                if ocr_enabled and len(page_text.strip()) < ocr_threshold:
                    logger.debug("Página %d com %d chars (< %d): aplicando OCR", i + 1, len(page_text.strip()), ocr_threshold)
                    ocr_text = _ocr_page(page, lang=ocr_lang)
                    if ocr_text.strip():
                        page_text = ocr_text
                        ocr_count += 1

                if page_text.strip():
                    text_parts.append(page_text)

            except Exception as e:
                logger.warning("Erro na página %d: %s", i + 1, e)
                try:
                    fallback = page.get_text("text")
                    if fallback.strip():
                        text_parts.append(fallback)
                except Exception:
                    text_parts.append(f"\n[Erro ao extrair página {i + 1}]\n")

        doc.close()

        if ocr_count > 0:
            logger.info("OCR aplicado em %d de %d páginas", ocr_count, len(pages_to_process))

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return "\n".join(text_parts)


# ============================================================
# DOCX extraction with table support via iter_block_items
# ============================================================

def _iter_block_items(parent):
    """Itera sobre parágrafos e tabelas na ordem em que aparecem no documento DOCX."""
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    from docx.oxml.ns import qn

    for child in parent.element.body:
        if child.tag == qn('w:p'):
            yield Paragraph(child, parent)
        elif child.tag == qn('w:tbl'):
            yield Table(child, parent)


def _docx_table_to_markdown(table) -> str:
    """Converte uma tabela python-docx para formato Markdown."""
    rows = table.rows
    if not rows:
        return ""

    lines = []
    # Header (primeira linha)
    header_cells = [cell.text.strip().replace("\n", " ") for cell in rows[0].cells]
    lines.append("| " + " | ".join(header_cells) + " |")
    lines.append("| " + " | ".join("---" for _ in header_cells) + " |")

    # Data rows
    for row in list(rows)[1:]:
        cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
        while len(cells) < len(header_cells):
            cells.append("")
        lines.append("| " + " | ".join(cells[:len(header_cells)]) + " |")

    return "\n".join(lines)


def _paragraph_to_markdown(paragraph, preserve_formatting: bool = True) -> str:
    """Converte um parágrafo DOCX para Markdown preservando bold/italic.

    Itera sobre runs do parágrafo e envolve trechos em **...** ou *...*.
    """
    if not preserve_formatting:
        return paragraph.text.strip()

    parts = []
    for run in paragraph.runs:
        text = run.text
        if not text:
            continue
        bold = run.bold
        italic = run.italic
        if bold and italic:
            parts.append(f"***{text}***")
        elif bold:
            parts.append(f"**{text}**")
        elif italic:
            parts.append(f"*{text}*")
        else:
            parts.append(text)

    result = "".join(parts).strip()
    # Limpar marcadores vazios: ****, **** etc.
    result = re.sub(r"\*{2,3}\s*\*{2,3}", "", result)
    # Mesclar marcadores adjacentes: **texto****outro** → **textooutro**
    result = re.sub(r"\*\*\*\*\*\*", "", result)  # ****** vazio
    result = re.sub(r"\*\*\*\*", "", result)        # **** entre bolds adjacentes
    result = re.sub(r"\*\*\s+\*\*", " ", result)   # ** ** espaço entre bolds
    return result


def _extract_docx(
    file_bytes: bytes,
    file_path: str | None = None,
    preserve_inline_formatting: bool = True,
    **kwargs,
) -> str:
    """Extrai texto de DOCX preservando estrutura de parágrafos, tabelas e formatação inline."""
    import io

    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    doc = Document(io.BytesIO(file_bytes))
    parts = []

    for block in _iter_block_items(doc):
        if isinstance(block, Paragraph):
            text = _paragraph_to_markdown(block, preserve_inline_formatting)
            if not text:
                continue

            style_name = (block.style.name or "").lower() if block.style else ""

            if "heading 1" in style_name:
                # Strip inline formatting from headings (redundant with #)
                plain = block.text.strip()
                parts.append(f"# {plain}")
            elif "heading 2" in style_name:
                plain = block.text.strip()
                parts.append(f"## {plain}")
            elif "heading 3" in style_name:
                plain = block.text.strip()
                parts.append(f"### {plain}")
            elif "heading 4" in style_name:
                plain = block.text.strip()
                parts.append(f"#### {plain}")
            elif "title" in style_name:
                plain = block.text.strip()
                parts.append(f"# {plain}")
            else:
                parts.append(text)

        elif isinstance(block, Table):
            md_table = _docx_table_to_markdown(block)
            if md_table:
                parts.append("")
                parts.append(md_table)
                parts.append("")

    return "\n".join(parts)


def _extract_txt(file_bytes: bytes, file_path: str | None = None, **kwargs) -> str:
    """Extrai texto de arquivo TXT detectando encoding automaticamente."""
    detected = chardet.detect(file_bytes)
    encoding = detected.get("encoding", "utf-8") or "utf-8"

    try:
        return file_bytes.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        logger.warning("Fallback de encoding: %s -> utf-8", encoding)
        return file_bytes.decode("utf-8", errors="replace")


def _extract_md(file_bytes: bytes, file_path: str | None = None, **kwargs) -> str:
    """Retorna conteúdo Markdown como está (já é o formato alvo)."""
    return _extract_txt(file_bytes, file_path)
