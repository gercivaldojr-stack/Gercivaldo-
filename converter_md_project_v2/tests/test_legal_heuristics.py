"""Testes para o módulo de heurísticas jurídicas."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.legal_heuristics import apply_legal_heuristics, detect_blockquotes, generate_toc, remove_sumario


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


class TestForenseEnumerationProtection:
    """M3: Alíneas jurídicas NÃO viram headings ###."""

    def test_alinea_a_not_heading(self):
        text = "a) A concessão de tutela de urgência"
        result = apply_legal_heuristics(text, mode="forense")
        assert not result.strip().startswith("#")

    def test_alinea_b_not_heading(self):
        text = "b) Indenização por danos morais"
        result = apply_legal_heuristics(text, mode="forense")
        assert not result.strip().startswith("#")

    def test_roman_dash_not_heading(self):
        """I — texto NÃO deve virar heading."""
        text = "I — os honorários advocatícios"
        result = apply_legal_heuristics(text, mode="forense")
        assert not result.strip().startswith("#")

    def test_roman_ii_dash_not_heading(self):
        text = "II — custas processuais"
        result = apply_legal_heuristics(text, mode="forense")
        assert not result.strip().startswith("#")

    def test_subsection_1_1_not_heading_forense(self):
        """1.1 texto NÃO deve virar heading no modo forense (é alínea)."""
        text = "1.1 primeira subseção do pedido"
        result = apply_legal_heuristics(text, mode="forense")
        assert not result.strip().startswith("#")

    def test_subsection_1_2_not_heading_forense(self):
        text = "1.2 segunda subseção do pedido"
        result = apply_legal_heuristics(text, mode="forense")
        assert not result.strip().startswith("#")


class TestForenseNumberedSections:
    """M5: Seções numeradas no modo forense."""

    def test_numbered_uppercase_section_is_h2(self):
        """1. DOS FATOS → ## H2."""
        text = "1. DOS FATOS"
        result = apply_legal_heuristics(text, mode="forense")
        assert result.strip().startswith("## ")

    def test_numbered_uppercase_section_2(self):
        text = "2. DO DIREITO"
        result = apply_legal_heuristics(text, mode="forense")
        assert result.strip().startswith("## ")

    def test_numbered_uppercase_section_pedidos(self):
        text = "3. DOS PEDIDOS"
        result = apply_legal_heuristics(text, mode="forense")
        assert result.strip().startswith("## ")

    def test_numbered_lowercase_not_h2(self):
        """1. texto minúsculo NÃO é seção numerada."""
        text = "1. Introdução ao caso"
        result = apply_legal_heuristics(text, mode="forense")
        assert not result.strip().startswith("## ")

    def test_excelentissimo_is_h2(self):
        text = "EXCELENTÍSSIMO SENHOR DOUTOR JUIZ DE DIREITO"
        result = apply_legal_heuristics(text, mode="forense")
        assert result.strip().startswith("## ")
        assert not result.strip().startswith("### ")

    def test_no_h2_promoted_to_h1(self):
        """H2 NÃO deve ser promovido a H1 mesmo sem H1 no documento."""
        text = "DOS FATOS\n\nTexto.\n\nDOS PEDIDOS\n\nTexto."
        result = apply_legal_heuristics(text, mode="forense")
        lines = [l for l in result.split("\n") if l.strip().startswith("#")]
        for line in lines:
            assert line.strip().startswith("## ")
            assert not line.strip().startswith("# ") or line.strip().startswith("## ")


class TestJurisprudenceCitations:
    """P7: Citações jurisprudenciais devem ser blockquote."""

    def test_no_hc_citation(self):
        text = (
            "Texto argumentativo.\n\n"
            "No HC 91.199/SP, Rel. Min. Cármen Lúcia, 1.ª Turma, j. 16/10/2007, "
            "o STF assentou que o excesso de prazo deve ser avaliado.\n\n"
            "Mais texto."
        )
        result = apply_legal_heuristics(text, mode="forense", detect_citations=True)
        assert "> No HC 91.199/SP" in result
        assert "Mais texto" in result
        assert "> Mais texto" not in result

    def test_no_agrg_citation(self):
        text = (
            "No AgRg no RHC 129.833/PB, Rel. Min. Laurita Vaz, 6.ª Turma, "
            "o STJ reconheceu a mitigação da Súmula 52.\n\n"
            "Texto normal."
        )
        result = apply_legal_heuristics(text, mode="forense", detect_citations=True)
        assert "> No AgRg no RHC 129.833/PB" in result

    def test_no_resp_citation(self):
        text = "No REsp 1.234.567/SP, decidiu-se que..."
        result = apply_legal_heuristics(text, mode="forense", detect_citations=True)
        assert "> No REsp 1.234.567/SP" in result

    def test_citation_disabled(self):
        text = "No HC 91.199/SP, Rel. Min. Cármen Lúcia, decidiu-se."
        result = apply_legal_heuristics(text, mode="forense", detect_citations=False)
        assert "> No HC" not in result

    def test_citation_only_in_forense(self):
        text = "No HC 91.199/SP, o STF assentou sobre o excesso de prazo."
        result = apply_legal_heuristics(text, mode="doutrina", detect_citations=True)
        assert "> No HC" not in result

    def test_normal_text_not_cited(self):
        text = "O réu deve pagar indenização por danos morais."
        result = apply_legal_heuristics(text, mode="forense", detect_citations=True)
        assert "> " not in result

    def test_multiline_citation(self):
        text = (
            "No HC 5043351-09.2023.8.09.0000, admitiu-se\n"
            "a mitigação da Súmula em caso análogo.\n\n"
            "Texto seguinte."
        )
        result = apply_legal_heuristics(text, mode="forense", detect_citations=True)
        assert "> No HC 5043351" in result
        assert "> a mitigação" in result
        assert "Texto seguinte" in result
        assert "> Texto seguinte" not in result


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


