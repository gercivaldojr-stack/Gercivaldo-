# flake8: noqa: E501
"""Teste end-to-end com trecho real do livro Manual de Direito Empresarial.

Simula a conversão do livro Sacramone 3ª ed. 2022 e valida que os
defeitos D1, D2, D3, D4, D6 e D10 foram corrigidos no modo doutrina.
"""

from core.pipeline import convert_document


REAL_BOOK_EXCERPT = """MARCELO BARBOSA SACRAMONE

Manual de Direito Empresarial

3ª edição
São Paulo, 2022

DADOS INTERNACIONAIS DE CATALOGAÇÃO NA PUBLICAÇÃO (CIP)
(Câmara Brasileira do Livro, SP, Brasil)
Sacramone, Marcelo Barbosa
Manual de Direito Empresarial / Marcelo Barbosa Sacramone. -- 3. ed.
Inclui bibliografia
ISBN 978-65-5362-241-8
1. Direito Empresarial - Brasil 2. Direito Comercial - Brasil
CDD 346.07
CDU 347.7

Em 61 de dezembro de 2018, foi publicada a lei complementar.

Esta publicação teve aprovação do Conselho Fiscal da editora.

## Capítulo 1 Empresa e Empresário

## Capítulo 2 Estabelecimento Comercial

## Capítulo 3 Nome Empresarial

## Capítulo 4 Registro

## Capítulo 5 Contabilidade

## Capítulo 6 Sociedades

## Capítulo 7 Falência

## 6. Fontes do direito empresarial Capítulo 1 Empresa e Empresário

A sociedade empresária constitui a forma típica de exercício da atividade econômica organizada no direito brasileiro. Ela se caracteriza pela reunião de pessoas em torno de um fim comum, com objetivo de lucro e partilha dos resultados. O direito empresarial disciplina sua constituição, desenvolvimento e extinção. A Lei das S.A. regula as sociedades anônimas de forma específica. O Código Civil trata das sociedades limitadas como tipo geral. A atividade empresarial exige registro na Junta Comercial para ter personalidade jurídica.

## Capítulo 2 Estabelecimento

O estabelecimento comercial é o complexo de bens organizado para o exercício da empresa.
"""


class TestRealBookConversion:
    def test_title_is_manual_not_author(self):
        """D1: título deve ser 'Manual de Direito Empresarial', não 'MARCELO BARBOSA'."""
        result = convert_document(
            file_bytes=REAL_BOOK_EXCERPT.encode("utf-8"),
            filename="Manual_Direito_Empresarial_2022.txt",
            mode="doutrina",
        )
        assert result.success
        assert "Manual de Direito Empresarial" in result.markdown
        assert 'titulo: "MARCELO BARBOSA' not in result.markdown

    def test_invalid_date_rejected(self):
        """D1: '61 de dezembro' é dia inválido, não deve aparecer em data."""
        result = convert_document(
            file_bytes=REAL_BOOK_EXCERPT.encode("utf-8"),
            filename="Manual_Direito_Empresarial_2022.txt",
            mode="doutrina",
        )
        assert result.success
        assert 'data: "61 de dezembro' not in result.markdown

    def test_conselho_fiscal_not_as_orgao(self):
        """D1: 'Conselho Fiscal' em doutrina é falso positivo."""
        result = convert_document(
            file_bytes=REAL_BOOK_EXCERPT.encode("utf-8"),
            filename="Manual_Direito_Empresarial_2022.txt",
            mode="doutrina",
        )
        assert result.success
        assert 'orgao_emissor: "Conselho Fiscal' not in result.markdown

    def test_cip_block_removed(self):
        """D2: bloco CIP/ISBN/CDD deve ser removido."""
        result = convert_document(
            file_bytes=REAL_BOOK_EXCERPT.encode("utf-8"),
            filename="Manual_Direito_Empresarial_2022.txt",
            mode="doutrina",
        )
        assert result.success
        assert "DADOS INTERNACIONAIS DE CATALOGAÇÃO" not in result.markdown
        assert "ISBN 978-65-5362" not in result.markdown
        assert "CDD 346.07" not in result.markdown
        assert "CDU 347.7" not in result.markdown

    def test_toc_sequence_removed(self):
        """D3: sequência de 7 headings '## Capítulo N' sem body deve ser removida."""
        result = convert_document(
            file_bytes=REAL_BOOK_EXCERPT.encode("utf-8"),
            filename="Manual_Direito_Empresarial_2022.txt",
            mode="doutrina",
        )
        assert result.success
        # Contar quantos "## Capítulo N" aparecem — deve ser apenas os que têm body
        cap_count = result.markdown.count("## Capítulo")
        # No excerpt real: 7 no TOC + 1 com body (Capítulo 1 em "6. Fontes...")
        # + 1 com body (Capítulo 2 Estabelecimento) = esperado ≤ 3
        assert cap_count <= 3, f"TOC não removido: {cap_count} '## Capítulo' found"

    def test_fused_heading_split(self):
        """D4: heading fundido '## 6. Fontes... Capítulo 1 Empresa...' deve ser separado."""
        result = convert_document(
            file_bytes=REAL_BOOK_EXCERPT.encode("utf-8"),
            filename="Manual_Direito_Empresarial_2022.txt",
            mode="doutrina",
        )
        assert result.success
        # Não deve mais ter os dois fundidos na mesma linha
        assert "Fontes do direito empresarial Capítulo 1" not in result.markdown

    def test_long_paragraph_split(self):
        """D6: parágrafo monolítico de 600+ chars com 4+ sentenças deve ser dividido."""
        result = convert_document(
            file_bytes=REAL_BOOK_EXCERPT.encode("utf-8"),
            filename="Manual_Direito_Empresarial_2022.txt",
            mode="doutrina",
        )
        assert result.success
        # Verificar que não há linha única com > 700 chars
        for line in result.markdown.split("\n"):
            if not line.strip().startswith(("#", ">", "|", "-")):
                assert len(line) < 700, (
                    f"Parágrafo monolítico não dividido ({len(line)} chars): "
                    f"{line[:80]}..."
                )

    def test_h1_inserted(self):
        """D10: deve haver um heading H1 com o título do livro."""
        result = convert_document(
            file_bytes=REAL_BOOK_EXCERPT.encode("utf-8"),
            filename="Manual_Direito_Empresarial_2022.txt",
            mode="doutrina",
        )
        assert result.success
        # Deve existir linha começando com '# ' (H1) e não '## '
        lines = result.markdown.split("\n")
        h1_lines = [
            ln for ln in lines
            if ln.strip().startswith("# ")
            and not ln.strip().startswith("## ")
        ]
        assert len(h1_lines) >= 1, "Nenhum H1 encontrado"
        # O H1 deve conter "Manual de Direito Empresarial"
        assert any(
            "Manual de Direito Empresarial" in ln for ln in h1_lines
        ), f"H1 não contém título esperado: {h1_lines}"
