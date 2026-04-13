# flake8: noqa: E501
"""Teste end-to-end com cenários reais de DOCX do JusBrasil.

Simula a conversão de "Capítulo 11. Serviços Públicos" de Gabriel Pires
em Manual de Direito Administrativo (JusBrasil) e valida correções P1-P10.
"""

from core.pipeline import convert_document


JUSBRASIL_CHAPTER = """PIRES, Gabriel. Capítulo 11. Serviços Públicos In: PIRES, Gabriel. Manual de Direito Administrativo. São Paulo (SP):Editora Saraiva, 2023. Disponível em: httpswww.jusbrasil.com.br/doutrina/manual-de-direito-administrativo/1339456630 Acesso em: 4 de Novembro de 2025.

Capítulo 11. Serviços Públicos

Clique aqui e acesse o vídeo sobre o tema.

11.1. Relevância e atualidade da questão A noção jurídica de serviço público tem especial relevância no direito administrativo moderno, pois representa a interface entre o Estado e a sociedade em matéria de atividades essenciais à coletividade.

11.2. Conceito

O serviço público é toda atividade prestada pela Administração Pública com o objetivo de satisfazer necessidades essenciais da coletividade, sob regime de direito público. O conceito envolve três elementos principais:

a)um elemento subjetivo: atividades administrativas do Estado;
b)um elemento material: satisfação de necessidades coletivas;
c)um elemento formal: regime jurídico de direito público;
d)um elemento finalístico: prestação à coletividade;
e)um elemento econômico: geralmente com contraprestação.

11.3. Classificação

Os serviços públicos podem ser classificados em diversas categorias segundo critérios distintos.

11.4. Princípios

Os princípios fundamentais dos serviços públicos incluem continuidade, regularidade, eficiência.

11.5. Formas de prestação

As formas de prestação variam conforme o regime adotado pelo ente federativo.

11.6.1. Concessão

A concessão de serviço público é a forma mais tradicional de delegação da prestação.

### 11.7. Regulação

A regulação dos serviços públicos é competência de agências reguladoras.

### 11.9. Considerações finais

O estudo dos serviços públicos revela a complexidade do tema no direito administrativo contemporâneo, especialmente em face das transformações sociais e tecnológicas que impactam a atuação estatal moderna.

A ouvidoria funciona como canal de comunicação entre o cidadão e a Administração 1 , permitindo o recebimento de reclamações, sugestões e denúncias. No regime de publicização 1 previsto no art. 14, a autarquia presta contas à ouvidoria. A Administração direta também deve qualquer outra 2 forma de controle social. O Art. 15 estabelece que as ouvidorias deverão receber manifestações externas qualificadas e encaminhá-las aos setores competentes da administração para tratamento adequado, com garantia de resposta ao interessado no prazo legal, preservando o anonimato quando solicitado pelo manifestante e observando os princípios da legalidade, impessoalidade, moralidade, publicidade e eficiência.
"""