class TestDetectBlockquotes:
    def test_ementa_block(self):
        text = (
            "## EMENTA\n"
            "Direito civil. Responsabilidade objetiva.\n"
            "Dano moral configurado.\n"
            "\n\n"
            "## ACÓRDÃO"
        )
        result = detect_blockquotes(text)
        assert "> " in result
        assert "> Direito civil" in result or "> EMENTA" in result

    def test_ementa_with_colon(self):
        text = (
            "EMENTA:\n"
            "Recurso especial. Consumidor.\n"
            "\n\n"
            "Conteúdo normal."
        )
        result = detect_blockquotes(text)
        assert "> EMENTA:" in result
        assert "> Recurso especial" in result

    def test_ementa_stops_at_heading(self):
        text = (
            "EMENTA\n"
            "Texto da ementa.\n"
            "# ACÓRDÃO\n"
            "Conteúdo do acórdão."
        )
        result = detect_blockquotes(text)
        assert "> Texto da ementa" in result
        assert "> # ACÓRDÃO" not in result

    def test_citation_with_tribunal(self):
        text = (
            '\u201cO consumidor tem direito à reparação integral dos danos sofridos.\u201d '
            '(STJ, REsp 1.234.567/SP, Rel. Min. Fulano, j. 10/03/2024)'
        )
        result = detect_blockquotes(text)
        assert result.startswith("> ")

    def test_no_blockquote_for_normal_text(self):
        text = "O réu deve pagar indenização por danos morais."
        result = detect_blockquotes(text)
        assert "> " not in result

    def test_short_quote_not_blockquoted(self):
        text = '"Sim" disse o juiz.'
        result = detect_blockquotes(text)
        assert "> " not in result

    def test_quote_without_tribunal_not_blockquoted(self):
        text = '\u201cTexto longo de citação sem atribuição a tribunal nenhum, apenas um trecho genérico.\u201d'
        result = detect_blockquotes(text)
        assert "> " not in result


class TestGenerateToc:
    def test_basic_toc(self):
        text = "# Título\n\nTexto.\n\n## Dos Fatos\n\nTexto.\n\n## Dos Pedidos\n\nTexto."
        toc = generate_toc(text)
        assert "## Sumário" in toc
        assert "- [Título]" in toc
        assert "- [Dos Fatos]" in toc
        assert "- [Dos Pedidos]" in toc

    def test_toc_indentation(self):
        text = "# Cap 1\n\n## Seção 1\n\n### Sub 1\n\nTexto."
        toc = generate_toc(text)
        assert "- [Cap 1]" in toc
        assert "  - [Seção 1]" in toc
        assert "    - [Sub 1]" in toc

    def test_toc_empty_for_single_heading(self):
        text = "# Título Único\n\nApenas um heading."
        toc = generate_toc(text)
        assert toc == ""

    def test_toc_empty_for_no_headings(self):
        text = "Texto sem headings.\nMais texto."
        toc = generate_toc(text)
        assert toc == ""

    def test_toc_slug_generation(self):
        text = "# Título\n\n## Dos Fatos Relevantes\n\nTexto."
        toc = generate_toc(text)
        assert "(#dos-fatos-relevantes)" in toc

    def test_toc_integrated_in_pipeline(self):
        """TOC deve aparecer no resultado final do pipeline."""
        from core.pipeline import convert_document

        content = "DOS FATOS\n\nTexto dos fatos.\n\nDOS PEDIDOS\n\nTexto dos pedidos."
        result = convert_document(
            file_bytes=content.encode("utf-8"),
            filename="peticao.txt",
            mode="forense",
        )
        assert result.success
        assert "## Sumário" in result.markdown
        assert "DOS FATOS" in result.markdown
