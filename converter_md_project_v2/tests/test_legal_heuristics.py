"""Testes para o módulo de heurísticas jurídicas."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.legal_heuristics import (  # noqa: E402
    apply_legal_heuristics,
    detect_blockquotes,
    fill_heading_gaps,
    format_signatures,
    generate_toc,
    remove_sumario,
    separate_enumerated_items,
    wrap_internal_notes,
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
        text = (
            "Da análise dos documentos juntados aos autos, verifica-se que o réu "
            "não comprovou suas alegações de forma satisfatória perante o juízo"
        )
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
        # depth 3 (N.N.N) → #### (D9 fix: deep hierarchy)
        assert result.startswith("#### ")

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
        lines = [ln for ln in result.split("\n") if ln.strip().startswith("#")]
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

    def test_toc_slug_truncation(self):
        """Slugs longos devem ser truncados para manter âncoras razoáveis."""
        long_title = (
            "Do constrangimento ilegal por excesso de prazo na "
            "formação da culpa e demora injustificada no julgamento"
        )
        text = f"# Título\n\n## {long_title}\n\nTexto."
        toc = generate_toc(text)
        # O slug deve estar truncado (< 65 chars)
        for line in toc.split("\n"):
            if "(#" in line:
                slug = line.split("(#")[1].rstrip(")")
                assert len(slug) <= 60

    def test_toc_integrated_in_pipeline(self):
        """TOC deve aparecer no resultado final do pipeline quando habilitado."""
        from core.pipeline import convert_document

        content = "DOS FATOS\n\nTexto dos fatos.\n\nDOS PEDIDOS\n\nTexto dos pedidos."
        result = convert_document(
            file_bytes=content.encode("utf-8"),
            filename="peticao.txt",
            mode="forense",
            generate_toc_flag=True,
        )
        assert result.success
        assert "## Sumário" in result.markdown
        assert "DOS FATOS" in result.markdown

    def test_toc_not_generated_by_default(self):
        """TOC NÃO deve aparecer por padrão (generate_toc_flag=False)."""
        from core.pipeline import convert_document

        content = "DOS FATOS\n\nTexto dos fatos.\n\nDOS PEDIDOS\n\nTexto dos pedidos."
        result = convert_document(
            file_bytes=content.encode("utf-8"),
            filename="peticao.txt",
            mode="forense",
        )
        assert result.success
        assert "## Sumário" not in result.markdown
        assert "DOS FATOS" in result.markdown


class TestSeparateEnumeratedItems:
    """M2 v4.1: Separação de itens enumerados por ponto-e-vírgula."""

    def test_basic_enumeration(self):
        text = (
            "Diante do exposto, requer-se:\n"
            "a) o conhecimento do recurso;\n"
            "b) a reforma da sentença;\n"
            "c) a condenação do réu."
        )
        result = separate_enumerated_items(text)
        assert "- " in result
        assert "o conhecimento do recurso;" in result
        assert "a reforma da sentença;" in result

    def test_items_become_list(self):
        text = (
            "Requer ao final:\n"
            "primeiro item;\n"
            "segundo item;\n"
            "terceiro item."
        )
        result = separate_enumerated_items(text)
        assert result.count("- ") >= 3

    def test_no_conversion_without_colon(self):
        text = "Texto normal sem dois-pontos\nOutra linha normal."
        result = separate_enumerated_items(text)
        assert "- " not in result

    def test_no_conversion_single_item(self):
        text = "Requer-se:\napenas um item."
        result = separate_enumerated_items(text)
        # Single item should not be converted
        assert "- " not in result

    def test_loose_semicolon_items(self):
        """Linhas soltas com ; recebem espaço entre elas."""
        text = (
            "Primeiro argumento relevante;\n"
            "segundo argumento relevante;\n"
            "terceiro argumento final."
        )
        result = separate_enumerated_items(text)
        # Deve ter linhas em branco entre itens com ;
        assert "\n\n" in result

    def test_heading_not_affected(self):
        text = "# Título\nTexto normal."
        result = separate_enumerated_items(text)
        assert result == text

    def test_integrated_in_pipeline(self):
        text = (
            "DOS PEDIDOS\n\n"
            "Diante do exposto, requer-se:\n"
            "a) procedência do pedido;\n"
            "b) condenação do réu;\n"
            "c) honorários."
        )
        result = apply_legal_heuristics(
            text, mode="forense", separate_enums=True,
        )
        assert "- " in result

    def test_not_applied_in_doutrina(self):
        text = (
            "Conceitos fundamentais:\n"
            "primeiro conceito;\n"
            "segundo conceito."
        )
        result = apply_legal_heuristics(
            text, mode="doutrina", separate_enums=True,
        )
        assert "- " not in result


class TestWrapInternalNotes:
    """M3 v4.1: Notas internas demarcadas em blockquote."""

    def test_observacoes_finais(self):
        text = (
            "Texto da peça.\n\n"
            "Observações finais de uso\n"
            "Este modelo deve ser adaptado.\n"
            "Verifique os prazos."
        )
        result = wrap_internal_notes(text)
        assert "> **Nota interna**" in result
        assert "> Este modelo deve ser adaptado." in result
        assert "> Verifique os prazos." in result

    def test_nota_adequacao(self):
        text = (
            "Texto principal.\n\n"
            "Nota de adequação\n"
            "Adaptar conforme o caso concreto."
        )
        result = wrap_internal_notes(text)
        assert "> **Nota interna**" in result
        assert "> Adaptar conforme" in result

    def test_instrucoes_protocolo(self):
        text = (
            "Texto.\n\n"
            "Instruções para protocolo\n"
            "Protocolar no prazo de 15 dias."
        )
        result = wrap_internal_notes(text)
        assert "> **Nota interna**" in result
        assert "> Protocolar no prazo" in result

    def test_normal_text_not_wrapped(self):
        text = "O réu deve pagar indenização.\nTexto normal."
        result = wrap_internal_notes(text)
        assert "> " not in result

    def test_heading_stops_note(self):
        text = (
            "Observações finais de uso\n"
            "Adaptar modelo.\n\n"
            "# Novo Título\n"
            "Conteúdo do título."
        )
        result = wrap_internal_notes(text)
        assert "> Adaptar modelo." in result
        assert "> # Novo Título" not in result
        assert "Conteúdo do título." in result

    def test_integrated_in_pipeline(self):
        text = (
            "DOS FATOS\n\nTexto.\n\n"
            "Observações finais de uso\n"
            "Verificar antes de protocolar."
        )
        result = apply_legal_heuristics(
            text, mode="forense", wrap_notes=True,
        )
        assert "> **Nota interna**" in result

    def test_not_applied_when_disabled(self):
        text = (
            "Observações finais de uso\n"
            "Verificar prazos."
        )
        result = apply_legal_heuristics(
            text, mode="forense", wrap_notes=False,
        )
        assert "> **Nota interna**" not in result

    def test_not_applied_in_doutrina(self):
        text = (
            "Observações finais de uso\n"
            "Verificar prazos."
        )
        result = apply_legal_heuristics(
            text, mode="doutrina", wrap_notes=True,
        )
        assert "> **Nota interna**" not in result


class TestGoogleMode:
    """F2: Modo 'google' — negrito inline, sem headings."""

    def test_enderecamento_bold_no_heading(self):
        text = "EXCELENTÍSSIMO SENHOR DOUTOR JUIZ DE DIREITO"
        result = apply_legal_heuristics(text, mode="google")
        assert "**EXCELENTÍSSIMO" in result
        assert not result.strip().startswith("#")

    def test_section_bold_no_heading(self):
        text = "DOS FATOS"
        result = apply_legal_heuristics(text, mode="google")
        assert "**DOS FATOS**" in result
        assert "##" not in result

    def test_numbered_section_bold(self):
        text = "1. DA SÍNTESE FÁTICA"
        result = apply_legal_heuristics(text, mode="google")
        assert "**1. DA SÍNTESE FÁTICA**" in result
        assert "#" not in result

    def test_subsection_bold(self):
        text = "3.1. Natureza do ato ilícito"
        result = apply_legal_heuristics(text, mode="google")
        assert "**3.1. Natureza do ato ilícito**" in result
        assert "#" not in result

    def test_titulo_peca_bold(self):
        text = "HABEAS CORPUS"
        result = apply_legal_heuristics(text, mode="google")
        assert "**HABEAS CORPUS**" in result
        assert "#" not in result

    def test_normal_text_unchanged(self):
        text = "O réu deve pagar indenização por danos morais."
        result = apply_legal_heuristics(text, mode="google")
        assert result.strip() == text
        assert "**" not in result

    def test_existing_heading_converted_to_bold(self):
        text = "## DOS PEDIDOS"
        result = apply_legal_heuristics(text, mode="google")
        assert "**DOS PEDIDOS**" in result
        assert "##" not in result

    def test_subsection_da_bold(self):
        text = "Da responsabilidade objetiva"
        result = apply_legal_heuristics(text, mode="google")
        assert "**Da responsabilidade objetiva**" in result

    def test_forense_mode_unchanged(self):
        """Modo forense continua usando headings."""
        text = "DOS FATOS"
        result = apply_legal_heuristics(text, mode="forense")
        assert result.strip().startswith("## ")

    def test_doutrina_mode_unchanged(self):
        """Modo doutrina continua usando headings."""
        text = "CAPÍTULO I - Introdução"
        result = apply_legal_heuristics(text, mode="doutrina")
        assert result.strip().startswith("# ")

    def test_processo_bold(self):
        text = "Processo de origem n.º 5550842-80.2025.8.09.0051"
        result = apply_legal_heuristics(text, mode="google")
        assert "**Processo de origem" in result

    def test_enumeration_not_bold(self):
        text = "a) primeiro item do pedido"
        result = apply_legal_heuristics(text, mode="google")
        assert "**" not in result


class TestItalicizeEmenta:
    """F3: Ementa/resumo da peça envolvida em itálico."""

    def test_ementa_between_title_and_body(self):
        text = (
            "PETIÇÃO INICIAL\n"
            "Ação de indenização por danos morais.\n"
            "\n"
            "JOÃO DA SILVA, já qualificado nos autos, vem..."
        )
        result = apply_legal_heuristics(text, mode="forense")
        assert "*Ação de indenização por danos morais.*" in result

    def test_ementa_multiple_lines(self):
        text = (
            "HABEAS CORPUS\n"
            "Constrangimento ilegal.\n"
            "Excesso de prazo.\n"
            "\n"
            "Trata-se de habeas corpus impetrado..."
        )
        result = apply_legal_heuristics(text, mode="forense")
        assert "*Constrangimento ilegal.*" in result
        assert "*Excesso de prazo.*" in result

    def test_no_ementa_when_no_title(self):
        text = "Texto normal sem título de peça.\nOutro parágrafo."
        result = apply_legal_heuristics(text, mode="forense")
        assert "*Texto normal" not in result

    def test_no_ementa_when_body_immediately_follows(self):
        text = (
            "SENTENÇA\n"
            "Trata-se de ação ordinária..."
        )
        result = apply_legal_heuristics(text, mode="forense")
        # Sem linhas entre título e corpo — nada para italicizar
        assert "*Trata-se" not in result

    def test_ementa_disabled(self):
        text = (
            "PETIÇÃO INICIAL\n"
            "Resumo da petição.\n"
            "\n"
            "JOÃO DA SILVA, já qualificado..."
        )
        result = apply_legal_heuristics(text, mode="forense", detect_ementa=False)
        assert "*Resumo da petição.*" not in result

    def test_ementa_in_google_mode(self):
        text = (
            "PETIÇÃO INICIAL\n"
            "Ação de cobrança.\n"
            "\n"
            "MARIA SOUZA, já qualificada nos autos..."
        )
        result = apply_legal_heuristics(text, mode="google")
        assert "*Ação de cobrança.*" in result

    def test_already_formatted_lines_skipped(self):
        text = (
            "HABEAS CORPUS\n"
            "*Já em itálico.*\n"
            "\n"
            "Trata-se de habeas corpus..."
        )
        result = apply_legal_heuristics(text, mode="forense")
        assert "**Já em itálico.*" not in result


class TestFormatSignatures:
    """F4: Formatar assinaturas com separador e negrito."""

    def test_nestes_termos(self):
        text = (
            "Texto do documento.\n\n"
            "Nestes termos, pede deferimento.\n"
            "Goiânia/GO, 31 de março de 2026\n"
            "DAVI MENDANHA LORERO\n"
            "OAB/GO n.º 41.757"
        )
        result = format_signatures(text)
        assert "---" in result
        assert "**DAVI MENDANHA LORERO**" in result
        assert "**OAB/GO n.º 41.757**" in result
        assert "Goiânia/GO, 31 de março de 2026" in result

    def test_termos_em_que(self):
        text = (
            "Conteúdo.\n\n"
            "Termos em que pede deferimento.\n"
            "MARIA DA SILVA"
        )
        result = format_signatures(text)
        assert "---" in result
        assert "**MARIA DA SILVA**" in result

    def test_atenciosamente(self):
        text = (
            "Conteúdo.\n\n"
            "Atenciosamente,\n"
            "JOÃO FERREIRA\n"
            "OAB/SP 123.456"
        )
        result = format_signatures(text)
        assert "---" in result
        assert "**JOÃO FERREIRA**" in result

    def test_no_signature_block(self):
        text = "Texto normal sem assinatura.\nOutro parágrafo."
        result = format_signatures(text)
        assert result == text
        assert "---" not in result

    def test_location_date_preserved(self):
        text = (
            "Texto.\n\n"
            "Pede deferimento.\n"
            "São Paulo/SP, 15 de janeiro de 2026\n"
            "ADVOGADO DA SILVA"
        )
        result = format_signatures(text)
        assert "São Paulo/SP, 15 de janeiro de 2026" in result

    def test_integrated_in_pipeline_forense(self):
        text = (
            "DOS FATOS\n\n"
            "Texto.\n\n"
            "Nestes termos, pede deferimento.\n"
            "ADVOGADO NOME"
        )
        result = apply_legal_heuristics(text, mode="forense")
        assert "---" in result
        assert "**ADVOGADO NOME**" in result

    def test_integrated_in_google_mode(self):
        text = (
            "Conteúdo.\n\n"
            "Nestes termos, pede deferimento.\n"
            "ADVOGADO NOME"
        )
        result = apply_legal_heuristics(text, mode="google")
        assert "---" in result
        assert "**ADVOGADO NOME**" in result


class TestRomanDecimalSubsections:
    """Sub-seções com numeração romana+decimal (II.1, III.2) → H3."""

    def test_ii_1_is_h3(self):
        text = "II.1 — Competência territorial"
        result = apply_legal_heuristics(text, mode="forense")
        assert result.strip().startswith("### ")

    def test_ii_2_is_h3(self):
        text = "II.2 — Legitimidade passiva"
        result = apply_legal_heuristics(text, mode="forense")
        assert result.strip().startswith("### ")

    def test_ii_3_is_h3(self):
        text = "II.3 — Prescrição"
        result = apply_legal_heuristics(text, mode="forense")
        assert result.strip().startswith("### ")

    def test_iii_1_is_h3(self):
        text = "III.1 – Dano material"
        result = apply_legal_heuristics(text, mode="forense")
        assert result.strip().startswith("### ")

    def test_iv_2_dot_is_h3(self):
        text = "IV.2. Nexo causal"
        result = apply_legal_heuristics(text, mode="forense")
        assert result.strip().startswith("### ")

    def test_roman_decimal_in_google_mode(self):
        text = "II.1 — Competência territorial"
        result = apply_legal_heuristics(text, mode="google")
        assert "**" in result
        assert "#" not in result

    def test_long_roman_decimal_not_heading(self):
        """Linhas longas com II.1 não devem virar heading."""
        text = "II.1 — " + "a" * 200
        result = apply_legal_heuristics(text, mode="forense")
        assert not result.strip().startswith("### ")


class TestTocRomanGaps:
    """TOC deve incluir seções com numeração romana mesmo com gaps."""

    def test_toc_includes_all_roman_sections(self):
        text = (
            "## I – DOS FATOS\n\nTexto.\n\n"
            "## II – DO DIREITO\n\nTexto.\n\n"
            "## III – DOS PEDIDOS\n\nTexto."
        )
        toc = generate_toc(text)
        assert "I – DOS FATOS" in toc
        assert "II – DO DIREITO" in toc
        assert "III – DOS PEDIDOS" in toc

    def test_roman_gap_filled(self):
        """Se existe ## V e ## VII, ## VI deve ser inserido."""
        text = (
            "## I – INTRODUÇÃO\n\nTexto.\n\n"
            "## II – QUADRO NORMATIVO\n\nTexto.\n\n"
            "## III – DOS FATOS\n\nTexto.\n\n"
            "## V – DOS PEDIDOS\n\nTexto.\n\n"
            "## VI – CONCLUSÃO\n\nTexto."
        )
        result = fill_heading_gaps(text)
        assert "## IV" in result
