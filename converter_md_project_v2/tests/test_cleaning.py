"""Testes para o módulo de limpeza de texto."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.cleaning import (
    clean_text,
    fix_hyphenation,
    normalize_paragraphs,
    normalize_whitespace,
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

    def test_joins_broken_paragraph(self):
        text = "Esta é uma linha que não termina com pontuação\ne continua aqui na próxima linha."
        result = normalize_paragraphs(text)
        assert "pontuação e continua" in result


class TestCleanText:
    def test_empty_string(self):
        assert clean_text("") == ""
        assert clean_text("   ") == ""

    def test_full_pipeline(self):
        text = "consti-\ntuição   do    Brasil\n\n\n\n\nSegundo parágrafo."
        result = clean_text(text, remove_headers_footers=False)
        assert "constituição" in result
        assert result.strip()
