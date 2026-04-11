"""Testes para o normalizador de tabelas."""

from core.table_normalizer import (
    _convert_single_column_to_paragraph,
    _dedupe_columns,
    _remove_empty_columns,
    normalize_tables,
)


class TestDedupeColumns:
    def test_removes_duplicate_adjacent_column(self):
        rows = [
            ["A", "A", "B"],
            ["X", "X", "Y"],
            ["P", "P", "Q"],
        ]
        result, removed = _dedupe_columns(rows)
        assert removed == 1
        assert result == [["A", "B"], ["X", "Y"], ["P", "Q"]]

    def test_keeps_distinct_columns(self):
        rows = [["A", "B", "C"], ["X", "Y", "Z"]]
        result, removed = _dedupe_columns(rows)
        assert removed == 0
        assert result == rows

    def test_handles_uneven_rows(self):
        rows = [["A", "B"], ["X", "Y", "Z"]]
        result, removed = _dedupe_columns(rows)
        # Padroniza primeiro
        assert all(len(r) == len(result[0]) for r in result)


class TestRemoveEmptyColumns:
    def test_removes_empty_column(self):
        rows = [["A", "", "B"], ["X", "", "Y"]]
        result, removed = _remove_empty_columns(rows)
        assert removed == 1
        assert result == [["A", "B"], ["X", "Y"]]

    def test_keeps_partially_filled(self):
        rows = [["A", "X", "B"], ["", "Y", ""]]
        result, removed = _remove_empty_columns(rows)
        assert removed == 0


class TestSingleColumnConversion:
    def test_single_cell_to_blockquote(self):
        rows = [["Citação importante"]]
        result = _convert_single_column_to_paragraph(rows)
        assert result == "> Citação importante"

    def test_multiple_cells_to_list(self):
        rows = [["Item 1"], ["Item 2"], ["Item 3"]]
        result = _convert_single_column_to_paragraph(rows)
        assert "- Item 1" in result
        assert "- Item 2" in result
        assert "- Item 3" in result

    def test_two_columns_returns_none(self):
        rows = [["A", "B"], ["X", "Y"]]
        result = _convert_single_column_to_paragraph(rows)
        assert result is None


class TestNormalizeTables:
    def test_normalizes_duplicated_table(self):
        text = (
            "| 1. | CONCEITOS  69 | CONCEITOS  69 | CONCEITOS  69 |\n"
            "| 1.1. | 1.1. | CAPACIDADE  69 | CAPACIDADE  69 |"
        )
        result = normalize_tables(text)
        # Deve ter menos pipes (colunas removidas)
        assert result.count("|") < text.count("|")
        assert "CONCEITOS" in result

    def test_keeps_normal_table(self):
        text = (
            "| Matéria | Dispositivos |\n"
            "| --- | --- |\n"
            "| Vigência | Art. 1º |"
        )
        result = normalize_tables(text)
        assert "Matéria" in result
        assert "Dispositivos" in result
        assert "Art. 1º" in result

    def test_no_tables_unchanged(self):
        text = "## Heading\n\nProsa simples sem tabelas."
        result = normalize_tables(text)
        assert result == text

    def test_single_column_to_list(self):
        text = (
            "| Item A |\n"
            "| Item B |\n"
            "| Item C |"
        )
        result = normalize_tables(text)
        # Tabela 1-coluna com múltiplas linhas vira lista
        assert "- Item A" in result
        assert "- Item B" in result
        assert "- Item C" in result
