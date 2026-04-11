"""Testes para o classificador semântico de callouts."""

from core.callout_classifier import apply_smart_callouts, classify_block


class TestClassifyBlock:
    def test_legislation_art(self):
        text = "Art. 50 do CC. Em caso de abuso..."
        assert classify_block(text) == "> [!QUOTE] Legislação"

    def test_legislation_paragraph(self):
        text = "§ 1º A pessoa jurídica responde..."
        assert classify_block(text) == "> [!QUOTE] Legislação"

    def test_sumula(self):
        text = "Súmula 403 do STJ. Independe de prova..."
        assert classify_block(text) == "> [!QUOTE] Súmula"

    def test_enunciado(self):
        text = "Enunciado 274 do CJF. Os direitos da personalidade..."
        assert classify_block(text) == "> [!QUOTE] Enunciado"

    def test_jurisprudencia(self):
        text = "STJ. 3ª Turma REsp 1.838.009/RJ, Rel. Min. Moura Ribeiro..."
        assert classify_block(text) == "> [!QUOTE] Jurisprudência"

    def test_questao_concurso(self):
        text = "(CESPE - 2023) A teoria da aparência aplica-se..."
        assert classify_block(text) == "> [!TIP] Questão de concurso"

    def test_warning_atencao(self):
        text = "Atenção: não confundir prescrição com decadência."
        assert classify_block(text) == "> [!WARNING] Atenção"

    def test_important(self):
        text = "Importante: a regra é inafastável."
        assert classify_block(text) == "> [!IMPORTANT]"

    def test_observacao(self):
        text = "OBS: este ponto é controverso na doutrina."
        assert classify_block(text) == "> [!NOTE]"

    def test_definicao(self):
        text = (
            "A desconsideração da personalidade jurídica consiste em "
            "afastar a autonomia patrimonial em casos de abuso."
        )
        assert classify_block(text) == "> [!INFO] Definição"

    def test_prosa_normal_no_callout(self):
        text = (
            "O direito civil brasileiro evoluiu significativamente "
            "ao longo do século XX, incorporando novos institutos."
        )
        assert classify_block(text) is None

    def test_empty_returns_none(self):
        assert classify_block("") is None
        assert classify_block("   ") is None


class TestApplySmartCallouts:
    def test_classifies_law_block(self):
        text = (
            "Texto introdutório.\n\n"
            "Art. 50 do CC. Em caso de abuso da personalidade.\n\n"
            "Texto seguinte."
        )
        result = apply_smart_callouts(text)
        assert "> [!QUOTE] Legislação" in result
        assert "> Art. 50 do CC" in result
        assert "Texto introdutório." in result
        assert "Texto seguinte." in result

    def test_keeps_prose_intact(self):
        text = (
            "Esta é uma prosa normal expositiva sobre direito civil. "
            "Não deve ser convertida em callout porque é texto corrido "
            "que integra o fluxo argumentativo do autor."
        )
        result = apply_smart_callouts(text)
        assert "[!NOTE]" not in result
        assert "[!INFO]" not in result

    def test_classifies_questao(self):
        text = "(CESPE - 2023) A pessoa jurídica responde objetivamente."
        result = apply_smart_callouts(text)
        assert "> [!TIP] Questão de concurso" in result

    def test_skips_existing_callouts(self):
        text = (
            "> [!INFO] Já é callout\n"
            "> Conteúdo existente.\n\n"
            "Prosa normal."
        )
        result = apply_smart_callouts(text)
        # Não deve duplicar
        assert result.count("[!INFO]") == 1

    def test_skips_headings(self):
        text = "## Capítulo 1\n\nProsa expositiva normal."
        result = apply_smart_callouts(text)
        assert "## Capítulo 1" in result
