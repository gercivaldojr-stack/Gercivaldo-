"""Testes para o módulo de heurísticas jurídicas."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.legal_heuristics import (
    apply_legal_heuristics,
    remove_sumario,
    _fix_heading_hierarchy,
    _format_enumeration_as_list,
)


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

    def test_numbered_item_is_not_heading(self):
        """Itens numerados (1., 2.) são enumeração, não heading."""
        text = "1. Introdução ao caso"
        result = apply_legal_heuristics(text, mode="forense")
        assert not result.startswith("### ")
        assert not result.startswith("## ")

    def test_letter_enumeration_not_heading(self):
        """Itens com letra (a), b)) são enumeração, não heading."""
        text = "a) A concessão de tutela de urgência para bloqueio de valores"
        result = apply_legal_heuristics(text, mode="forense")
        assert not result.startswith("#")

    def test_letter_dot_enumeration_not_heading(self):
        text = "b. Indenização por danos morais no valor de R$ 10.000,00"
        result = apply_legal_heuristics(text, mode="forense")
        assert not result.startswith("#")

    def test_roman_enumeration_not_heading(self):
        text = "ii) os honorários advocatícios"
        result = apply_legal_heuristics(text, mode="forense")
        assert not result.startswith("#")

    def test_number_paren_enumeration_not_heading(self):
        text = "2) A inversão do ônus da prova"
        result = apply_legal_heuristics(text, mode="forense")
        assert not result.startswith("#")

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

    def test_enderecamento_juiz_is_h2(self):
        """Endereçamento ao juiz deve ser H2, não H1."""
        text = "EXCELENTÍSSIMO SENHOR DOUTOR JUIZ DE DIREITO"
        result = apply_legal_heuristics(text, mode="forense")
        assert result.startswith("## ")
        assert not result.startswith("### ")

    def test_peticao_inicial_is_h1(self):
        """Título da peça deve ser H1."""
        text = "PETIÇÃO INICIAL"
        result = apply_legal_heuristics(text, mode="forense")
        assert result.startswith("# ")
        assert not result.startswith("## ")

    def test_enderecamento_ao_juizo(self):
        text = "AO JUÍZO DA 1ª VARA CÍVEL"
        result = apply_legal_heuristics(text, mode="forense")
        assert result.startswith("## ")

    def test_subsection_da_responsabilidade(self):
        """Subseções Da/Do/Das/Dos dentro de seções devem virar H3."""
        text = "Da responsabilidade objetiva do Réu"
        result = apply_legal_heuristics(text, mode="forense")
        assert result.startswith("### ")

    def test_subsection_do_dano_moral(self):
        text = "Do dano moral in re ipsa"
        result = apply_legal_heuristics(text, mode="forense")
        assert result.startswith("### ")

    def test_subsection_da_obrigacao(self):
        text = "Da obrigação de indenizar"
        result = apply_legal_heuristics(text, mode="forense")
        assert result.startswith("### ")

    def test_subsection_dos_juros(self):
        text = "Dos juros e correção monetária"
        result = apply_legal_heuristics(text, mode="forense")
        assert result.startswith("### ")

    def test_long_da_line_not_heading(self):
        """Linhas longas com Da/Do não são subseções, são parágrafos."""
        text = "Da análise dos documentos juntados aos autos, verifica-se que o réu não comprovou suas alegações de forma satisfatória perante o juízo"
        result = apply_legal_heuristics(text, mode="forense")
        assert not result.startswith("#")

    def test_acao_revisional_is_h1(self):
        """Bug 2: AÇÃO REVISIONAL deve virar H1."""
        text = "AÇÃO REVISIONAL DE CONTRATOS DE CRÉDITO RURAL"
        result = apply_legal_heuristics(text, mode="forense")
        assert "# AÇÃO REVISIONAL" in result
        assert not result.strip().startswith("## ")

    def test_acao_indenizacao_is_h1(self):
        text = "AÇÃO DE INDENIZAÇÃO POR DANOS MORAIS"
        result = apply_legal_heuristics(text, mode="forense")
        assert "# AÇÃO DE INDENIZAÇÃO" in result

    def test_acao_declaratoria_is_h1(self):
        text = "AÇÃO DECLARATÓRIA DE NULIDADE"
        result = apply_legal_heuristics(text, mode="forense")
        assert "# AÇÃO DECLARATÓRIA" in result

    def test_acao_cautelar_is_h1(self):
        text = "AÇÃO CAUTELAR DE EXIBIÇÃO DE DOCUMENTOS"
        result = apply_legal_heuristics(text, mode="forense")
        assert "# AÇÃO CAUTELAR" in result


class TestHeadingHierarchy:
    def test_first_h2_promoted_to_h1(self):
        """Bug 3: Se primeiro heading é ##, promover para #."""
        text = "## EXCELENTÍSSIMO SENHOR JUIZ\n\nTexto.\n\n## DOS FATOS\n\nFatos."
        result = _fix_heading_hierarchy(text)
        lines = result.split("\n")
        assert lines[0].startswith("# ")
        assert "EXCELENTÍSSIMO" in lines[0]

    def test_h1_already_present(self):
        """Se já existe H1, não promover nada."""
        text = "# PETIÇÃO INICIAL\n\n## EXCELENTÍSSIMO SENHOR JUIZ\n\nTexto."
        result = _fix_heading_hierarchy(text)
        assert result == text

    def test_acao_before_enderecamento(self):
        """Bug 2+3: AÇÃO H1 antes de EXCELENTÍSSIMO H2 preserva hierarquia."""
        text = "AÇÃO REVISIONAL DE CRÉDITO RURAL\n\nEXCELENTÍSSIMO SENHOR DOUTOR JUIZ\n\nDOS FATOS\n\nOs fatos."
        result = apply_legal_heuristics(text, mode="forense")
        lines = [l for l in result.split("\n") if l.strip().startswith("#")]
        assert lines[0].startswith("# ")
        assert "AÇÃO REVISIONAL" in lines[0]
        assert lines[1].startswith("## ")
        assert "EXCELENTÍSSIMO" in lines[1]


class TestEnumerationFormatting:
    def test_letter_items_become_list(self):
        """Bug 5: Itens a), b) devem virar lista markdown."""
        text = "## DOS PEDIDOS\n\na) Concessão de tutela\nb) Indenização por danos"
        result = _format_enumeration_as_list(text)
        assert "- **a)** Concessão" in result
        assert "- **b)** Indenização" in result

    def test_number_items_become_list(self):
        text = "1) Primeiro pedido\n2) Segundo pedido"
        result = _format_enumeration_as_list(text)
        assert "- **1)** Primeiro" in result
        assert "- **2)** Segundo" in result

    def test_headings_preserved(self):
        text = "## DOS PEDIDOS"
        result = _format_enumeration_as_list(text)
        assert result == "## DOS PEDIDOS"


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
