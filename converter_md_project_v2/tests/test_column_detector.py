"""Testes para detecção de colunas em PDF."""

from unittest.mock import MagicMock

from core.column_detector import _is_two_column_layout, detect_and_reorder_columns


def _make_block(x0, y0, x1, y1, text):
    return {"x0": x0, "y0": y0, "x1": x1, "y1": y1, "text": text}


def _make_page(blocks_data, width=612, height=792):
    """Cria mock de página PyMuPDF."""
    page = MagicMock()
    page.rect.width = width
    page.rect.height = height
    dict_blocks = []
    for x0, y0, x1, y1, text in blocks_data:
        lines = [{"spans": [{"text": text}]}]
        dict_blocks.append({
            "type": 0,
            "bbox": (x0, y0, x1, y1),
            "lines": lines,
        })
    page.get_text.return_value = {"blocks": dict_blocks}
    return page


class TestIsTwoColumnLayout:
    def test_single_column(self):
        blocks = [
            _make_block(50, 100, 550, 120, "Texto 1"),
            _make_block(50, 130, 550, 150, "Texto 2"),
            _make_block(50, 160, 550, 180, "Texto 3"),
            _make_block(50, 190, 550, 210, "Texto 4"),
        ]
        assert _is_two_column_layout(blocks, 612) is False

    def test_two_columns(self):
        blocks = [
            _make_block(50, 100, 280, 120, "Esq 1"),
            _make_block(50, 130, 280, 150, "Esq 2"),
            _make_block(320, 100, 560, 120, "Dir 1"),
            _make_block(320, 130, 560, 150, "Dir 2"),
        ]
        assert _is_two_column_layout(blocks, 612) is True

    def test_too_few_blocks(self):
        blocks = [
            _make_block(50, 100, 280, 120, "Um"),
            _make_block(320, 100, 560, 120, "Dois"),
        ]
        assert _is_two_column_layout(blocks, 612) is False

    def test_many_crossing_blocks(self):
        blocks = [
            _make_block(50, 100, 560, 120, "Cruza 1"),
            _make_block(50, 130, 560, 150, "Cruza 2"),
            _make_block(50, 160, 560, 180, "Cruza 3"),
            _make_block(50, 190, 560, 210, "Cruza 4"),
        ]
        assert _is_two_column_layout(blocks, 612) is False

    def test_threshold_edge_only_left(self):
        blocks = [
            _make_block(50, 100, 280, 120, "Esq 1"),
            _make_block(50, 130, 280, 150, "Esq 2"),
            _make_block(50, 160, 280, 180, "Esq 3"),
            _make_block(50, 190, 280, 210, "Esq 4"),
        ]
        assert _is_two_column_layout(blocks, 612) is False


class TestDetectAndReorderColumns:
    def test_empty_page(self):
        page = _make_page([])
        assert detect_and_reorder_columns(page) == ""

    def test_single_column_order(self):
        page = _make_page([
            (50, 200, 550, 220, "Paragrafo 1"),
            (50, 100, 550, 120, "Titulo"),
            (50, 300, 550, 320, "Paragrafo 2"),
        ])
        result = detect_and_reorder_columns(page)
        lines = result.split("\n")
        assert lines[0] == "Titulo"
        assert lines[1] == "Paragrafo 1"
        assert lines[2] == "Paragrafo 2"

    def test_two_column_reorder(self):
        page = _make_page([
            (320, 100, 560, 120, "Dir 1"),
            (50, 100, 280, 120, "Esq 1"),
            (320, 200, 560, 220, "Dir 2"),
            (50, 200, 280, 220, "Esq 2"),
        ])
        result = detect_and_reorder_columns(page)
        lines = result.split("\n")
        assert lines[0] == "Esq 1"
        assert lines[1] == "Esq 2"
        assert lines[2] == "Dir 1"
        assert lines[3] == "Dir 2"

    def test_mixed_page_no_reorder(self):
        page = _make_page([
            (50, 100, 560, 120, "Titulo largo"),
            (50, 200, 560, 220, "Paragrafo largo"),
            (50, 300, 560, 320, "Outro paragrafo"),
            (50, 400, 560, 420, "Mais texto"),
        ])
        result = detect_and_reorder_columns(page)
        assert "Titulo largo" in result
