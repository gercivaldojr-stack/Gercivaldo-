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

import streamlit as st

from core.pipeline import convert_batch, convert_document

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
             "A primeira ocorrência é preservada (P10).",
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
    st.subheader("v4.1")

    extract_procedural = st.checkbox(
        "Extrair metadados processuais",
        value=False,
        disabled=(mode != "forense"),
        help="Extrai autor (CPF), reu, comarca, pedido liminar e acoes "
             "cumuladas. Apenas modo forense.",
    )

    separate_enums = st.checkbox(
        "Separar itens enumerados",
        value=False,
        disabled=(mode != "forense"),
        help="Converte listas com ponto-e-virgula (;) em lista Markdown.",
    )

    wrap_notes = st.checkbox(
        "Demarcar notas internas",
        value=False,
        disabled=(mode != "forense"),
        help="Detecta secoes como 'Observacoes finais de uso', "
             "'Nota de adequacao' e envolve em blockquote.",
    )

    st.divider()
    st.caption("Formatos aceitos: PDF, DOCX, TXT, MD")
    st.caption("v4.1 | Python 3.10+ | PyMuPDF | python-docx")

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

        for i, uploaded_file in enumerate(uploaded_files):
            progress_text = f"Processando {i + 1}/{len(uploaded_files)}: {uploaded_file.name}"
            progress_bar.progress((i) / len(uploaded_files), text=progress_text)

            file_bytes = uploaded_file.read()

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

                    # Download individual
                    md_filename = Path(result.filename).stem + ".md"
                    st.download_button(
                        label=f"⬇️ Baixar {md_filename}",
                        data=result.markdown.encode("utf-8"),
                        file_name=md_filename,
                        mime="text/markdown",
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
        """
    )
