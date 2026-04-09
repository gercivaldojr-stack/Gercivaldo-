"""Testes para o módulo de otimização RAG."""

from core.rag_optimizer import (
    apply_semantic_formatting,
    detect_legal_area,
    extract_tags,
    generate_section_summaries,
    insert_callouts,
    normalize_footnotes,
    optimize_for_rag,
)


class TestDetectLegalArea:
    def test_detect_civil(self):
        text = (
            "O contrato de compra e venda celebrado entre as partes "
            "gera obrigação de entrega do bem. A responsabilidade civil "
            "decorre do inadimplemento contratual conforme o código civil."
        )
        area, sub = detect_legal_area(text)
        assert area == "Direito Civil"

    def test_detect_penal(self):
        text = (
            "O réu praticou crime de homicídio qualificado com dolo "
            "eventual. A pena de reclusão foi fixada conforme o código "
            "penal. A tipicidade e antijuridicidade foram comprovadas."
        )
        area, _ = detect_legal_area(text)
        assert area == "Direito Penal"

    def test_detect_constitucional(self):
        text = (
            "A ação direta de inconstitucionalidade questiona a "
            "emenda constitucional que viola cláusula pétrea. Os "
            "direitos fundamentais previstos na constituição devem ser "
            "preservados pelo controle de constitucionalidade."
        )
        area, _ = detect_legal_area(text)
        assert area == "Direito Constitucional"

    def test_detect_trabalhista(self):
        text = (
            "O empregado foi dispensado sem justa causa pelo empregador. "
            "O vínculo empregatício foi reconhecido conforme a CLT. "
            "FGTS e aviso prévio são devidos na rescisão trabalhista."
        )
        area, _ = detect_legal_area(text)
        assert area == "Direito do Trabalho"

    def test_empty_returns_default(self):
        area, sub = detect_legal_area("")
        assert area == "Direito Civil"
        assert sub == "Geral"

    def test_detects_subarea(self):
        text = (
            "A responsabilidade civil por dano moral e material "
            "decorre do nexo causal entre a conduta e o dano. "
            "A indenização deve ser fixada com razoabilidade."
        )
        area, sub = detect_legal_area(text)
        assert area == "Direito Civil"
        assert sub == "Responsabilidade Civil"


class TestExtractTags:
    def test_extracts_tags(self):
        text = (
            "O contrato de compra e venda estabelece obrigações "
            "para ambas as partes contratantes. O contrato deve "
            "respeitar a função social. As obrigações contratuais "
            "incluem entrega e pagamento."
        )
        tags = extract_tags(text, max_tags=3)
        assert len(tags) <= 3
        assert isinstance(tags, list)
        assert all(isinstance(t, str) for t in tags)

    def test_respects_max_tags(self):
        text = "palavra1 " * 50 + "palavra2 " * 40
        tags = extract_tags(text, max_tags=2)
        assert len(tags) <= 2

    def test_empty_text(self):
        tags = extract_tags("")
        assert tags == []


class TestApplySemanticFormatting:
    def test_italicize_latin(self):
        text = "O princípio pacta sunt servanda é fundamental."
        result = apply_semantic_formatting(text)
        assert "*pacta sunt servanda*" in result

    def test_no_italic_in_headings(self):
        text = "## Pacta sunt servanda no direito"
        result = apply_semantic_formatting(text)
        assert result.startswith("## ")
        assert "*pacta" not in result

    def test_bold_first_concept(self):
        text = (
            "A responsabilidade civil é instituto fundamental. "
            "A responsabilidade civil abrange danos morais."
        )
        result = apply_semantic_formatting(text)
        assert "**responsabilidade civil**" in result
        assert result.count("**responsabilidade civil**") == 1

    def test_bold_tribunals(self):
        text = "O STF decidiu no julgamento que o STJ já havia confirmado."
        result = apply_semantic_formatting(text)
        assert "**STF**" in result
        assert "**STJ**" in result


class TestInsertCallouts:
    def test_definition_callout(self):
        text = "Prescrição é a perda do direito de ação pelo decurso do tempo."
        result = insert_callouts(text)
        assert "> [!NOTE] Definição" in result

    def test_alert_callout(self):
        text = "ATENÇÃO: não confundir prescrição com decadência."
        result = insert_callouts(text)
        assert "> [!IMPORTANT]" in result

    def test_no_callout_in_heading(self):
        text = "## Prescrição é um instituto"
        result = insert_callouts(text)
        assert "[!NOTE]" not in result

    def test_no_callout_in_short_text(self):
        text = "Prescrição é curta."
        result = insert_callouts(text)
        assert "[!NOTE]" not in result


class TestGenerateSectionSummaries:
    def test_generates_summary(self):
        text = (
            "## Introdução\n\n"
            "O presente estudo analisa a responsabilidade civil "
            "no direito brasileiro contemporâneo.\n\n"
            "## Metodologia\n\n"
            "A pesquisa utilizou método dedutivo.\n"
        )
        result = generate_section_summaries(text)
        assert "*Resumo:" in result

    def test_no_summary_single_section(self):
        text = "## Única Seção\n\nTexto da seção."
        result = generate_section_summaries(text)
        assert "*Resumo:" not in result


class TestNormalizeFootnotes:
    def test_basic_footnote(self):
        text = (
            "Conforme a doutrina (1) e a jurisprudência.\n\n"
            "1. TARTUCE, Flávio. Manual de Direito Civil."
        )
        result = normalize_footnotes(text)
        assert "[^1]" in result
        assert "[^1]: TARTUCE" in result

    def test_multiple_footnotes(self):
        text = (
            "Texto com nota (1) e outra nota (2).\n\n"
            "1. Referência 1.\n"
            "2. Referência 2."
        )
        result = normalize_footnotes(text)
        assert "[^1]" in result
        assert "[^2]" in result


class TestOptimizeForRag:
    def test_full_pipeline(self):
        text = (
            "---\ntitulo: \"Test\"\nstatus: \"vigente\"\n---\n\n"
            "## Introdução\n\n"
            "A responsabilidade civil é instituto do código civil. "
            "O princípio pacta sunt servanda é fundamental. "
            "Conforme ensina FLÁVIO TARTUCE, as obrigações devem "
            "ser cumpridas. O STJ já decidiu nesse sentido (1).\n\n"
            "## Conclusão\n\n"
            "O estudo demonstra a importância do tema.\n\n"
            "1. TARTUCE, Flávio. Manual de Direito Civil."
        )
        result = optimize_for_rag(text)
        assert "area:" in result
        assert "subarea:" in result
        assert "tags:" in result
        assert "ultima_revisao:" in result

    def test_without_frontmatter(self):
        text = (
            "## Seção\n\n"
            "Texto simples sem frontmatter.\n\n"
            "## Outra\n\nMais texto."
        )
        result = optimize_for_rag(text)
        assert "area:" not in result
        assert "*Resumo:" in result

    def test_pipeline_integration(self):
        """rag_optimize=True no pipeline deve funcionar."""
        from core.pipeline import convert_document
        result = convert_document(
            file_bytes=b"Texto sobre responsabilidade civil.\n",
            filename="test.txt",
            rag_optimize=True,
        )
        assert result.success
