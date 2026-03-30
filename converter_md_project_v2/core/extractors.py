"""
Módulo de extração de texto de diferentes formatos de documentos.
Suporta: PDF, DOCX, TXT, Markdown.
"""

import logging
import os
import tempfile
from pathlib import Path

import chardet

logger = logging.getLogger(__name__)


def extract_text(file_path: str, file_bytes: bytes | None = None, filename: str | None = None) -> str:
    """Extrai texto de um arquivo com base na extensão.

    Args:
        file_path: Caminho do arquivo no disco (pode ser None se file_bytes for fornecido).
        file_bytes: Conteúdo do arquivo em bytes (para uso via Streamlit upload).
        filename: Nome original do arquivo (usado para detectar extensão quando file_bytes é fornecido).

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
        if file_bytes is not None:
            return extractor(file_bytes=file_bytes, file_path=None)
        else:
            with open(file_path, "rb") as f:
                raw = f.read()
            return extractor(file_bytes=raw, file_path=file_path)
    except Exception as e:
        logger.error("Erro ao extrair texto de %s: %s", filename or file_path, e)
        raise


def _extract_pdf(file_bytes: bytes, file_path: str | None = None) -> str:
    """Extrai texto de PDF usando PyMuPDF (fitz), com tratamento para PDFs grandes."""
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

        for i, page in enumerate(doc):
            try:
                page_text = page.get_text("text")
                if page_text.strip():
                    text_parts.append(page_text)
            except Exception as e:
                logger.warning("Erro na página %d: %s", i + 1, e)
                text_parts.append(f"\n[Erro ao extrair página {i + 1}]\n")

        doc.close()
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return "\n".join(text_parts)


def _extract_docx(file_bytes: bytes, file_path: str | None = None) -> str:
    """Extrai texto de DOCX preservando estrutura de parágrafos."""
    import io

    from docx import Document

    doc = Document(io.BytesIO(file_bytes))
    parts = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        style_name = (para.style.name or "").lower() if para.style else ""

        if "heading 1" in style_name:
            parts.append(f"# {text}")
        elif "heading 2" in style_name:
            parts.append(f"## {text}")
        elif "heading 3" in style_name:
            parts.append(f"### {text}")
        elif "heading 4" in style_name:
            parts.append(f"#### {text}")
        elif "title" in style_name:
            parts.append(f"# {text}")
        else:
            parts.append(text)

    return "\n\n".join(parts)


def _extract_txt(file_bytes: bytes, file_path: str | None = None) -> str:
    """Extrai texto de arquivo TXT detectando encoding automaticamente."""
    detected = chardet.detect(file_bytes)
    encoding = detected.get("encoding", "utf-8") or "utf-8"

    try:
        return file_bytes.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        logger.warning("Fallback de encoding: %s -> utf-8", encoding)
        return file_bytes.decode("utf-8", errors="replace")


def _extract_md(file_bytes: bytes, file_path: str | None = None) -> str:
    """Retorna conteúdo Markdown como está (já é o formato alvo)."""
    return _extract_txt(file_bytes, file_path)
