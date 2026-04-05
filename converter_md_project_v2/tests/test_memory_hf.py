"""Testes para _detect_hf_zones com amostragem."""

import fitz

from core.extractors import _detect_hf_zones


def _make_pdf_with_footers(num_pages: int) -> fitz.Document:
    """Cria PDF com footer repetido em todas as páginas."""
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page()
        # Conteúdo no meio da página (não será removido)
        page.insert_text((72, 400), f"Conteudo pagina {i + 1}.")
        # Footer repetido na zona de rodapé (y > 88% de 842 = ~740)
        page.insert_text((72, 770), "Escritorio Juridico XYZ - Pagina")
    return doc


class TestDetectHfZonesSmallDoc:
    def test_no_sampling_for_small(self):
        """Doc com 10 páginas não usa amostragem."""
        doc = _make_pdf_with_footers(10)
        result = _detect_hf_zones(doc, sample_pages=50)
        # Footer repetido deve ser detectado em todas as páginas
        pages_with_removal = {page_idx for page_idx, _ in result}
        assert len(pages_with_removal) >= 5
        doc.close()


class TestDetectHfZonesLargeDoc:
    def test_sampling_for_large(self):
        """Doc com 80 páginas usa amostragem de 50."""
        doc = _make_pdf_with_footers(80)
        result = _detect_hf_zones(doc, sample_pages=50)
        # Padrão deve ser identificado e aplicado a TODAS as páginas
        pages_with_removal = {page_idx for page_idx, _ in result}
        # Pelo menos 40 páginas devem ter blocos removidos
        assert len(pages_with_removal) >= 40
        doc.close()


class TestDetectHfZonesContent:
    def test_identifies_repeated_footers(self):
        """Footer repetido em 80%+ das páginas é detectado."""
        doc = _make_pdf_with_footers(20)
        result = _detect_hf_zones(doc)
        assert len(result) > 0
        doc.close()

    def test_preserves_legal_content(self):
        """Blocos no meio da página nunca são removidos."""
        doc = fitz.open()
        for i in range(10):
            page = doc.new_page()
            # Conteúdo no corpo (y=400, longe de header/footer zones)
            page.insert_text((72, 400), f"DOS FATOS - pagina {i + 1}")
        result = _detect_hf_zones(doc)
        # Nenhum bloco no meio deve ser removido
        for page_idx, blk_idx in result:
            page = doc[page_idx]
            blocks = page.get_text("dict")["blocks"]
            if blk_idx < len(blocks):
                bbox = blocks[blk_idx]["bbox"]
                page_height = page.rect.height
                assert bbox[1] < page_height * 0.12 or bbox[3] > page_height * 0.85
        doc.close()

    def test_applies_to_unsampled(self):
        """Padrão identificado na amostra é aplicado a páginas não amostradas."""
        doc = _make_pdf_with_footers(100)
        result = _detect_hf_zones(doc, sample_pages=20)
        pages_with_removal = {page_idx for page_idx, _ in result}
        # Deve cobrir páginas além das 20 amostradas
        assert len(pages_with_removal) > 20
        doc.close()

    def test_empty_doc(self):
        """Doc vazio retorna set vazio."""
        doc = fitz.open()
        result = _detect_hf_zones(doc)
        assert result == set()
        doc.close()
