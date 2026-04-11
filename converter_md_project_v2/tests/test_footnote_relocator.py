"""Testes para o reconciliador de notas de rodapé."""

from core.footnote_relocator import (
    _has_inline_reference,
    relocate_orphan_footnotes,
)


class TestHasInlineReference:
    def test_finds_inline(self):
        text = "Texto com chamada[^1] no meio."
        assert _has_inline_reference(text, "1") is True

    def test_misses_definition(self):
        text = "[^1]: Definição"
        assert _has_inline_reference(text, "1") is False

    def test_not_found(self):
        text = "Texto sem chamadas."
        assert _has_inline_reference(text, "1") is False


class TestRelocateOrphanFootnotes:
    def test_relocates_orphan(self):
        text = (
            "Texto principal sem chamadas inline.\n\n"
            "Mais um parágrafo.\n\n"
            "[^1]: Definição da nota órfã.\n"
        )
        result = relocate_orphan_footnotes(text)
        assert "> [!NOTE]" in result
        assert "**Nota:** Definição da nota órfã." in result
        assert "[^1]:" not in result

    def test_keeps_used_footnote(self):
        text = (
            "Texto com referência[^1] correta.\n\n"
            "[^1]: Conteúdo da nota.\n"
        )
        result = relocate_orphan_footnotes(text)
        assert "[^1]: Conteúdo da nota." in result
        assert "**Nota:**" not in result

    def test_mixed_orphan_and_used(self):
        text = (
            "Texto com referência[^1] correta.\n\n"
            "Outro parágrafo.\n\n"
            "[^1]: Nota usada.\n"
            "[^2]: Nota órfã.\n"
        )
        result = relocate_orphan_footnotes(text)
        assert "[^1]: Nota usada." in result
        assert "**Nota:** Nota órfã." in result
        assert "[^2]:" not in result

    def test_no_footnotes_unchanged(self):
        text = "## Capítulo\n\nProsa simples sem notas."
        result = relocate_orphan_footnotes(text)
        assert result.strip() == text.strip()
