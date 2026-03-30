"""Testes para o módulo de heurísticas jurídicas."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.legal_heuristics import apply_legal_heuristics, remove_sumario


class TestForenseMode:
    def test_dos_fatos(self):
        text = "DOS FATOS"
        result = apply_legal_heuristics(text, mode="forense")
        assert result.startswith("## ")

    def test_fundamentacao(self):
        text = "FUNDAMENTAÇÃO"
        result = apply_legal_heuristics(text, mode="forense")
        assert result.startswith("## ")

    def test_do_direito(self):
        text = "DO DIREITO"
        result = apply_legal_heuristics(text, mode="forense")
        assert result.startswith("## ")

    def test_dos_pedidos(self):
        text = "DOS PEDIDOS"
        result = apply_legal_heuristics(text, mode="forense")
        assert result.startswith("## ")

    def test_clausula(self):
        text = "CLÁUSULA PRIMEIRA"
        result = apply_legal_heuristics(text, mode="forense")
        assert result.startswith("## ")

    def test_numbered_item(self):
        text = "1. Introdução ao caso"
        result = apply_legal_heuristics(text, mode="forense")
        assert result.startswith("### ")

    def test_sentenca_h1(self):
        text = "SENTENÇA"
        result = apply_legal_heuristics(text, mode="forense")
        assert result.startswith("# ")

    def test_preserves_existing_heading(self):
        text = "## Já é heading"
        result = apply_legal_heuristics(text, mode="forense")
        assert result == "## Já é heading"

    def test_empty_text(self):
        assert apply_legal_heuristics("") == ""

    def test_long_numbered_line_not_heading(self):
        text = "1. " + "a" * 250
        result = apply_legal_heuristics(text, mode="forense")
        assert not result.startswith("### ")

    def test_roman_numeral_dos_fatos(self):
        text = "I - DOS FATOS"
        result = apply_legal_heuristics(text, mode="forense")
        assert result.startswith("## ")

    def test_do_merito(self):
        text = "DO MÉRITO"
        result = apply_legal_heuristics(text, mode="forense")
        assert result.startswith("## ")


class TestDoutrinaMode:
    def test_capitulo(self):
        text = "CAPÍTULO I - Introdução"
        result = apply_legal_heuristics(text, mode="doutrina")
        assert result.startswith("# ")

    def test_secao(self):
        text = "SEÇÃO I - Conceitos"
        result = apply_legal_heuristics(text, mode="doutrina")
        assert result.startswith("## ")

    def test_numbered_section(self):
        text = "1. Aspectos Gerais"
        result = apply_legal_heuristics(text, mode="doutrina")
        assert result.startswith("## ")

    def test_subsection(self):
        text = "1.1 Definições"
        result = apply_legal_heuristics(text, mode="doutrina")
        assert result.startswith("### ")

    def test_deep_subsection(self):
        text = "1.1.2 Sub-item"
        result = apply_legal_heuristics(text, mode="doutrina")
        assert result.startswith("### ")

    def test_parte(self):
        text = "PARTE I - Direito Civil"
        result = apply_legal_heuristics(text, mode="doutrina")
        assert result.startswith("# ")

    def test_titulo(self):
        text = "TÍTULO II - Obrigações"
        result = apply_legal_heuristics(text, mode="doutrina")
        assert result.startswith("# ")


class TestRemoveSumario:
    def test_removes_sumario_section(self):
        text = (
            "SUMÁRIO\n"
            "1. Introdução ................ 5\n"
            "2. Capítulo .................. 15\n"
            "3. Conclusão ................. 30\n"
            "\n\n\n"
            "Este é o conteúdo real do documento que deve permanecer intacto "
            "e contém texto suficiente para ser identificado como conteúdo real do documento."
        )
        result = remove_sumario(text)
        assert "SUMÁRIO" not in result
        assert "conteúdo real" in result

    def test_no_sumario(self):
        text = "Texto normal sem sumário."
        assert remove_sumario(text) == text
