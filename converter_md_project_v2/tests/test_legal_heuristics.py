"""Testes para o módulo de heurísticas jurídicas."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.legal_heuristics import (
    apply_legal_heuristics,
    detect_blockquotes,
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


class TestSeparateEnumeratedItems:
    def test_colon_followed_by_semicolons_becomes_list(self):
        text = "Requer o autor:\na citação do réu;\no reconhecimento da incidência;\na procedência do pedido."
        result = separate_enumerated_items(text)
        assert "- " in result
        assert "\n\n" in result

    def test_sequential_semicolons_get_blank_lines(self):
        text = "primeiro item;\nsegundo item;\nterceiro item."
        result = separate_enumerated_items(text)
        # Blank lines inserted between semicolon-terminated items
        lines = result.split("\n")
        blank_found = any(l.strip() == "" for l in lines)
        assert blank_found

    def test_single_semicolon_sentence_unchanged(self):
        text = "O autor celebrou contrato; porém, não houve adimplemento."
        result = separate_enumerated_items(text)
        assert result == text

    def test_heading_not_merged_with_items(self):
        text = "## DOS PEDIDOS\nprimeiro pedido;\nsegundo pedido;"
        result = separate_enumerated_items(text)
        assert "## DOS PEDIDOS" in result

    def test_integrated_in_pipeline(self):
        from core.pipeline import convert_document

        content = (
            "DOS PEDIDOS\n\n"
            "a condenação do réu;\n"
            "o pagamento de indenização;\n"
            "os honorários advocatícios."
        )
        result = convert_document(
            file_bytes=content.encode("utf-8"),
            filename="pedidos.txt",
            mode="forense",
        )
        assert result.success
        # Semicolons should have blank lines between items
        lines = result.markdown.split("\n")
        semicolon_lines = [i for i, l in enumerate(lines) if l.strip().endswith(";")]
        if semicolon_lines:
            # At least one blank line should follow a semicolon line
            has_blank_after = any(
                i + 1 < len(lines) and lines[i + 1].strip() == ""
                for i in semicolon_lines
            )
            assert has_blank_after


class TestWrapInternalNotes:
    def test_observacoes_finais_wrapped(self):
        text = "## OBSERVAÇÕES FINAIS DE USO DA MINUTA\nO capítulo dos juros foi reforçado."
        result = wrap_internal_notes(text)
        assert "Nota interna" in result
        assert "> O capítulo dos juros" in result

    def test_nota_adequacao_wrapped(self):
        text = "## NOTA DE ADEQUAÇÃO\nEsta minuta foi aprimorada."
        result = wrap_internal_notes(text)
        assert "Nota interna" in result
        assert "> Esta minuta" in result

    def test_instrucoes_protocolo_wrapped(self):
        text = "## INSTRUÇÕES PARA PROTOCOLO\nVerificar antes de protocolar."
        result = wrap_internal_notes(text)
        assert "Nota interna" in result

    def test_regular_section_not_wrapped(self):
        text = "## DOS FATOS\nO autor é produtor rural."
        result = wrap_internal_notes(text)
        assert "Nota interna" not in result
        assert "> O autor" not in result

    def test_internal_block_ends_at_next_heading(self):
        text = (
            "## OBSERVAÇÕES FINAIS DE USO\n"
            "Texto interno.\n"
            "## DOS PEDIDOS\n"
            "Texto normal."
        )
        result = wrap_internal_notes(text)
        assert "> Texto interno" in result
        assert "> Texto normal" not in result

    def test_empty_lines_in_internal_block(self):
        text = "## OBSERVAÇÕES FINAIS DE USO\nPrimeiro parágrafo.\n\nSegundo parágrafo."
        result = wrap_internal_notes(text)
        assert "> Primeiro parágrafo" in result
        assert "> Segundo parágrafo" in result
        # Empty line becomes >
        assert "\n>\n" in result

    def test_integrated_in_pipeline(self):
        from core.pipeline import convert_document

        # Use heading markers so heuristics preserve them as-is
        content = (
            "## DOS FATOS\n\nTexto normal.\n\n"
            "## OBSERVAÇÕES FINAIS DE USO DA MINUTA\n\n"
            "Texto da nota interna."
        )
        result = convert_document(
            file_bytes=content.encode("utf-8"),
            filename="minuta.md",
            mode="forense",
        )
        assert result.success
        assert "Nota interna" in result.markdown
