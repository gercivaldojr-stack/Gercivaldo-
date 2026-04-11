"""Testes para o validador de hierarquia de headings."""

from core.heading_validator import (
    ensure_heading_blank_lines,
    fix_heading_level_jumps,
    normalize_heading_hierarchy,
    remove_duplicate_numbering,
)


class TestRemoveDuplicateNumbering:
    def test_removes_duplicate_h3(self):
        text = "### 3.1. ### 3.1. Fonte primária"
        count, result = remove_duplicate_numbering(text)
        assert count == 1
        assert result == "### 3.1. Fonte primária"

    def test_removes_duplicate_h2(self):
        text = "## 1. ## 1. Capítulo Inicial"
        count, result = remove_duplicate_numbering(text)
        assert count == 1
        assert "## 1. Capítulo Inicial" in result

    def test_keeps_normal_heading(self):
        text = "### 3.1. Fonte primária"
        count, result = remove_duplicate_numbering(text)
        assert count == 0
        assert result == text


class TestFixHeadingLevelJumps:
    def test_fixes_h2_to_h4_jump(self):
        text = "## Capítulo 1\n\n#### Subseção sem H3 intermediário"
        count, result = fix_heading_level_jumps(text)
        assert count == 1
        assert "### Subseção" in result
        assert "#### " not in result

    def test_keeps_valid_progression(self):
        text = "## H2\n\n### H3\n\n#### H4"
        count, result = fix_heading_level_jumps(text)
        assert count == 0
        assert result == text

    def test_first_heading_not_promoted(self):
        text = "#### Heading inicial nivel 4"
        count, result = fix_heading_level_jumps(text)
        assert count == 0
        assert result == text


class TestEnsureHeadingBlankLines:
    def test_adds_blank_before(self):
        text = "Texto colado.\n## Heading"
        count, result = ensure_heading_blank_lines(text)
        assert count >= 1
        assert "Texto colado.\n\n## Heading" in result

    def test_adds_blank_after(self):
        text = "## Heading\nTexto colado."
        count, result = ensure_heading_blank_lines(text)
        assert count >= 1
        assert "## Heading\n\nTexto colado." in result

    def test_keeps_already_correct(self):
        text = "Texto.\n\n## Heading\n\nMais texto."
        count, result = ensure_heading_blank_lines(text)
        assert count == 0
        assert result == text


class TestNormalizeHeadingHierarchy:
    def test_full_pipeline(self):
        text = (
            "Texto.\n"
            "## Capítulo\n"
            "Mais texto.\n"
            "#### Subseção sem H3"
        )
        result = normalize_heading_hierarchy(text)
        # Não deve ter saltos
        lines = result.split("\n")
        levels = [
            len(ln) - len(ln.lstrip("#"))
            for ln in lines if ln.strip().startswith("#")
        ]
        for i in range(1, len(levels)):
            assert levels[i] - levels[i - 1] <= 1
