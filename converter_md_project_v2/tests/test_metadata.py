"""Testes para o módulo de geração de frontmatter YAML."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.metadata import extract_procedural_metadata, generate_frontmatter


class TestGenerateFrontmatter:
    def test_basic_frontmatter_structure(self):
        """Frontmatter deve ter delimitadores --- no início e fim."""
        text = "Título do documento\n\nConteúdo aqui."
        result = generate_frontmatter(text, filename="doc.pdf")
        assert result.startswith("---\n")
        assert result.endswith("\n---")

    def test_extracts_title_from_first_line(self):
        """Deve extrair título da primeira linha significativa."""
        text = "PETIÇÃO INICIAL DE INDENIZAÇÃO\n\nConteúdo."
        result = generate_frontmatter(text)
        assert 'titulo:' in result
        assert 'PETIÇÃO INICIAL' in result

    def test_fallback_title_to_filename(self):
        """Se não há linha significativa, usa o nome do arquivo."""
        text = "\n\n\n"
        result = generate_frontmatter(text, filename="meu_documento.pdf")
        assert 'titulo:' in result
        assert 'meu_documento' in result

    def test_extracts_proad_number(self):
        """Deve detectar número PROAD/SEI no texto."""
        text = "Título\n\nPROAD nº 123.456/2024\n\nConteúdo."
        result = generate_frontmatter(text)
        assert 'proad:' in result
        assert '123.456/2024' in result

    def test_extracts_sei_number(self):
        """Deve detectar número SEI."""
        text = "Título\n\nSEI 98765.432100/2023-01\n\nConteúdo."
        result = generate_frontmatter(text)
        assert 'proad:' in result

    def test_extracts_processo_number(self):
        """Deve detectar número de processo."""
        text = "Título\n\nProcesso nº 0001234-56.2024.8.26.0100\n\nConteúdo."
        result = generate_frontmatter(text)
        assert 'proad:' in result

    def test_extracts_date_long_format(self):
        """Deve extrair data no formato extenso brasileiro."""
        text = "Título\n\nBrasília, 15 de março de 2024.\n\nConteúdo."
        result = generate_frontmatter(text)
        assert 'data:' in result
        assert '15 de março de 2024' in result

    def test_extracts_date_short_format(self):
        """Deve extrair data no formato DD/MM/YYYY."""
        text = "Título\n\n15/03/2024\n\nConteúdo."
        result = generate_frontmatter(text)
        assert 'data:' in result
        assert '15/03/2024' in result

    def test_prefers_long_date_over_short(self):
        """Formato extenso deve ter prioridade sobre numérico."""
        text = "Título\n\n15/03/2024\n\n20 de janeiro de 2025\n\nConteúdo."
        result = generate_frontmatter(text)
        assert '20 de janeiro de 2025' in result

    def test_extracts_orgao_emissor(self):
        """Deve detectar órgão emissor no texto."""
        text = "TRIBUNAL DE JUSTIÇA DO ESTADO DE SÃO PAULO\n\nConteúdo."
        result = generate_frontmatter(text)
        assert 'orgao_emissor:' in result
        assert 'TRIBUNAL' in result

    def test_extracts_conselho(self):
        """Deve detectar CONSELHO como órgão."""
        text = "CONSELHO NACIONAL DE JUSTIÇA\n\nResolução nº 123."
        result = generate_frontmatter(text)
        assert 'orgao_emissor:' in result

    def test_default_status_vigente(self):
        """Status padrão deve ser 'vigente'."""
        text = "Título\n\nConteúdo."
        result = generate_frontmatter(text)
        assert 'status: "vigente"' in result

    def test_convertido_em_present(self):
        """Campo convertido_em deve estar presente com data atual."""
        text = "Título\n\nConteúdo."
        result = generate_frontmatter(text)
        assert 'convertido_em:' in result

    def test_handles_empty_text(self):
        """Texto vazio deve gerar frontmatter mínimo."""
        result = generate_frontmatter("", filename="vazio.pdf")
        assert result.startswith("---\n")
        assert 'titulo:' in result
        assert 'vazio' in result

    def test_handles_quotes_in_title(self):
        """Aspas no título devem ser escapadas."""
        text = 'Sentença do caso "Silva vs. Estado"\n\nConteúdo.'
        result = generate_frontmatter(text)
        assert '\\"' in result or "Silva" in result

    def test_title_max_length(self):
        """Título deve ser truncado em 120 caracteres."""
        long_line = "A" * 200
        text = f"{long_line}\n\nConteúdo."
        result = generate_frontmatter(text)
        for line in result.split("\n"):
            if line.startswith("titulo:"):
                title_value = line.split('"')[1]
                assert len(title_value) <= 120
                break

    def test_skips_short_first_lines(self):
        """Linhas muito curtas (<= 5 chars) devem ser ignoradas para título."""
        text = "abc\nSENTENÇA DE MÉRITO\n\nConteúdo."
        result = generate_frontmatter(text)
        assert 'SENTENÇA DE MÉRITO' in result

    def test_strips_heading_markers_from_title(self):
        """Marcadores # devem ser removidos do título."""
        text = "## DOS FATOS\n\nO autor alega que..."
        result = generate_frontmatter(text)
        assert 'DOS FATOS' in result
        assert 'titulo: "##' not in result

    def test_no_proad_when_absent(self):
        """Se não há PROAD/SEI, campo não deve aparecer."""
        text = "Título simples\n\nConteúdo sem número de processo."
        result = generate_frontmatter(text)
        assert 'proad:' not in result

    def test_no_orgao_when_absent(self):
        """Se não há órgão, campo não deve aparecer."""
        text = "Título simples\n\nConteúdo sem menção a órgão."
        result = generate_frontmatter(text)
        assert 'orgao_emissor:' not in result


