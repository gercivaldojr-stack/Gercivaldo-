"""Testes para o módulo de separação de peças processuais."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.piece_separator import format_separated_pieces, separate_pieces


class TestSeparatePieces:
    def test_single_piece(self):
        text = "Texto de um documento simples sem peças identificáveis."
        pieces = separate_pieces(text)
        assert len(pieces) == 1
        assert pieces[0]["title"] == "Documento Principal"

    def test_multiple_pieces(self):
        text = (
            "PETIÇÃO INICIAL\n\n"
            "Conteúdo da petição inicial com fatos e argumentos.\n\n"
            "CONTESTAÇÃO\n\n"
            "Conteúdo da contestação com defesa e argumentos.\n\n"
            "SENTENÇA\n\n"
            "Conteúdo da sentença com dispositivo final."
        )
        pieces = separate_pieces(text)
        assert len(pieces) == 3
        assert "PETIÇÃO INICIAL" in pieces[0]["title"]
        assert "CONTESTAÇÃO" in pieces[1]["title"]
        assert "SENTENÇA" in pieces[2]["title"]

    def test_empty_text(self):
        assert separate_pieces("") == []
        assert separate_pieces("   ") == []

    def test_piece_with_recurso(self):
        text = (
            "SENTENÇA\n\n"
            "O juiz decide...\n\n"
            "RECURSO DE APELAÇÃO\n\n"
            "O apelante recorre..."
        )
        pieces = separate_pieces(text)
        assert len(pieces) == 2

    def test_long_line_not_piece_start(self):
        text = "SENTENÇA " + "a" * 200
        pieces = separate_pieces(text)
        # Linha muito longa não deve ser tratada como início de peça
        assert len(pieces) == 1


class TestFormatSeparatedPieces:
    def test_format_multiple(self):
        pieces = [
            {"title": "Petição Inicial", "content": "Conteúdo 1"},
            {"title": "Contestação", "content": "Conteúdo 2"},
        ]
        result = format_separated_pieces(pieces)
        assert "# Petição Inicial" in result
        assert "# Contestação" in result
        assert "---" in result

    def test_format_empty(self):
        assert format_separated_pieces([]) == ""

    def test_format_single(self):
        pieces = [{"title": "Documento", "content": "Conteúdo"}]
        result = format_separated_pieces(pieces)
        assert "# Documento" in result
        assert "---" not in result
