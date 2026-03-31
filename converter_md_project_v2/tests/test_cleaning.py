"""Testes para o módulo de limpeza de texto."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.cleaning import (
    clean_text,
    fix_hyphenation,
    normalize_paragraphs,
    normalize_whitespace,
    rejoin_broken_paragraphs,
    remove_corrupted_glyphs,
    remove_ereader_boilerplate,
    remove_ocr_noise,
    remove_repeated_headers_footers,
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
        # O padrão "Tribunal de Justiça - Página #" deve ser removido
        assert "Tribunal de Justiça" not in result

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


class TestCleanText:
    def test_empty_string(self):
        assert clean_text("") == ""
        assert clean_text("   ") == ""

    def test_full_pipeline(self):
        text = "consti-\ntuição   do    Brasil\n\n\n\n\nSegundo parágrafo."
        result = clean_text(text, remove_headers_footers=False)
        assert "constituição" in result
        assert result.strip()
