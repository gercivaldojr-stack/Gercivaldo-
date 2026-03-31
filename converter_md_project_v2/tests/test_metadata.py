"""Testes para o módulo de geração de frontmatter YAML."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.metadata import generate_frontmatter


class TestGenerateFrontmatter:
    def test_basic_frontmatter_structure(self):
        """Frontmatter deve ter delimitadores --- no início e fim."""
        text = "Título do documento\n\nConteúdo aqui."
        result = generate_frontmatter(text, filename="doc.pdf")
        assert result.startswith("---\n")
        assert result.endswith("\n---")

    def test_extracts_title_from_first_line(self):
        text = "PETIÇÃO INICIAL DE INDENIZAÇÃO\n\nConteúdo."
        result = generate_frontmatter(text)
        assert "titulo:" in result
        assert "PETIÇÃO INICIAL" in result

    def test_fallback_title_to_filename(self):
        text = "\n\n\n"
        result = generate_frontmatter(text, filename="meu_documento.pdf")
        assert "titulo:" in result
        assert "meu_documento" in result

    def test_extracts_proad_number(self):
        text = "Título\n\nPROAD nº 123.456/2024\n\nConteúdo."
        result = generate_frontmatter(text)
        assert "proad:" in result
        assert "123.456/2024" in result

    def test_extracts_date_long_format(self):
        text = "Título\n\nBrasília, 15 de março de 2024.\n\nConteúdo."
        result = generate_frontmatter(text)
        assert "data:" in result
        assert "15 de março de 2024" in result

    def test_extracts_date_short_format(self):
        text = "Título\n\n15/03/2024\n\nConteúdo."
        result = generate_frontmatter(text)
        assert "data:" in result
        assert "15/03/2024" in result

    def test_default_status_vigente(self):
        text = "Título\n\nConteúdo."
        result = generate_frontmatter(text)
        assert 'status: "vigente"' in result

    def test_convertido_em_present(self):
        text = "Título\n\nConteúdo."
        result = generate_frontmatter(text)
        assert "convertido_em:" in result

    def test_handles_empty_text(self):
        result = generate_frontmatter("", filename="vazio.pdf")
        assert result.startswith("---\n")
        assert "titulo:" in result

    def test_strips_heading_markers_from_title(self):
        text = "## DOS FATOS\n\nO autor alega que..."
        result = generate_frontmatter(text)
        assert "DOS FATOS" in result
        assert 'titulo: "##' not in result

    def test_no_proad_when_absent(self):
        text = "Título simples\n\nConteúdo sem número de processo."
        result = generate_frontmatter(text)
        assert "proad:" not in result
