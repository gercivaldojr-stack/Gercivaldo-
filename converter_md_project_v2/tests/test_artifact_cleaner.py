"""Testes para o limpador de artefatos."""

from core.artifact_cleaner import (
    clean_artifacts,
    remove_layout_artifacts,
    remove_spurious_metadata,
)


class TestRemoveSpuriousMetadata:
    def test_removes_resumo_palavras_chave(self):
        text = (
            "## Seção\n\n"
            "Texto normal.\n\n"
            "*Resumo: Este é o conteúdo. Palavras-chave: direito, civil.*\n\n"
            "Mais texto."
        )
        count, result = remove_spurious_metadata(text)
        assert count == 1
        assert "Resumo:" not in result
        assert "Palavras-chave:" not in result
        assert "Texto normal" in result
        assert "Mais texto" in result

    def test_removes_multiple_blocks(self):
        text = (
            "*Resumo: Bloco 1. Palavras-chave: a, b.*\n\n"
            "Texto.\n\n"
            "*Resumo: Bloco 2. Palavras-chave: c, d.*"
        )
        count, result = remove_spurious_metadata(text)
        assert count == 2
        assert "Resumo:" not in result

    def test_keeps_text_without_metadata(self):
        text = "## Seção\n\nProsa simples.\n\nMais prosa."
        count, result = remove_spurious_metadata(text)
        assert count == 0
        assert result == text

    def test_no_false_positive_on_real_text(self):
        text = "O resumo do contrato é claro. Palavras importantes."
        count, _ = remove_spurious_metadata(text)
        assert count == 0


class TestRemoveLayoutArtifacts:
    def test_removes_cs_civil_pattern(self):
        text = (
            "Texto antes.\n"
            "CS – CIVIL I 2025.2 | 42\n"
            "Texto depois."
        )
        count, result = remove_layout_artifacts(text)
        assert count == 1
        assert "CS – CIVIL I" not in result
        assert "Texto antes" in result
        assert "Texto depois" in result

    def test_removes_pipe_wrapped_header(self):
        text = (
            "Conteúdo válido.\n"
            "| CS – CIVIL I 2025.2 | 7 |\n"
            "Mais conteúdo."
        )
        count, result = remove_layout_artifacts(text)
        assert count >= 1
        assert "Conteúdo válido" in result

    def test_removes_pagina_label(self):
        text = "Linha A.\nPágina 42\nLinha B."
        count, result = remove_layout_artifacts(text)
        assert count == 1
        assert "Página 42" not in result

    def test_removes_isolated_page_number(self):
        text = "Parágrafo final.\n\n42\n\nNovo parágrafo."
        count, result = remove_layout_artifacts(text)
        assert count == 1
        assert "Parágrafo final" in result
        assert "Novo parágrafo" in result

    def test_keeps_inline_numbers(self):
        text = "O Art. 42 do CC dispõe sobre o tema."
        count, result = remove_layout_artifacts(text)
        assert count == 0
        assert "42" in result

    def test_removes_dash_page_number(self):
        text = "Texto.\n— 15 —\nMais texto."
        count, result = remove_layout_artifacts(text)
        assert count == 1
        assert "— 15 —" not in result


class TestCleanArtifacts:
    def test_full_pipeline(self):
        text = (
            "## Capítulo\n\n"
            "Texto principal.\n\n"
            "*Resumo: Conteúdo. Palavras-chave: tag1, tag2.*\n\n"
            "Mais texto."
        )
        result = clean_artifacts(text)
        assert "Resumo:" not in result
        assert "Texto principal" in result
        assert "Mais texto" in result

    def test_normalizes_blank_lines_after_removal(self):
        text = (
            "Linha A.\n\n\n\n\n"
            "*Resumo: x. Palavras-chave: y.*\n\n\n\n\n"
            "Linha B."
        )
        result = clean_artifacts(text)
        # Não deve ter mais que 3 newlines consecutivas
        assert "\n\n\n\n" not in result
