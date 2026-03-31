"""Testes para o pipeline principal."""

import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.pipeline import convert_batch, convert_document


class TestConvertDocument:
    def test_txt_conversion(self):
        content = "DOS FATOS\n\nO autor alega que...\n\nDOS PEDIDOS\n\nRequer-se a condenação."
        result = convert_document(
            file_bytes=content.encode("utf-8"),
            filename="peticao.txt",
            mode="forense",
        )
        assert result.success
        # First heading promoted to H1 by hierarchy fix; second stays H2
        assert "DOS FATOS" in result.markdown
        assert "DOS PEDIDOS" in result.markdown

    def test_txt_doutrina(self):
        content = "CAPÍTULO I - Introdução\n\nTexto introdutório.\n\n1.1 Conceitos\n\nDefinições."
        result = convert_document(
            file_bytes=content.encode("utf-8"),
            filename="doutrina.txt",
            mode="doutrina",
        )
        assert result.success
        assert "# CAPÍTULO I" in result.markdown
        assert "### 1.1" in result.markdown

    def test_empty_document(self):
        result = convert_document(
            file_bytes=b"",
            filename="vazio.txt",
        )
        assert not result.success
        assert "vazio" in result.error.lower() or "empty" in result.error.lower()

    def test_piece_separation(self):
        content = (
            "PETIÇÃO INICIAL\n\nConteúdo da petição.\n\n"
            "CONTESTAÇÃO\n\nConteúdo da contestação."
        )
        result = convert_document(
            file_bytes=content.encode("utf-8"),
            filename="autos.txt",
            mode="forense",
            separate=True,
        )
        assert result.success
        assert len(result.pieces) >= 2

    def test_docx_conversion(self):
        from docx import Document

        doc = Document()
        doc.add_heading("Sentença", level=1)
        doc.add_paragraph("O juiz decide...")

        buffer = io.BytesIO()
        doc.save(buffer)

        result = convert_document(
            file_bytes=buffer.getvalue(),
            filename="sentenca.docx",
            mode="forense",
        )
        assert result.success
        assert "Sentença" in result.markdown

    def test_stats_populated(self):
        content = "Texto simples para teste de estatísticas."
        result = convert_document(
            file_bytes=content.encode("utf-8"),
            filename="stats.txt",
        )
        assert result.stats.get("chars_raw", 0) > 0
        assert result.stats.get("chars_final", 0) > 0

    def test_frontmatter_present(self):
        """Bug 1: Output deve conter frontmatter YAML."""
        content = "PETIÇÃO INICIAL\n\nDOS FATOS\n\nO autor alega."
        result = convert_document(
            file_bytes=content.encode("utf-8"),
            filename="peticao.txt",
            mode="forense",
        )
        assert result.success
        assert result.markdown.startswith("---\n")
        assert "\n---\n" in result.markdown
        assert "titulo:" in result.markdown

    def test_docx_double_spaces_normalized(self):
        """Bug 4: Espaços duplos em DOCX devem ser normalizados."""
        from docx import Document

        doc = Document()
        doc.add_heading("DA  VARA  CÍVEL", level=2)
        doc.add_paragraph("Texto  com  espaços  duplos.")

        buffer = io.BytesIO()
        doc.save(buffer)

        result = convert_document(
            file_bytes=buffer.getvalue(),
            filename="test_spaces.docx",
            mode="forense",
        )
        assert result.success
        assert "DA  VARA" not in result.markdown
        assert "DA VARA" in result.markdown
        assert "espaços  duplos" not in result.markdown


class TestConvertBatch:
    def test_batch_conversion(self):
        files = [
            {"file_bytes": b"DOS FATOS\n\nTexto 1.", "filename": "doc1.txt"},
            {"file_bytes": b"DOS PEDIDOS\n\nTexto 2.", "filename": "doc2.txt"},
        ]
        results = convert_batch(files, mode="forense")
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_batch_with_error(self):
        files = [
            {"file_bytes": b"Texto ok.", "filename": "ok.txt"},
            {"file_bytes": b"data", "filename": "bad.xyz"},
        ]
        results = convert_batch(files, mode="forense")
        assert len(results) == 2
        assert results[0].success
        assert not results[1].success
