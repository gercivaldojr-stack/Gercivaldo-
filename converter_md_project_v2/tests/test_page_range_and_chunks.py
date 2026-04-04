"""Testes para page_range (1-based), chunk_size e extração PDF."""

import pytest

from core.extractors import _parse_page_range


# ============================================================
# _parse_page_range — entrada 1-based, saída 0-based
# ============================================================

class TestParsePageRange:
    """Valida conversão 1-based → 0-based com tratamento de erros."""

    def test_single_page_1(self):
        """Página 1 (primeira) → índice 0."""
        assert _parse_page_range("1", 20) == [0]

    def test_single_page_5(self):
        """Página 5 → índice 4."""
        assert _parse_page_range("5", 20) == [4]

    def test_range_1_to_10(self):
        """Páginas 1-10 → índices 0-9 (10 páginas)."""
        result = _parse_page_range("1-10", 20)
        assert result == list(range(0, 10))
        assert len(result) == 10

    def test_range_10_to_20(self):
        """Páginas 10-20 → índices 9-19 (11 páginas)."""
        result = _parse_page_range("10-20", 20)
        assert result == list(range(9, 20))
        assert len(result) == 11

    def test_multiple_specs(self):
        """'1,5,10-20' → [0, 4, 9, 10, ..., 19]."""
        result = _parse_page_range("1,5,10-20", 20)
        assert 0 in result      # página 1
        assert 4 in result      # página 5
        assert 9 in result      # página 10
        assert 19 in result     # página 20
        assert 1 not in result  # página 2 NÃO incluída
        assert len(result) == 13  # 1 + 1 + 11

    def test_page_beyond_limit_ignored(self):
        """Página 100 em doc de 20 páginas → lista vazia (ignorada)."""
        result = _parse_page_range("100", 20)
        assert result == []

    def test_range_partially_beyond_limit(self):
        """Páginas 15-30 em doc de 20 → índices 14-19 (apenas as existentes)."""
        result = _parse_page_range("15-30", 20)
        assert result == list(range(14, 20))
        assert len(result) == 6

    def test_empty_spec_returns_all(self):
        """Spec vazia → todas as páginas."""
        result = _parse_page_range("", 5)
        assert result == [0, 1, 2, 3, 4]

    def test_none_like_empty(self):
        """Spec com espaços → todas as páginas."""
        result = _parse_page_range("  ", 5)
        assert result == [0, 1, 2, 3, 4]

    def test_invalid_non_numeric_raises(self):
        """Entrada não-numérica gera ValueError."""
        with pytest.raises(ValueError, match="invalido|invalida"):
            _parse_page_range("abc", 20)

    def test_invalid_range_format_raises(self):
        """'5-abc' gera ValueError."""
        with pytest.raises(ValueError, match="invalido"):
            _parse_page_range("5-abc", 20)

    def test_page_zero_raises(self):
        """Página 0 gera ValueError (1-based, mínimo é 1)."""
        with pytest.raises(ValueError, match=">= 1"):
            _parse_page_range("0", 20)

    def test_negative_page_raises(self):
        """Página negativa gera ValueError (parseada como range vazio-1)."""
        with pytest.raises(ValueError):
            _parse_page_range("-1", 20)

    def test_inverted_range_raises(self):
        """Intervalo invertido '10-5' gera ValueError."""
        with pytest.raises(ValueError, match="inicio > fim"):
            _parse_page_range("10-5", 20)

    def test_spaces_in_spec(self):
        """Espaços são tolerados: ' 1 , 5 , 10 - 20 '."""
        result = _parse_page_range(" 1 , 5 , 10 - 20 ", 20)
        assert 0 in result  # página 1
        assert 4 in result  # página 5

    def test_duplicate_pages_deduplicated(self):
        """Páginas duplicadas são deduplicadas."""
        result = _parse_page_range("1,1,1-3", 10)
        assert result == [0, 1, 2]

    def test_single_page_equal_to_total(self):
        """Última página do documento."""
        result = _parse_page_range("20", 20)
        assert result == [19]

    def test_range_exact_document(self):
        """Range cobrindo todo o documento."""
        result = _parse_page_range("1-20", 20)
        assert result == list(range(20))
        assert len(result) == 20


# ============================================================
# chunk_size — validação funcional com PDF real
# ============================================================

