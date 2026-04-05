"""Testes para detecção automática de idioma."""

from unittest.mock import MagicMock

from core.lang_detector import (
    detect_document_language,
    detect_language,
    detect_language_from_page,
)


class TestDetectLanguage:
    def test_detect_portuguese(self):
        text = (
            "O autor celebrou contrato de prestação de serviços com o réu. "
            "O tribunal determinou que o processo deve ser julgado pela "
            "primeira vara cível. A sentença foi proferida pelo juiz "
            "nos termos do artigo da lei. O recurso não foi provido."
        )
        assert detect_language(text) == "por"

    def test_detect_english(self):
        text = (
            "The court has determined that the case shall be heard "
            "in the district court. The judge ruled that the law "
            "requires the defendant to appear before the court. "
            "This section provides for the rights of the accused."
        )
        assert detect_language(text) == "eng"

    def test_detect_spanish(self):
        text = (
            "El tribunal ha determinado que el recurso del demandado "
            "no tiene fundamento legal. La sentencia fue dictada por "
            "el juez conforme a la ley vigente. Los artículos del "
            "código establecen las obligaciones de las partes."
        )
        assert detect_language(text) == "spa"

    def test_detect_french(self):
        text = (
            "Le tribunal a décidé que cette affaire relève de la "
            "compétence du juge. La loi dispose que les parties "
            "doivent comparaître dans les délais prévus par "
            "article du code. La décision est définitive."
        )
        assert detect_language(text) == "fra"

    def test_detect_german(self):
        text = (
            "Das Gericht hat entschieden dass der Angeklagte "
            "nicht schuldig ist. Der Richter hat das Urteil "
            "gemäß dem Gesetz und dem Artikel gesprochen. "
            "Die Entscheidung ist rechtskräftig und endgültig."
        )
        assert detect_language(text) == "deu"

    def test_detect_italian(self):
        text = (
            "Il tribunale ha stabilito che il ricorso non ha "
            "fondamento legale. La sentenza è stata pronunciata "
            "dal giudice conformemente alla legge vigente. "
            "Gli articoli del codice stabiliscono gli obblighi."
        )
        assert detect_language(text) == "ita"

    def test_empty_text_returns_default(self):
        assert detect_language("") == "por"
        assert detect_language(None) == "por"

    def test_short_text_returns_default(self):
        assert detect_language("Hello world") == "por"
        assert detect_language("Texto curto") == "por"

    def test_ambiguous_text_returns_default(self):
        # Mistura de idiomas — ambíguo
        text = "legal process tribunal court judge sentença lei artigo"
        result = detect_language(text)
        assert result == "por"  # default quando ambíguo


class TestDetectLanguageFromPage:
    def test_detect_language_from_page_mock(self):
        page = MagicMock()
        page.get_text.return_value = (
            "O tribunal determinou que o processo deve ser julgado. "
            "O juiz proferiu sentença nos termos da lei. "
            "O recurso não foi provido pelo tribunal."
        )
        assert detect_language_from_page(page) == "por"

    def test_page_error_returns_default(self):
        page = MagicMock()
        page.get_text.side_effect = RuntimeError("fail")
        assert detect_language_from_page(page) == "por"


class TestDetectDocumentLanguage:
    def test_detect_document_language_mock(self):
        doc = MagicMock()
        doc.__len__ = MagicMock(return_value=3)
        pages = []
        for _ in range(3):
            p = MagicMock()
            p.get_text.return_value = (
                "O tribunal determinou que o processo de recurso "
                "deve ser julgado pela primeira vara cível da "
                "comarca. A sentença foi proferida pelo juiz."
            )
            pages.append(p)
        doc.__getitem__ = MagicMock(side_effect=lambda i: pages[i])
        assert detect_document_language(doc) == "por"

    def test_empty_doc_returns_default(self):
        doc = MagicMock()
        doc.__len__ = MagicMock(return_value=0)
        assert detect_document_language(doc) == "por"

    def test_auto_in_extract_text(self):
        """ocr_lang='auto' is accepted without error in extract_text."""
        from core.extractors import extract_text
        result = extract_text(
            file_bytes=b"Texto simples de teste.",
            filename="test.txt",
            ocr_lang="auto",
        )
        assert "Texto simples" in result
