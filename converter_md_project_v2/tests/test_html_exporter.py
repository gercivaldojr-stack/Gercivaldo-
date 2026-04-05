"""Testes para exportação HTML."""

from core.html_exporter import _strip_frontmatter, markdown_to_html


class TestStripFrontmatter:
    def test_removes_yaml(self):
        text = "---\ntitulo: Test\n---\n# Heading"
        result = _strip_frontmatter(text)
        assert "# Heading" in result
        assert "titulo:" not in result

    def test_no_frontmatter(self):
        text = "# Heading\nTexto."
        assert _strip_frontmatter(text) == text


class TestMarkdownToHtml:
    def test_basic_conversion(self):
        md = "# Titulo\n\nParagrafo de texto."
        html = markdown_to_html(md)
        assert "<h1" in html
        assert "Titulo" in html
        assert "Paragrafo de texto" in html

    def test_headings_preserved(self):
        md = "# H1\n\n## H2\n\n### H3"
        html = markdown_to_html(md)
        assert "<h1" in html
        assert "<h2" in html
        assert "<h3" in html

    def test_tables(self):
        md = "| Col1 | Col2 |\n| --- | --- |\n| A | B |"
        html = markdown_to_html(md)
        assert "<table>" in html
        assert "<th>" in html

    def test_blockquotes(self):
        md = "> Citacao juridica importante."
        html = markdown_to_html(md)
        assert "<blockquote>" in html

    def test_frontmatter_removed(self):
        md = "---\ntitulo: Test\nstatus: vigente\n---\n\n# Doc"
        html = markdown_to_html(md)
        assert "titulo:" not in html
        assert "status:" not in html

    def test_title_in_html(self):
        md = "# Meu Documento"
        html = markdown_to_html(md, title="Titulo Custom")
        assert "<title>Titulo Custom</title>" in html

    def test_auto_title_from_h1(self):
        md = "# Peticao Inicial"
        html = markdown_to_html(md)
        assert "Peticao Inicial" in html

    def test_css_present(self):
        html = markdown_to_html("Texto")
        assert "<style>" in html
        assert "blockquote" in html
