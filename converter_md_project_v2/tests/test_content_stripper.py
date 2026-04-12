"""Testes para o módulo content_stripper."""

from core.content_stripper import (
    strip_conversion_artifacts,
    strip_footnotes,
    strip_reference_blocks,
)


class TestStripFootnotes:
    def test_removes_inline_refs(self):
        text = "Texto com nota[^1] e outra[^2]."
        result = strip_footnotes(text)
        assert "[^1]" not in result
        assert "[^2]" not in result
        assert "Texto com nota e outra." in result

    def test_removes_definitions(self):
        text = "Texto.\n\n[^1]: Definição da nota."
        result = strip_footnotes(text)
        assert "[^1]:" not in result
        assert "Definição da nota" not in result

    def test_removes_callout_nota(self):
        text = (
            "Texto.\n\n"
            "> [!NOTE]\n"
            "> **Nota:** Conteúdo da nota.\n\n"
            "Mais texto."
        )
        result = strip_footnotes(text)
        assert "**Nota:**" not in result
        assert "Mais texto" in result

    def test_removes_trailing_separator(self):
        text = "Texto.\n\n---\n[^1]: Nota.\n"
        result = strip_footnotes(text)
        assert "---" not in result.strip()

    def test_keeps_text_without_footnotes(self):
        text = "Texto simples sem notas."
        result = strip_footnotes(text)
        assert result.strip() == text

    def test_pipeline_integration(self):
        from core.pipeline import convert_document
        result = convert_document(
            file_bytes=b"Texto com nota (1).\n1. Ref.\n",
            filename="test.txt",
            strip_footnotes_flag=True,
        )
        assert result.success


class TestStripConversionArtifacts:
    def test_removes_page_numbers(self):
        text = "Texto.\n\n42\n\nMais texto."
        result = strip_conversion_artifacts(text)
        assert "42" not in result
        assert "Texto." in result
        assert "Mais texto." in result

    def test_removes_page_marker(self):
        text = "Texto.\n--- Página 5 ---\nMais."
        result = strip_conversion_artifacts(text)
        assert "Página 5" not in result

    def test_removes_cs_header(self):
        text = "CS – CIVIL I 2025.2 | 42\nConteúdo."
        result = strip_conversion_artifacts(text)
        assert "CS –" not in result
        assert "Conteúdo" in result

    def test_removes_resumo_block(self):
        text = "*Resumo: Bloco. Palavras-chave: tag.*"
        result = strip_conversion_artifacts(text)
        assert "Resumo:" not in result

    def test_removes_empty_table_lines(self):
        text = "Texto.\n|   |   |\nMais."
        result = strip_conversion_artifacts(text)
        assert "|   |   |" not in result

    def test_keeps_real_content(self):
        text = "## Capítulo 1\n\nO Art. 50 do CC dispõe sobre o tema."
        result = strip_conversion_artifacts(text)
        assert "Art. 50" in result
        assert "## Capítulo 1" in result


class TestStripReferenceBlocks:
    def test_removes_referencias(self):
        text = (
            "## Capítulo 1\n\n"
            "Conteúdo principal.\n\n"
            "## Referências\n\n"
            "TARTUCE, Flávio. Manual.\n"
            "GONÇALVES, Carlos. Direito Civil.\n"
        )
        result = strip_reference_blocks(text)
        assert "Conteúdo principal" in result
        assert "TARTUCE" not in result
        assert "GONÇALVES" not in result
        assert "## Referências" not in result

    def test_removes_bibliografia(self):
        text = (
            "## Conclusão\n\nTexto final.\n\n"
            "## Bibliografia\n\nREALE, Miguel. Lições.\n"
        )
        result = strip_reference_blocks(text)
        assert "Texto final" in result
        assert "REALE" not in result

    def test_removes_obras_consultadas(self):
        text = (
            "## Conclusão\n\nTexto.\n\n"
            "## Obras Consultadas\n\nAutor. Título.\n"
        )
        result = strip_reference_blocks(text)
        assert "## Obras Consultadas" not in result

    def test_stops_at_next_same_level_heading(self):
        text = (
            "## Capítulo 1\n\nConteúdo.\n\n"
            "## Referências Bibliográficas\n\n"
            "AUTOR. Título.\n\n"
            "## Anexos\n\nConteúdo dos anexos.\n"
        )
        result = strip_reference_blocks(text)
        assert "AUTOR. Título" not in result
        assert "## Anexos" in result
        assert "Conteúdo dos anexos" in result

    def test_keeps_text_without_refs(self):
        text = "## Capítulo\n\nProsa sem referências."
        result = strip_reference_blocks(text)
        assert result.strip() == text.strip()

    def test_pipeline_with_stripping_disabled(self):
        from core.pipeline import convert_document
        text = b"## Conteudo\n\nTexto.\n\n## Referencias\n\nAutor. Titulo.\n"
        result = convert_document(
            file_bytes=text,
            filename="test.txt",
            strip_references_flag=False,
        )
        assert result.success
        assert "Autor. Titulo" in result.markdown
