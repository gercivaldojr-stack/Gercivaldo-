"""
Interface Streamlit para conversão de documentos jurídicos para Markdown.
"""

import io
import logging
import sys
import zipfile
from pathlib import Path

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from core.pipeline import convert_document  # noqa: E402

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# ============================================================
# Configuração da página
# ============================================================

st.set_page_config(
    page_title="Conversor Jurídico → Markdown",
    page_icon="⚖️",
    layout="wide",
)

# ============================================================
# CSS customizado
# ============================================================

st.markdown("""
<style>
    .stMarkdown pre {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 16px;
        font-size: 14px;
        line-height: 1.6;
        max-height: 600px;
        overflow-y: auto;
    }
    .success-box {
        padding: 12px;
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        border-radius: 4px;
        margin: 8px 0;
    }
    .error-box {
        padding: 12px;
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        border-radius: 4px;
        margin: 8px 0;
    }
    .stats-box {
        padding: 8px 12px;
        background-color: #e2e3e5;
        border-radius: 4px;
        font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# Interface principal
# ============================================================

st.title("⚖️ Conversor de Documentos Jurídicos → Markdown")
st.caption("Converta PDFs, DOCX, TXT e Markdown para Markdown limpo e estruturado.")

# ============================================================
# Sidebar — Configurações
# ============================================================

with st.sidebar:
    st.header("Configurações")

    mode = st.radio(
        "Modo de heurísticas",
        options=["forense", "doutrina", "google"],
        index=0,
        help="**Forense**: peças processuais com headings (#/##/###)\n\n"
             "**Doutrina**: livros e artigos jurídicos (capítulos, seções)\n\n"
             "**Google**: estilo Google Drive — negrito inline, sem headings",
    )

    separate_pieces = st.checkbox(
        "Separar peças processuais",
        value=False,
        help="Detecta e separa múltiplas peças dentro de um mesmo documento.",
    )

    remove_hf = st.checkbox(
        "Remover cabeçalhos/rodapés repetidos",
        value=True,
        help="Remove cabeçalhos e rodapés que se repetem entre páginas. "
             "A primeira ocorrência é preservada.",
    )

    detect_citations = st.checkbox(
        "Detectar citações jurisprudenciais como blockquote",
        value=True,
        disabled=(mode != "forense"),
        help="Detecta citações de julgados (No HC ..., No REsp ...) "
             "e formata como blockquote Markdown. Apenas no modo forense.",
    )

    extract_metadata = st.checkbox(
        "Extrair metadados da peça",
        value=False,
        help="Extrai campos adicionais no frontmatter: tipo_peca, paciente, "
             "autoridade_coatora, pedido_liminar, etc.",
    )

    st.divider()
    st.subheader("v5.0")

    extract_procedural = st.checkbox(
        "Extrair metadados processuais",
        value=False,
        disabled=(mode != "forense"),
        help="Extrai autor (CPF), réu, comarca, pedido liminar e ações "
             "cumuladas. Apenas modo forense.",
    )

    separate_enums = st.checkbox(
        "Separar itens enumerados",
        value=False,
        disabled=(mode != "forense"),
        help="Converte listas com ponto-e-vírgula (;) em lista Markdown.",
    )

    wrap_notes = st.checkbox(
        "Demarcar notas internas",
        value=False,
        disabled=(mode != "forense"),
        help="Detecta seções como 'Observações finais de uso', "
             "'Nota de adequação' e envolve em blockquote.",
    )

    generate_toc_opt = st.checkbox(
        "Gerar sumário automático",
        value=False,
        help="Gera sumário (TOC) automático com links para cada heading.",
    )

    # ── OCR ──
    st.divider()
    st.subheader("OCR")

    ocr_enabled = st.checkbox(
        "Habilitar OCR seletivo",
        value=False,
        help="Aplica OCR apenas em páginas com pouco texto nativo. "
             "Requer pytesseract e Tesseract instalados no sistema.",
    )

    ocr_lang = st.selectbox(
        "Idioma do OCR",
        options=["auto", "por", "eng", "spa", "fra", "deu", "ita"],
        index=1,
        disabled=not ocr_enabled,
        help="auto: detecta automaticamente. "
             "por (português), eng (inglês), spa (espanhol), etc.",
    )

    ocr_threshold = st.number_input(
        "Threshold de OCR (chars mínimos)",
        min_value=1,
        max_value=500,
        value=30,
        step=1,
        disabled=not ocr_enabled,
        help="Páginas com menos caracteres que este valor receberão OCR.",
    )

    ocr_cache_enabled = st.checkbox(
        "Habilitar cache de OCR",
        value=False,
        disabled=not ocr_enabled,
        help="Salva resultados OCR em disco para evitar re-processamento. "
             "Útil ao processar o mesmo PDF múltiplas vezes.",
    )

    # ── Layout e formato ──
    st.divider()
    st.subheader("Layout e formato")

    detect_columns_opt = st.checkbox(
        "Detectar layout de 2 colunas (PDFs)",
        value=True,
        help="Detecta PDFs com layout de 2 colunas e reordena texto "
             "na ordem correta de leitura.",
    )

    output_format = st.selectbox(
        "Formato de saída",
        options=["Markdown", "HTML", "DOCX"],
        index=0,
        help="Markdown: arquivo .md. HTML: documento com CSS jurídico. "
             "DOCX: documento Word.",
    )
    format_map = {"Markdown": "md", "HTML": "html", "DOCX": "docx"}
    output_format_key = format_map[output_format]

    # ── Performance / PDFs grandes ──
    st.divider()
    st.subheader("Performance / PDFs grandes")

    page_range_input = st.text_input(
        "Páginas a processar (1-based)",
        value="",
        placeholder="Ex: 1-50, 1,5,10-20",
        help="Deixe vazio para processar todas. Página 1 = primeira página. "
             "Aplica-se apenas a PDFs.",
    )

    chunk_size_input = st.number_input(
        "Chunk size (páginas por lote)",
        min_value=0,
        max_value=10000,
        value=0,
        step=1,
        help="Processa N páginas por vez, liberando memória entre lotes. "
             "0 = processar tudo de uma vez. Aplica-se apenas a PDFs.",
    )

    workers_input = st.number_input(
        "Workers paralelos",
        min_value=0,
        max_value=32,
        value=0,
        step=1,
        help="0 = sequencial. >0 = número fixo de workers para chunks de PDF.",
    )

    st.divider()
    st.caption("Formatos aceitos: PDF, DOCX, TXT, MD")
    st.caption("v5.0 | Python 3.10+ | PyMuPDF | python-docx")

# ============================================================
# Upload de arquivos
# ============================================================

uploaded_files = st.file_uploader(
    "Selecione os documentos",
    type=["pdf", "docx", "txt", "md"],
    accept_multiple_files=True,
    help="Arraste e solte ou clique para selecionar.",
)

if uploaded_files:
    st.info(f"📄 {len(uploaded_files)} arquivo(s) selecionado(s)")

    if st.button("🚀 Converter", type="primary", use_container_width=True):
        results = []
        progress_bar = st.progress(0, text="Iniciando conversão...")

        # Preparar valores de page_range e chunk_size
        page_range_val = page_range_input.strip() if page_range_input.strip() else None
        chunk_size_val = int(chunk_size_input) if chunk_size_input >= 1 else None
        workers_val = int(workers_input) if workers_input != 0 else None

        for i, uploaded_file in enumerate(uploaded_files):
            progress_text = f"Processando {i + 1}/{len(uploaded_files)}: {uploaded_file.name}"
            progress_bar.progress((i) / len(uploaded_files), text=progress_text)

            file_bytes = uploaded_file.read()
            is_pdf = uploaded_file.name.lower().endswith(".pdf")

            result = convert_document(
                file_bytes=file_bytes,
                filename=uploaded_file.name,
                mode=mode,
                separate=separate_pieces,
                remove_headers_footers=remove_hf,
                detect_citations=detect_citations and mode == "forense",
                extract_metadata=extract_metadata,
                extract_procedural=extract_procedural and mode == "forense",
                separate_enums=separate_enums and mode == "forense",
                wrap_notes=wrap_notes and mode == "forense",
                generate_toc_flag=generate_toc_opt,
                ocr_enabled=ocr_enabled and is_pdf,
                ocr_lang=ocr_lang,
                ocr_threshold=int(ocr_threshold),
                page_range=page_range_val if is_pdf else None,
                chunk_size=chunk_size_val if is_pdf else None,
                detect_columns=detect_columns_opt and is_pdf,
                output_format=output_format_key,
                max_workers=workers_val,
                ocr_cache_enabled=ocr_cache_enabled and is_pdf,
            )
            results.append(result)

        progress_bar.progress(1.0, text="Conversão concluída!")

        # ============================================================
        # Exibir resultados
        # ============================================================

        st.divider()
        st.header("Resultados")

        success_count = sum(1 for r in results if r.success)
        error_count = len(results) - success_count

        col1, col2, col3 = st.columns(3)
        col1.metric("Total", len(results))
        col2.metric("Sucesso", success_count)
        col3.metric("Erros", error_count)

        for result in results:
            with st.expander(
                f"{'✅' if result.success else '❌'} {result.filename}",
                expanded=len(results) == 1,
            ):
                if result.success:
                    # Estatísticas
                    if result.stats:
                        stats_cols = st.columns(4)
                        stats_cols[0].metric("Chars bruto", f"{result.stats.get('chars_raw', 0):,}")
                        stats_cols[1].metric("Chars limpo", f"{result.stats.get('chars_cleaned', 0):,}")
                        stats_cols[2].metric("Chars final", f"{result.stats.get('chars_final', 0):,}")
                        if "pieces_count" in result.stats:
                            stats_cols[3].metric("Peças", result.stats["pieces_count"])

                    # Tabs para preview e download
                    tab_preview, tab_raw = st.tabs(["📖 Preview", "📝 Código Markdown"])

                    with tab_preview:
                        st.markdown(result.markdown)

                    with tab_raw:
                        st.code(result.markdown, language="markdown")

                    # Download individual (formato selecionado)
                    stem = Path(result.filename).stem
                    if output_format_key == "html" and result.html:
                        dl_name = stem + ".html"
                        dl_data = result.html.encode("utf-8")
                        dl_mime = "text/html"
                    elif output_format_key == "docx" and result.docx_bytes:
                        dl_name = stem + ".docx"
                        dl_data = result.docx_bytes
                        dl_mime = (
                            "application/vnd.openxmlformats-"
                            "officedocument.wordprocessingml.document"
                        )
                    else:
                        dl_name = stem + ".md"
                        dl_data = result.markdown.encode("utf-8")
                        dl_mime = "text/markdown"
                    st.download_button(
                        label=f"⬇️ Baixar {dl_name}",
                        data=dl_data,
                        file_name=dl_name,
                        mime=dl_mime,
                    )

                    # Download de peças separadas
                    if result.pieces and len(result.pieces) > 1:
                        st.subheader("Peças separadas")
                        for j, piece in enumerate(result.pieces):
                            piece_filename = f"{Path(result.filename).stem}_peca_{j + 1}_{piece['title'][:30]}.md"
                            st.download_button(
                                label=f"⬇️ {piece['title'][:50]}",
                                data=piece["content"].encode("utf-8"),
                                file_name=piece_filename,
                                mime="text/markdown",
                                key=f"piece_{result.filename}_{j}",
                            )
                else:
                    st.markdown(
                        f'<div class="error-box">❌ Erro: {result.error}</div>',
                        unsafe_allow_html=True,
                    )

        # ============================================================
        # Download em lote (ZIP)
        # ============================================================

        successful_results = [r for r in results if r.success]
        if len(successful_results) > 1:
            st.divider()
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for result in successful_results:
                    md_filename = Path(result.filename).stem + ".md"
                    zf.writestr(md_filename, result.markdown)

            st.download_button(
                label="📦 Baixar todos (ZIP)",
                data=zip_buffer.getvalue(),
                file_name="documentos_convertidos.zip",
                mime="application/zip",
                use_container_width=True,
            )

else:
    st.markdown(
        """
        ### Como usar

        1. **Selecione** os documentos jurídicos (PDF, DOCX, TXT ou MD)
        2. **Configure** o modo de heurísticas na barra lateral
        3. **Clique** em "Converter" para processar
        4. **Baixe** os resultados em Markdown

        ---

        **Modos disponíveis:**

        - **Forense**: otimizado para peças processuais (petições, sentenças, acórdãos)
        - **Doutrina**: otimizado para livros e artigos (capítulos, seções, subseções)
        - **Google**: estilo Google Drive — negrito inline, sem headings Markdown
        """
    )
