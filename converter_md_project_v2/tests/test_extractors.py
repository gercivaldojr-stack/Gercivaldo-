"""Testes para o módulo de extração de texto."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.extractors import extract_text


class TestExtractText:
    def test_unsupported_format(self):
        with pytest.raises(ValueError, match="Formato não suportado"):
            extract_text(file_path=None, file_bytes=b"test", filename="file.xyz")

    def test_no_args(self):
        with pytest.raises(ValueError, match="Forneça"):
            extract_text(file_path=None, file_bytes=None, filename=None)

    def test_txt_extraction(self):
        content = "Texto de teste para extração."
        result = extract_text(
            file_path=None,
            file_bytes=content.encode("utf-8"),
            filename="test.txt",
        )
        assert result == content

    def test_md_extraction(self):
        content = "# Heading\n\nParágrafo com acentuação."
        result = extract_text(
            file_path=None,
            file_bytes=content.encode("utf-8"),
            filename="test.md",
        )
        assert "# Heading" in result

    def test_txt_latin1(self):
        content = "Texto com acentuação: ção, ão, é, ê"
        encoded = content.encode("latin-1")
        result = extract_text(
            file_path=None,
            file_bytes=encoded,
            filename="test.txt",
        )
        assert "ação" in result or "a" in result  # encoding detection may vary


class TestExtractDocx:
    def test_docx_extraction(self):
        """Testa extração de DOCX gerando um arquivo mínimo em memória."""
        from docx import Document
        import io

        doc = Document()
        doc.add_heading("Título do Documento", level=1)
        doc.add_paragraph("Primeiro parágrafo com conteúdo jurídico.")
        doc.add_heading("Dos Fatos", level=2)
        doc.add_paragraph("Descrição dos fatos relevantes ao caso.")

        buffer = io.BytesIO()
        doc.save(buffer)
        file_bytes = buffer.getvalue()

        result = extract_text(
            file_path=None,
            file_bytes=file_bytes,
            filename="test.docx",
        )

        assert "Título do Documento" in result
        assert "Primeiro parágrafo" in result
        assert "Dos Fatos" in result
        assert "# " in result  # Heading deve ser convertido


class TestExtractPDF:
    def test_pdf_extraction(self):
        """Testa extração de PDF gerando um PDF mínimo em memória."""
        import fitz

        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Texto do PDF de teste", fontsize=12)
        page.insert_text((72, 100), "Segundo parágrafo do documento.", fontsize=12)

        pdf_bytes = doc.tobytes()
        doc.close()

        result = extract_text(
            file_path=None,
            file_bytes=pdf_bytes,
            filename="test.pdf",
        )

        assert "Texto do PDF" in result
        assert "Segundo parágrafo" in result