class TestChunkSize:
    """Testa processamento em chunks via pipeline."""

    def _make_pdf_bytes(self, num_pages: int) -> bytes:
        """Cria PDF mínimo com N páginas usando PyMuPDF.

        Texto colocado a y=300 para não cair na zona de header/footer
        (que é removida pela detecção de cabeçalhos repetidos).
        """
        import fitz
        doc = fitz.open()
        for i in range(num_pages):
            page = doc.new_page()
            page.insert_text((72, 300), f"Texto da pagina {i + 1}.")
        data = doc.tobytes()
        doc.close()
        return data

    def test_no_chunk_processes_all(self):
        """Sem chunk_size, processa todas as páginas de uma vez."""
        from core.pipeline import convert_document
        pdf = self._make_pdf_bytes(5)
        result = convert_document(
            file_bytes=pdf, filename="test.pdf",
            chunk_size=None,
        )
        assert result.success
        for i in range(1, 6):
            assert f"pagina {i}" in result.markdown.lower()

    def test_chunk_size_2(self):
        """chunk_size=2 em doc de 5 páginas → 3 chunks, mesmo resultado."""
        from core.pipeline import convert_document
        pdf = self._make_pdf_bytes(5)
        result = convert_document(
            file_bytes=pdf, filename="test.pdf",
            chunk_size=2,
        )
        assert result.success
        for i in range(1, 6):
            assert f"pagina {i}" in result.markdown.lower()

    def test_chunk_size_1(self):
        """chunk_size=1 → uma página por chunk (caso extremo)."""
        from core.pipeline import convert_document
        pdf = self._make_pdf_bytes(3)
        result = convert_document(
            file_bytes=pdf, filename="test.pdf",
            chunk_size=1,
        )
        assert result.success
        for i in range(1, 4):
            assert f"pagina {i}" in result.markdown.lower()

    def test_chunk_size_larger_than_doc(self):
        """chunk_size maior que o doc → processa tudo em 1 chunk."""
        from core.pipeline import convert_document
        pdf = self._make_pdf_bytes(3)
        result = convert_document(
            file_bytes=pdf, filename="test.pdf",
            chunk_size=1000,
        )
        assert result.success
        assert "pagina 1" in result.markdown.lower()

    def test_chunk_with_page_range(self):
        """chunk_size + page_range: só processa páginas do range, em chunks."""
        from core.pipeline import convert_document
        pdf = self._make_pdf_bytes(10)
        result = convert_document(
            file_bytes=pdf, filename="test.pdf",
            page_range="3-7",
            chunk_size=2,
        )
        assert result.success
        # Páginas 3-7 devem estar presentes
        for i in [3, 4, 5, 6, 7]:
            assert f"pagina {i}" in result.markdown.lower()
        # Páginas 1, 2, 8, 9, 10 NÃO devem estar (exceto via frontmatter/limpeza)
        assert "pagina 1." not in result.markdown.lower()
        assert "pagina 10." not in result.markdown.lower()

    def test_chunk_result_equals_no_chunk(self):
        """Resultado com chunk deve ser idêntico ao sem chunk."""
        from core.pipeline import convert_document
        pdf = self._make_pdf_bytes(6)
        r_no_chunk = convert_document(
            file_bytes=pdf, filename="test.pdf",
            chunk_size=None,
        )
        r_chunk = convert_document(
            file_bytes=pdf, filename="test.pdf",
            chunk_size=2,
        )
        assert r_no_chunk.success and r_chunk.success

        # O texto extraído deve ser igual (frontmatter tem timestamp, comparar sem ele)
        def strip_frontmatter(md):
            lines = md.split("\n")
            result = []
            fm_count = 0
            for line in lines:
                if line.strip() == "---":
                    fm_count += 1
                    if fm_count <= 2:
                        continue
                if fm_count < 2:
                    continue
                result.append(line)
            return "\n".join(result)

        assert strip_frontmatter(r_no_chunk.markdown) == strip_frontmatter(r_chunk.markdown)


# ============================================================
# page_range funcional com PDF real
# ============================================================

class TestPageRangeWithPdf:
    """Testa page_range end-to-end com PDF real."""

    def _make_pdf_bytes(self, num_pages: int) -> bytes:
        import fitz
        doc = fitz.open()
        for i in range(num_pages):
            page = doc.new_page()
            # y=300 para não cair na zona de header/footer
            page.insert_text((72, 300), f"Conteudo pagina {i + 1}.")
        data = doc.tobytes()
        doc.close()
        return data

    def test_page_1_only(self):
        from core.pipeline import convert_document
        pdf = self._make_pdf_bytes(5)
        result = convert_document(file_bytes=pdf, filename="test.pdf", page_range="1")
        assert result.success
        assert "pagina 1" in result.markdown.lower()
        assert "pagina 2" not in result.markdown.lower()

    def test_page_range_3_to_5(self):
        from core.pipeline import convert_document
        pdf = self._make_pdf_bytes(10)
        result = convert_document(file_bytes=pdf, filename="test.pdf", page_range="3-5")
        assert result.success
        assert "pagina 3" in result.markdown.lower()
        assert "pagina 4" in result.markdown.lower()
        assert "pagina 5" in result.markdown.lower()
        assert "pagina 1." not in result.markdown.lower()
        assert "pagina 6." not in result.markdown.lower()

    def test_page_range_beyond_limit(self):
        """Range totalmente além do limite → documento vazio."""
        from core.pipeline import convert_document
        pdf = self._make_pdf_bytes(5)
        result = convert_document(file_bytes=pdf, filename="test.pdf", page_range="100-200")
        assert not result.success
        assert "vazio" in result.error.lower() or "extraível" in result.error.lower()

    def test_page_range_invalid_raises_in_pipeline(self):
        """Entrada inválida gera erro no pipeline (não crash)."""
        from core.pipeline import convert_document
        pdf = self._make_pdf_bytes(5)
        result = convert_document(file_bytes=pdf, filename="test.pdf", page_range="abc")
        assert not result.success
        assert result.error  # deve ter mensagem de erro