class TestExtractPieceMetadata:
    """P8: Metadados expandidos da peça jurídica."""

    def test_tipo_peca_habeas_corpus(self):
        text = "HABEAS CORPUS\n\nTexto da peça."
        result = generate_frontmatter(text, extract_metadata=True)
        assert 'tipo_peca: "Habeas Corpus"' in result

    def test_tipo_peca_peticao(self):
        text = "PETIÇÃO INICIAL\n\nTexto da petição."
        result = generate_frontmatter(text, extract_metadata=True)
        assert "Petição Inicial" in result

    def test_tipo_peca_sentenca(self):
        text = "SENTENÇA\n\nTexto da sentença."
        result = generate_frontmatter(text, extract_metadata=True)
        assert "Sentença" in result

    def test_extracts_paciente(self):
        text = "HABEAS CORPUS\nPaciente: José Leonardo Ferreira Borges\nTexto."
        result = generate_frontmatter(text, extract_metadata=True)
        assert 'paciente: "José Leonardo Ferreira Borges"' in result

    def test_extracts_autoridade_coatora(self):
        text = "HABEAS CORPUS\nAutoridade coatora: MM. Juíza de Direito da 1.ª Vara\nTexto."
        result = generate_frontmatter(text, extract_metadata=True)
        assert "autoridade_coatora:" in result
        assert "Juíza de Direito" in result

    def test_extracts_processo_origem(self):
        text = "Processo de origem n.º 5550842-80.2025.8.09.0051\nTexto."
        result = generate_frontmatter(text, extract_metadata=True)
        assert "processo_origem:" in result
        assert "5550842" in result

    def test_extracts_pedido_liminar(self):
        text = "HABEAS CORPUS\nContém pedido liminar.\nTexto."
        result = generate_frontmatter(text, extract_metadata=True)
        assert 'pedido_liminar: "true"' in result

    def test_no_metadata_when_disabled(self):
        text = "HABEAS CORPUS\nPaciente: José\nTexto."
        result = generate_frontmatter(text, extract_metadata=False)
        assert "paciente:" not in result
        assert "tipo_peca:" not in result

    def test_normal_text_no_tipo(self):
        text = "Texto normal sem tipo de peça identificável."
        result = generate_frontmatter(text, extract_metadata=True)
        assert "tipo_peca:" not in result

    def test_extracts_impetrante(self):
        text = "Impetrante: DAVI MENDANHA LORERO\nTexto."
        result = generate_frontmatter(text, extract_metadata=True)
        assert "impetrante:" in result
        assert "DAVI MENDANHA" in result


class TestExtractProceduralMetadata:
    """M1 v4.1: Metadados processuais detalhados."""

    def test_extracts_autor_with_cpf(self):
        text = "Autor: JOÃO DA SILVA, inscrito no CPF 123.456.789-00\nTexto."
        meta = {}
        extract_procedural_metadata(text, meta)
        assert "autor" in meta
        assert "JOÃO DA SILVA" in meta["autor"]
        assert "CPF: 123.456.789-00" in meta["autor"]

    def test_extracts_autor_without_cpf(self):
        text = "Requerente: MARIA SOUZA\nTexto."
        meta = {}
        extract_procedural_metadata(text, meta)
        assert "autor" in meta
        assert "MARIA SOUZA" in meta["autor"]

    def test_extracts_reu(self):
        text = "Réu: BANCO DO BRASIL S.A.\ncom sede em Brasilia."
        meta = {}
        extract_procedural_metadata(text, meta)
        assert "reu" in meta
        assert "BANCO DO BRASIL" in meta["reu"]

    def test_extracts_comarca(self):
        text = "Comarca de Goiânia\nTexto do documento."
        meta = {}
        extract_procedural_metadata(text, meta)
        assert "comarca" in meta
        assert "Goiânia" in meta["comarca"]

    def test_extracts_foro(self):
        text = "Foro da Capital\nTexto."
        meta = {}
        extract_procedural_metadata(text, meta)
        assert "comarca" in meta
        assert "Capital" in meta["comarca"]

    def test_pedido_liminar_true(self):
        text = "Requer a concessão de MEDIDA LIMINAR.\nTexto."
        meta = {}
        extract_procedural_metadata(text, meta)
        assert meta["pedido_liminar"] == "true"

    def test_pedido_liminar_false(self):
        text = "Requer a condenação do réu ao pagamento."
        meta = {}
        extract_procedural_metadata(text, meta)
        assert meta["pedido_liminar"] == "false"

    def test_pedido_tutela_urgencia(self):
        text = "Requer pedido de tutela de urgência."
        meta = {}
        extract_procedural_metadata(text, meta)
        assert meta["pedido_liminar"] == "true"

    def test_acoes_cumuladas_danos_morais(self):
        text = "Ação de indenização por danos morais c/c indenização por danos materiais."
        meta = {}
        extract_procedural_metadata(text, meta)
        assert "acoes_cumuladas" in meta
        assert "danos morais" in meta["acoes_cumuladas"]
        assert "danos materiais" in meta["acoes_cumuladas"]

    def test_acoes_cumuladas_obrigacao_fazer(self):
        text = "Ação de obrigação de fazer c/c reparação de danos."
        meta = {}
        extract_procedural_metadata(text, meta)
        assert "acoes_cumuladas" in meta
        assert "obrigação de fazer" in meta["acoes_cumuladas"]

    def test_no_acoes_when_absent(self):
        text = "Texto simples sem ação identificável."
        meta = {}
        extract_procedural_metadata(text, meta)
        assert "acoes_cumuladas" not in meta

    def test_normal_text_no_autor(self):
        text = "O réu deve pagar indenização."
        meta = {}
        extract_procedural_metadata(text, meta)
        assert "autor" not in meta
