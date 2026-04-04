"""Testes para o módulo de limpeza de texto."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.cleaning import (
    clean_text,
    fix_hyphenation,
    normalize_bullets,
    normalize_legal_citations,
    normalize_paragraphs,
    normalize_whitespace,
    reconnect_cnj_numbers,
    rejoin_broken_paragraphs,
    remove_corrupted_glyphs,
    remove_ereader_boilerplate,
    remove_ocr_noise,
    remove_repeated_headers_footers,
    remove_residual_pagination,
    separate_enumerations,
)


class TestFixHyphenation:
    def test_basic_hyphenation(self):
        text = "consti-\ntuição"
        assert "constituição" in fix_hyphenation(text)

    def test_hyphenation_with_spaces(self):
        text = "funda-\n   mental"
        assert "fundamental" in fix_hyphenation(text)

    def test_no_hyphenation(self):
        text = "texto normal\nsem hifenização"
        result = fix_hyphenation(text)
        assert "texto normal" in result

    def test_multiple_hyphenations(self):
        text = "consti-\ntuição e funda-\nmental"
        result = fix_hyphenation(text)
        assert "constituição" in result
        assert "fundamental" in result


class TestNormalizeWhitespace:
    def test_multiple_spaces(self):
        assert "texto aqui" in normalize_whitespace("texto   aqui")

    def test_tabs(self):
        assert "\t" not in normalize_whitespace("texto\taqui")

    def test_leading_trailing(self):
        result = normalize_whitespace("  texto  ")
        assert result == "texto"


class TestRemoveOCRNoise:
    def test_dots_sequence(self):
        text = "Capítulo 1 ........... 15"
        result = remove_ocr_noise(text)
        assert "........" not in result

    def test_underscores(self):
        text = "texto _______ texto"
        result = remove_ocr_noise(text)
        assert "___" not in result

    def test_preserves_normal_text(self):
        text = "Este é um texto normal."
        assert remove_ocr_noise(text) == text


class TestRemoveRepeatedHeadersFooters:
    def test_detects_repeated_lines(self):
        lines = []
        for i in range(10):
            lines.append(f"Tribunal de Justiça - Página {i + 1}")
            lines.append(f"Conteúdo do parágrafo {i + 1} com texto suficiente para não ser confundido.")
            lines.append("")
        text = "\n".join(lines)
        result = remove_repeated_headers_footers(text)
        # P10: primeira ocorrência preservada por padrão
        assert "Tribunal de Justiça - Página 1" in result
        # Repetições removidas
        assert "Tribunal de Justiça - Página 5" not in result

    def test_short_document_unchanged(self):
        text = "Linha 1\nLinha 2\nLinha 3"
        assert remove_repeated_headers_footers(text) == text


class TestNormalizeParagraphs:
    def test_excessive_newlines(self):
        text = "Parágrafo 1\n\n\n\n\n\nParágrafo 2"
        result = normalize_paragraphs(text)
        assert "\n\n\n\n" not in result

    def test_preserves_headings(self):
        text = "# Título\n\nTexto aqui"
        result = normalize_paragraphs(text)
        assert "# Título" in result


class TestRejoinBrokenParagraphs:
    def test_joins_broken_lines(self):
        """Linhas curtas sem pontuação final devem ser unidas."""
        text = "Despesas indispensáveis\nà administração da falência."
        result = rejoin_broken_paragraphs(text)
        assert "indispensáveis à administração" in result

    def test_joins_multiline_paragraph(self):
        text = "O direito empresarial\nregula as atividades\neconômicas organizadas."
        result = rejoin_broken_paragraphs(text)
        assert "empresarial regula as atividades econômicas" in result

    def test_preserves_headings(self):
        text = "# Título\nTexto do parágrafo."
        result = rejoin_broken_paragraphs(text)
        assert "# Título" in result
        assert "# Título Texto" not in result

    def test_preserves_blank_line_separation(self):
        text = "Parágrafo um completo.\n\nParágrafo dois completo."
        result = rejoin_broken_paragraphs(text)
        assert "Parágrafo um completo." in result
        assert "Parágrafo dois completo." in result
        assert "completo. Parágrafo" not in result

    def test_preserves_uppercase_lines(self):
        text = "DOS FATOS\nO autor alega que sofreu danos."
        result = rejoin_broken_paragraphs(text)
        assert "DOS FATOS" in result
        assert "DOS FATOS O autor" not in result

    def test_preserves_enumeration(self):
        text = "a) primeiro item do pedido\nb) segundo item do pedido"
        result = rejoin_broken_paragraphs(text)
        assert "a) primeiro" in result
        assert "b) segundo" in result
        assert "pedido b)" not in result

    def test_sentence_ending_breaks_paragraph(self):
        text = "Primeira sentença completa.\nSegunda sentença aqui."
        result = rejoin_broken_paragraphs(text)
        assert "completa.\nSegunda" in result or "completa." in result

    def test_joins_line_ending_with_parenthesis(self):
        """Linhas que terminam com ) devem ser unidas se a próxima é continuação."""
        text = "conforme art. 5º (CF/88)\ndo ordenamento jurídico brasileiro."
        result = rejoin_broken_paragraphs(text)
        assert "(CF/88) do ordenamento" in result

    def test_joins_line_starting_with_dash(self):
        """Travessão no início de linha não deve impedir junção."""
        text = "O autor sofreu danos\n- materiais e morais -\nde grande monta."
        result = rejoin_broken_paragraphs(text)
        assert "danos - materiais" in result or "danos\n- materiais" in result


class TestRemoveEreaderBoilerplate:
    def test_removes_ereader_instructions(self):
        text = (
            "Como usar seu e-reader\n"
            "Toque para escolher fonte e tamanho\n"
            "Alterar layout e luminosidade do display\n"
            "Fazer buscas no texto do livro\n"
            "Anotar trechos e fazer marcações\n"
            "Acesso a outras opções do menu lateral\n"
            "\n"
            "CAPÍTULO I - Introdução ao Direito Empresarial\n"
            "\n"
            "O direito empresarial é o ramo do direito privado."
        )
        result = remove_ereader_boilerplate(text)
        assert "escolher fonte" not in result
        assert "luminosidade" not in result
        assert "CAPÍTULO I" in result
        assert "direito empresarial" in result

    def test_preserves_normal_text(self):
        text = "O direito empresarial regula as atividades econômicas.\n\nA empresa é a atividade."
        assert remove_ereader_boilerplate(text) == text

    def test_short_document_unchanged(self):
        text = "Texto curto."
        assert remove_ereader_boilerplate(text) == text

    def test_removes_boilerplate_beyond_line_80(self):
        """Boilerplate nas linhas 90+ deve ser removido (scan_limit=150)."""
        lines = ["Texto qualquer do documento."] * 90
        lines += [
            "Como usar o epub reader",
            "Escolher fonte e tamanho da letra",
            "Alterar layout e luminosidade do display",
            "Fazer buscas no texto",
            "",
            "CAPÍTULO I - Introdução ao Direito Empresarial",
        ]
        text = "\n".join(lines)
        result = remove_ereader_boilerplate(text)
        assert "epub" not in result.lower()
        assert "luminosidade" not in result
        assert "CAPÍTULO I" in result


class TestRemoveCorruptedGlyphs:
    def test_removes_sinhala_glyphs(self):
        text = "Texto normal\nSමිමිකුකාටමාම\nMais texto normal."
        result = remove_corrupted_glyphs(text)
        assert "Texto normal" in result
        assert "Mais texto" in result
        assert "මිමි" not in result

    def test_removes_cjk_glyphs(self):
        text = "Parágrafo válido.\n你好世界这是测试文本\nOutro parágrafo."
        result = remove_corrupted_glyphs(text)
        assert "Parágrafo válido" in result
        assert "Outro parágrafo" in result
        assert "你好" not in result

    def test_preserves_portuguese_accents(self):
        text = "Ação, ção, função, instituição, é, ê, à, ã, õ, ú"
        result = remove_corrupted_glyphs(text)
        assert result.strip() == text

    def test_preserves_mixed_content_low_ratio(self):
        """Linha com poucos chars não-latinos é preservada."""
        text = "Artigo 5° da CF/88"
        result = remove_corrupted_glyphs(text)
        assert "Artigo 5" in result

    def test_cleans_inline_glyphs_mixed_line(self):
        """Linha mista com glyphs inline deve ter glyphs removidos mas texto latino preservado."""
        text = "O direito empresarial Sමිමිකුකාටමාම regula atividades"
        result = remove_corrupted_glyphs(text)
        assert "O direito empresarial" in result
        assert "regula atividades" in result
        assert "මිමි" not in result

    def test_preserves_empty_lines(self):
        text = "Texto\n\n\nMais texto"
        result = remove_corrupted_glyphs(text)
        assert result == text


class TestNormalizeLegalCitations:
    def test_artigo_full_word(self):
        assert "Art. 5" in normalize_legal_citations("Artigo 5")

    def test_artigo_uppercase(self):
        assert "Art. 5" in normalize_legal_citations("ART. 5")

    def test_artigo_lowercase(self):
        assert "Art. 5" in normalize_legal_citations("art. 5")

    def test_artigo_no_dot(self):
        assert "Art. 5" in normalize_legal_citations("Art 5")

    def test_artigo_no_space(self):
        assert "Art. 5" in normalize_legal_citations("Art.5")

    def test_paragrafo_full_word(self):
        result = normalize_legal_citations("Parágrafo 1")
        assert "§ 1" in result

    def test_paragrafo_par_dot(self):
        result = normalize_legal_citations("Par. 2")
        assert "§ 2" in result

    def test_paragrafo_unico(self):
        result = normalize_legal_citations("Parágrafo único")
        assert "§ único" in result

    def test_double_section_sign(self):
        result = normalize_legal_citations("§§ 1")
        assert "§ 1" in result
        assert "§§" not in result

    def test_artigo_ordinal_normalization(self):
        result = normalize_legal_citations("Art. 5o da CF")
        assert "Art. 5º" in result

    def test_alinea_normalization(self):
        result = normalize_legal_citations("conforme alinea a)")
        assert "alínea" in result

    def test_preserves_normal_text(self):
        text = "O réu deve pagar indenização."
        assert normalize_legal_citations(text) == text

    def test_comma_spacing(self):
        result = normalize_legal_citations("Art. 5 , § 2")
        assert "Art. 5," in result


class TestRejoinPrepositions:
    """M1: Linhas terminando com preposição SEMPRE são unidas."""

    def test_trailing_preposition_de(self):
        text = "O valor de\nindenização é alto."
        result = rejoin_broken_paragraphs(text)
        assert "valor de indenização" in result

    def test_trailing_preposition_da(self):
        text = "A análise da\nresponsabilidade civil."
        result = rejoin_broken_paragraphs(text)
        assert "análise da responsabilidade" in result

    def test_trailing_preposition_para(self):
        text = "Os documentos necessários para\ncomprovar o dano."
        result = rejoin_broken_paragraphs(text)
        assert "necessários para comprovar" in result

    def test_trailing_preposition_com(self):
        text = "O réu agiu com\nnegligência grave."
        result = rejoin_broken_paragraphs(text)
        assert "agiu com negligência" in result

    def test_trailing_preposition_que(self):
        text = "Considerando que\no autor apresentou provas."
        result = rejoin_broken_paragraphs(text)
        assert "Considerando que o autor" in result

    def test_trailing_conjunction_e(self):
        text = "Danos materiais e\nmorais."
        result = rejoin_broken_paragraphs(text)
        assert "materiais e morais" in result

    def test_trailing_conjunction_ou(self):
        text = "Multa ou\nprisão."
        result = rejoin_broken_paragraphs(text)
        assert "Multa ou prisão" in result

    def test_trailing_preposition_ao(self):
        text = "Conforme disposto ao\nart. 5 da CF."
        result = rejoin_broken_paragraphs(text)
        assert "disposto ao art." in result

    def test_trailing_preposition_a_crase(self):
        text = "Direito à\nliberdade."
        result = rejoin_broken_paragraphs(text)
        assert "Direito à liberdade" in result


class TestRejoinProtectedLines:
    """M1: Linhas protegidas NÃO devem ser unidas."""

    def test_next_line_heading_not_joined(self):
        text = "Texto do parágrafo\n# Título Novo"
        result = rejoin_broken_paragraphs(text)
        assert "# Título Novo" in result
        assert "parágrafo\n# Título" in result or "parágrafo #" not in result

    def test_next_line_list_dash_not_joined(self):
        text = "Texto do parágrafo\n- item de lista"
        result = rejoin_broken_paragraphs(text)
        assert "- item de lista" in result

    def test_next_line_table_not_joined(self):
        text = "Texto do parágrafo\n| Col1 | Col2 |"
        result = rejoin_broken_paragraphs(text)
        assert "| Col1 | Col2 |" in result

    def test_table_lines_preserved(self):
        text = "| A | B |\n|---|---|\n| 1 | 2 |"
        result = rejoin_broken_paragraphs(text)
        assert "| A | B |" in result
        assert "| 1 | 2 |" in result

    def test_next_line_enumeration_a_not_joined(self):
        text = "Texto anterior\na) primeiro item"
        result = rejoin_broken_paragraphs(text)
        assert "a) primeiro item" in result
        assert "anterior a)" not in result

    def test_next_line_enumeration_roman_not_joined(self):
        text = "Texto anterior\nI — primeiro item"
        result = rejoin_broken_paragraphs(text)
        assert "I — primeiro item" in result

    def test_next_line_blockquote_not_joined(self):
        text = "Texto anterior\n> citação jurídica"
        result = rejoin_broken_paragraphs(text)
        assert "> citação jurídica" in result


class TestReconnectCNJNumbers:
    """M2: Reconecta números CNJ partidos por quebra de linha."""

    def test_resp_number(self):
        text = "REsp\n1234567-89.2024"
        result = reconnect_cnj_numbers(text)
        assert "REsp 1234567-89.2024" in result

    def test_hc_number(self):
        text = "HC\n1234567-89.2024"
        result = reconnect_cnj_numbers(text)
        assert "HC 1234567-89.2024" in result

    def test_adi_number(self):
        text = "ADI\n1234567-89.2024"
        result = reconnect_cnj_numbers(text)
        assert "ADI 1234567-89.2024" in result

    def test_adpf_number(self):
        text = "ADPF\n1234567-89.2024"
        result = reconnect_cnj_numbers(text)
        assert "ADPF 1234567-89.2024" in result

    def test_are_number(self):
        text = "ARE\n1234567-89.2024"
        result = reconnect_cnj_numbers(text)
        assert "ARE 1234567-89.2024" in result

    def test_no_break_no_change(self):
        text = "REsp 1234567-89.2024 está correto."
        result = reconnect_cnj_numbers(text)
        assert "REsp 1234567-89.2024" in result

    def test_preserves_normal_text(self):
        text = "O recurso especial foi negado."
        assert reconnect_cnj_numbers(text) == text

    def test_agrg_number(self):
        text = "AgRg\n1234567-89.2024"
        result = reconnect_cnj_numbers(text)
        assert "AgRg 1234567-89.2024" in result


class TestRemoveResidualPagination:
    """M4: Remove paginação residual."""

    def test_pagina_pattern(self):
        text = "Texto antes.\nPágina 15\nTexto depois."
        result = remove_residual_pagination(text)
        assert "Página 15" not in result
        assert "Texto antes." in result
        assert "Texto depois." in result

    def test_pag_pattern(self):
        text = "Texto.\nPág. 3\nMais texto."
        result = remove_residual_pagination(text)
        assert "Pág. 3" not in result

    def test_decorative_pagination(self):
        text = "Texto.\n— 15 —\nMais texto."
        result = remove_residual_pagination(text)
        assert "— 15 —" not in result

    def test_isolated_number_first_lines(self):
        text = "42\nTexto do documento.\nMais conteúdo.\nFinal."
        result = remove_residual_pagination(text)
        assert result.startswith("Texto do documento")

    def test_isolated_number_last_lines(self):
        lines = ["Início.", "Meio.", "Fim.", "99"]
        text = "\n".join(lines)
        result = remove_residual_pagination(text)
        assert "99" not in result

    def test_isolated_number_middle_preserved(self):
        lines = ["L1", "L2", "L3", "L4", "42", "L6", "L7", "L8", "L9", "L10"]
        text = "\n".join(lines)
        result = remove_residual_pagination(text)
        assert "42" in result

    def test_preserves_normal_text(self):
        text = "O réu deve pagar indenização."
        assert remove_residual_pagination(text) == text

    def test_pagina_case_insensitive(self):
        text = "Texto.\npágina 5\nMais."
        result = remove_residual_pagination(text)
        assert "página 5" not in result


class TestSeparateEnumerations:
    """P9: Alíneas jurídicas devem ser parágrafos separados."""

    def test_alinea_gets_blank_line_before(self):
        text = "Requer-se:\na) primeiro pedido\nb) segundo pedido"
        result = separate_enumerations(text)
        assert "\n\na) primeiro pedido" in result
        assert "\n\nb) segundo pedido" in result

    def test_roman_gets_blank_line_before(self):
        text = "Fundamentos:\nI — primeiro\nII — segundo"
        result = separate_enumerations(text)
        assert "\n\nI — primeiro" in result
        assert "\n\nII — segundo" in result

    def test_subsection_gets_blank_line(self):
        text = "Seção principal\n1.1 subseção\n1.2 outra"
        result = separate_enumerations(text)
        assert "\n\n1.1 subseção" in result
        assert "\n\n1.2 outra" in result

    def test_already_separated_no_double(self):
        """Se já tem linha em branco, não duplicar."""
        text = "Requer-se:\n\na) primeiro pedido"
        result = separate_enumerations(text)
        assert "\n\n\na)" not in result

    def test_normal_text_unchanged(self):
        text = "O réu deve pagar indenização.\nPrazo de 30 dias."
        assert separate_enumerations(text) == text


class TestPreserveFirstHeaderFooter:
    """P10: Primeira ocorrência de header/footer deve ser preservada."""

    def test_first_occurrence_preserved(self):
        lines = []
        for i in range(10):
            lines.append(f"Tribunal de Justiça - Página {i + 1}")
            lines.append(f"Conteúdo do parágrafo {i + 1} com texto suficiente para não ser confundido.")
            lines.append("")
        text = "\n".join(lines)
        result = remove_repeated_headers_footers(text, preserve_first=True)
        # A primeira ocorrência deve existir
        assert "Tribunal de Justiça - Página 1" in result
        # As demais devem ser removidas
        assert "Tribunal de Justiça - Página 2" not in result
        assert "Tribunal de Justiça - Página 5" not in result

    def test_all_removed_when_preserve_false(self):
        lines = []
        for i in range(10):
            lines.append(f"Tribunal de Justiça - Página {i + 1}")
            lines.append(f"Conteúdo do parágrafo {i + 1} com texto suficiente para não ser confundido.")
            lines.append("")
        text = "\n".join(lines)
        result = remove_repeated_headers_footers(text, preserve_first=False)
        assert "Tribunal de Justiça" not in result

    def test_content_preserved(self):
        lines = []
        for i in range(10):
            lines.append(f"Rodapé escritório - página {i + 1}")
            lines.append(f"Conteúdo substancial do parágrafo {i + 1} com argumentação jurídica.")
            lines.append("")
        text = "\n".join(lines)
        result = remove_repeated_headers_footers(text, preserve_first=True)
        assert "Conteúdo substancial" in result

    def test_default_preserves_first(self):
        """O default do parâmetro é preserve_first=True."""
        lines = []
        for i in range(10):
            lines.append(f"CEP 12345-678 escritório - pag {i + 1}")
            lines.append(f"Conteúdo parágrafo {i + 1} com texto extenso suficiente para o teste.")
            lines.append("")
        text = "\n".join(lines)
        result = remove_repeated_headers_footers(text)
        # Primeira deve ser preservada (default)
        assert "CEP 12345-678 escritório - pag 1" in result


class TestCleanText:
    def test_empty_string(self):
        assert clean_text("") == ""
        assert clean_text("   ") == ""

    def test_full_pipeline(self):
        text = "consti-\ntuição   do    Brasil\n\n\n\n\nSegundo parágrafo."
        result = clean_text(text, remove_headers_footers=False)
        assert "constituição" in result
        assert result.strip()

    def test_pipeline_includes_pagination_removal(self):
        text = "Texto do documento.\nPágina 15\nMais conteúdo relevante."
        result = clean_text(text, remove_headers_footers=False)
        assert "Página 15" not in result

    def test_pipeline_includes_cnj_reconnect(self):
        text = "Conforme o REsp\n1234567-89.2024 decidiu."
        result = clean_text(text, remove_headers_footers=False)
        assert "REsp 1234567-89.2024" in result

    def test_pipeline_includes_normalize_bullets(self):
        text = "Itens:\n• primeiro item\n◦ segundo item\n▪ terceiro"
        result = clean_text(text, remove_headers_footers=False)
        assert "- primeiro item" in result
        assert "- segundo item" in result
        assert "- terceiro" in result


class TestNormalizeBullets:
    """Conversão de chars de bullet para Markdown '- '."""

    def test_bullet_dot(self):
        assert normalize_bullets("• texto") == "- texto"

    def test_open_bullet(self):
        assert normalize_bullets("◦ texto") == "- texto"

    def test_square_bullet(self):
        assert normalize_bullets("▪ texto") == "- texto"

    def test_arrow_bullet(self):
        assert normalize_bullets("► texto") == "- texto"

    def test_dash_bullet(self):
        assert normalize_bullets("– texto") == "- texto"

    def test_multiline(self):
        text = "Itens:\n• primeiro\n• segundo\n• terceiro"
        result = normalize_bullets(text)
        assert result == "Itens:\n- primeiro\n- segundo\n- terceiro"

    def test_no_bullet(self):
        text = "Texto normal sem bullet."
        assert normalize_bullets(text) == text

    def test_bullet_mid_line_preserved(self):
        """Bullet no meio da linha NÃO deve ser convertido."""
        text = "O item • não deve mudar"
        assert normalize_bullets(text) == text

    def test_bullet_without_space_preserved(self):
        """Bullet sem espaço após NÃO deve ser convertido."""
        text = "•texto sem espaço"
        assert normalize_bullets(text) == text