class TestJusBrasilChapter:
    def _convert(self):
        return convert_document(
            file_bytes=JUSBRASIL_CHAPTER.encode("utf-8"),
            filename="Capitulo_11_Servicos_Publicos.txt",
            mode="doutrina",
        )

    def test_p1_title_not_bibliographic_reference(self):
        """P1: título não deve ser a referência bibliográfica truncada."""
        r = self._convert()
        assert r.success
        # Não deve começar com "PIRES, Gabriel"
        assert 'titulo: "PIRES, Gabriel' not in r.markdown
        # Não deve truncar no meio de palavra tipo "Edit" (de "Editora")
        assert 'titulo: "' in r.markdown
        # Aceitar qualquer título razoável que não seja a referência
        import re
        m = re.search(r'titulo: "([^"]+)"', r.markdown)
        assert m, "No title in frontmatter"
        title = m.group(1)
        # Título não deve conter "In:" (marker de referência bibliográfica)
        assert "In:" not in title, f"Title is biblio reference: {title}"

    def test_p2_biblio_reference_removed_from_body(self):
        """P2: bloco de referência "PIRES, Gabriel... Acesso em:" removido."""
        r = self._convert()
        # A linha "PIRES, Gabriel. Capítulo..." com "Disponível em" e
        # "Acesso em" deveria ser removida do corpo
        body_lines = [
            ln for ln in r.markdown.split("\n")
            if not ln.strip().startswith("---") and not ln.startswith("titulo:")
            and not ln.startswith("status:") and not ln.startswith("convertido_em:")
        ]
        body_text = "\n".join(body_lines)
        assert "Acesso em: 4 de Novembro de 2025" not in body_text

    def test_p3_h1_before_body(self):
        """P3: H1 deve vir antes do corpo, imediatamente após frontmatter."""
        r = self._convert()
        lines = r.markdown.split("\n")
        # Encontrar posição do primeiro H1
        h1_idx = -1
        for i, ln in enumerate(lines):
            if ln.strip().startswith("# ") and not ln.strip().startswith("## "):
                h1_idx = i
                break
        assert h1_idx != -1, "Nenhum H1 encontrado"
        # Verificar que antes do H1 só há frontmatter ou linhas vazias
        for j in range(h1_idx):
            line = lines[j].strip()
            if line and not line.startswith("---") and not line.startswith(("titulo:", "status:", "convertido_em:", "data:", "area:", "subarea:", "tags:", "ultima_revisao:", "orgao_emissor:", "proad:")):
                assert False, f"Conteúdo antes do H1 linha {j}: {line!r}"

    def test_p4_heading_not_fused_with_paragraph(self):
        """P4: ### 11.1. + corpo devem estar separados."""
        r = self._convert()
        # Buscar "### 11.1" — não deve ter "A noção jurídica" na mesma linha
        for line in r.markdown.split("\n"):
            if line.strip().startswith("### 11.1"):
                assert "noção jurídica" not in line, (
                    f"Heading fundido com corpo: {line}"
                )

    def test_p5_nested_numbered_sections_as_headings(self):
        """P5: 11.2., 11.3., 11.4., 11.5., 11.6.1 devem virar headings."""
        r = self._convert()
        # Todas estas seções devem aparecer como headings (### ou ##)
        for num in ["11.2", "11.3", "11.4", "11.5"]:
            # Buscar heading contendo esse número
            found = False
            for line in r.markdown.split("\n"):
                if line.strip().startswith("#") and f"{num}." in line:
                    found = True
                    break
            assert found, f"Seção {num} não virou heading"

    def test_p6_list_items_separated(self):
        """P6: a), b), c) devem ter espaço ou estar em linhas separadas."""
        r = self._convert()
        # Não deve ter "a)um" colado sem espaço
        assert "a)um elemento" not in r.markdown
        assert "b)um elemento" not in r.markdown

    def test_p7_url_corrected(self):
        """P7: 'httpswww.jusbrasil' deve ser corrigido para 'https://www.jusbrasil'."""
        r = self._convert()
        # A URL na referência pode ter sido removida (P2), mas se aparecer
        # em outro lugar deve estar corrigida
        assert "httpswww." not in r.markdown
        # Se a URL persistir, deve ter :// correto
        if "jusbrasil" in r.markdown:
            assert "https://www.jusbrasil" in r.markdown or "http://" in r.markdown

    def test_p8_ui_text_removed(self):
        """P8: 'Clique aqui e acesse o vídeo' deve ser removido."""
        r = self._convert()
        assert "Clique aqui e acesse" not in r.markdown

    def test_p10_inline_footnote_numbers_handled(self):
        """P10: números "1", "2", "3" soltos no meio do texto tratados."""
        r = self._convert()
        # "publicização 1 previsto" não deve permanecer — ou remove o "1",
        # ou vira [^1]
        assert "publicização 1 previsto" not in r.markdown
        assert "qualquer outra 2 forma" not in r.markdown
