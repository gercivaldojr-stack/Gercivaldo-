"""
Conversor PDF → Markdown (v5.0) — Etapa 2: Visualização
App Streamlit para preview e download de Markdown convertido pelo Marker.

Deploy: Streamlit Cloud (sem GPU, sem dependências pesadas)
"""

import io
import re
import zipfile
from datetime import datetime

import streamlit as st


st.set_page_config(
    page_title="Conversor PDF → Markdown",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)


def count_headings(text: str) -> dict:
    """Conta headings por nível."""
    counts = {}
    for line in text.split("\n"):
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            if level <= 6:
                key = f"H{level}"
                counts[key] = counts.get(key, 0) + 1
    return counts


def count_elements(text: str) -> dict:
    """Conta elementos Markdown."""
    lines = text.split("\n")
    return {
        "Linhas": len(lines),
        "Caracteres": len(text),
        "Palavras": len(text.split()),
        "Blockquotes": sum(1 for l in lines if l.startswith(">")),
        "Tabelas": sum(1 for l in lines if l.startswith("|")),
        "Negritos": len(re.findall(r"\*\*[^*]+\*\*", text)),
        "Itálicos": len(re.findall(r"(?<!\*)\*[^*]+\*(?!\*)", text)),
        "Links": len(re.findall(r"\[.+?\]\(.+?\)", text)),
        "Imagens": len(re.findall(r"!\[.*?\]\(.+?\)", text)),
    }


def extract_toc(text: str) -> list:
    """Extrai headings para exibir como sumário."""
    toc = []
    for line in text.split("\n"):
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            title = line.lstrip("#").strip()
            if title and level <= 4:
                toc.append((level, title))
    return toc


def apply_light_postprocess(text: str, options: dict) -> str:
    """Pós-processamento leve (opcional)."""

    if options.get("fix_line_breaks"):
        preps = r"\b(de|da|do|das|dos|para|com|sob|por|no|na|nos|nas|ao|à|aos|às|em|entre|sobre|a|o|as|os|e|ou|que)\s*$"
        lines = text.split("\n")
        merged = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if (i + 1 < len(lines)
                and re.search(preps, line)
                and lines[i + 1].strip()
                and not lines[i + 1].startswith(("#", ">", "|", "-", "*"))):
                merged.append(line.rstrip() + " " + lines[i + 1].lstrip())
                i += 2
            else:
                merged.append(line)
                i += 1
        text = "\n".join(merged)

    if options.get("fix_multiple_blanks"):
        text = re.sub(r"\n{4,}", "\n\n\n", text)

    if options.get("fix_smart_quotes"):
        text = text.replace('"', "\u201c").replace('"', "\u201d")

    return text


with st.sidebar:
    st.title("📄 Conversor v5.0")
    st.caption("PDF → Markdown via Marker")

    st.divider()

    st.subheader("Upload")
    uploaded_file = st.file_uploader(
        "Arraste o arquivo .md ou .zip gerado pelo Marker",
        type=["md", "txt", "zip"],
        help="Limite: 200 MB",
    )

    st.divider()

    st.subheader("Pós-processamento")
    fix_line_breaks = st.checkbox("Juntar linhas fragmentadas", value=False,
        help="Une linhas que terminam em preposição/artigo com a linha seguinte")
    fix_multiple_blanks = st.checkbox("Reduzir linhas em branco", value=False,
        help="Máximo de 2 linhas em branco consecutivas")
    fix_smart_quotes = st.checkbox("Aspas tipográficas", value=False,
        help='Converte " para \u201c \u201d')

    st.divider()

    st.subheader("Instruções")
    st.markdown("""
    **Etapa 1** — Na sua máquina:
    ```
    marker_single doc.pdf \\
      --output_dir ./saida \\
      --output_format markdown \\
      --use_llm \\
      --llm_service marker.services.ollama.OllamaService \\
      --ollama_model gemma3
    ```

    **Etapa 2** — Aqui:
    Upload do `.md` gerado → Preview → Download
    """)


if uploaded_file is None:
    st.title("Conversor PDF → Markdown")
    st.markdown("""
    Este app exibe e permite download de arquivos Markdown convertidos
    pelo **Marker** (Datalab) na sua máquina local.

    **Workflow:**
    1. Converta o PDF localmente com o Marker (+ Ollama para qualidade máxima)
    2. Faça upload do `.md` gerado aqui
    3. Visualize, aplique pós-processamento leve e baixe o resultado

    Arraste o arquivo na barra lateral para começar.
    """)
    st.stop()


md_content = ""
filename = uploaded_file.name

if filename.endswith(".zip"):
    with zipfile.ZipFile(io.BytesIO(uploaded_file.read()), "r") as zf:
        md_files = [f for f in zf.namelist() if f.endswith(".md")]
        if md_files:
            if len(md_files) > 1:
                selected = st.sidebar.selectbox("Arquivo:", md_files)
            else:
                selected = md_files[0]

            md_content = zf.read(selected).decode("utf-8", errors="replace")
            filename = selected
        else:
            st.error("Nenhum arquivo .md encontrado no ZIP.")
            st.stop()
else:
    md_content = uploaded_file.read().decode("utf-8", errors="replace")


options = {
    "fix_line_breaks": fix_line_breaks,
    "fix_multiple_blanks": fix_multiple_blanks,
    "fix_smart_quotes": fix_smart_quotes,
}

if any(options.values()):
    md_content = apply_light_postprocess(md_content, options)


tab_preview, tab_source, tab_stats, tab_toc = st.tabs(
    ["Preview", "Código-fonte", "Estatísticas", "Sumário"]
)

with tab_preview:
    st.markdown(md_content, unsafe_allow_html=False)

with tab_source:
    st.code(md_content, language="markdown", line_numbers=True)

with tab_stats:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Elementos")
        elements = count_elements(md_content)
        for key, value in elements.items():
            st.metric(key, f"{value:,}")

    with col2:
        st.subheader("Headings")
        headings = count_headings(md_content)
        if headings:
            for key, value in sorted(headings.items()):
                st.metric(key, value)
        else:
            st.warning("Nenhum heading detectado.")

with tab_toc:
    toc = extract_toc(md_content)
    if toc:
        for level, title in toc:
            indent = "\u00a0\u00a0\u00a0\u00a0" * (level - 1)
            prefix = "#" * level
            st.markdown(f"{indent}`{prefix}` {title}")
    else:
        st.info("Nenhum heading encontrado para gerar sumário.")


st.divider()

col_dl1, col_dl2 = st.columns(2)

with col_dl1:
    st.download_button(
        label="⬇️ Download .md",
        data=md_content.encode("utf-8"),
        file_name=filename if filename.endswith(".md") else f"{filename}.md",
        mime="text/markdown",
    )

with col_dl2:
    st.download_button(
        label="⬇️ Download .txt",
        data=md_content.encode("utf-8"),
        file_name=filename.replace(".md", ".txt") if filename.endswith(".md") else f"{filename}.txt",
        mime="text/plain",
    )
