"""
Exportação de Markdown para HTML com CSS jurídico.
"""

import re

import markdown


_CSS = """
body {
    font-family: Georgia, 'Times New Roman', serif;
    max-width: 900px;
    margin: 40px auto;
    padding: 0 20px;
    line-height: 1.8;
    color: #1a1a1a;
}
h1, h2, h3 { color: #1e3a5f; margin-top: 1.5em; }
h1 { font-size: 1.8em; border-bottom: 2px solid #1e3a5f; padding-bottom: 6px; }
h2 { font-size: 1.4em; border-bottom: 1px solid #ccc; padding-bottom: 4px; }
h3 { font-size: 1.2em; }
blockquote {
    border-left: 4px solid #1e3a5f;
    margin: 1em 0;
    padding: 8px 16px;
    background: #f8f9fa;
    color: #333;
}
table { border-collapse: collapse; width: 100%; margin: 1em 0; }
th, td { border: 1px solid #ccc; padding: 8px 12px; text-align: left; }
th { background: #f0f0f0; font-weight: bold; }
pre { background: #f5f5f5; padding: 12px; border-radius: 4px; overflow-x: auto; }
code { background: #f0f0f0; padding: 2px 4px; border-radius: 3px; }
""".strip()


def _strip_frontmatter(text: str) -> str:
    """Remove bloco YAML frontmatter (--- ... ---) do início do texto."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return text
    i = 1
    while i < len(lines):
        if lines[i].strip() == "---":
            return "\n".join(lines[i + 1:])
        i += 1
    return text


def markdown_to_html(md_text: str, title: str = "") -> str:
    """Converte Markdown para HTML completo com CSS jurídico.

    Args:
        md_text: Texto Markdown (pode conter frontmatter YAML).
        title: Título para o <title> do HTML.

    Returns:
        String HTML completa.
    """
    clean_md = _strip_frontmatter(md_text)

    html_body = markdown.markdown(
        clean_md,
        extensions=["tables", "fenced_code", "toc"],
    )

    if not title:
        m = re.search(r"<h1[^>]*>(.+?)</h1>", html_body)
        if m:
            title = re.sub(r"<[^>]+>", "", m.group(1))

    title_escaped = title.replace("&", "&amp;").replace("<", "&lt;")

    return (
        "<!DOCTYPE html>\n"
        '<html lang="pt-BR">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        f"  <title>{title_escaped}</title>\n"
        f"  <style>\n{_CSS}\n  </style>\n"
        "</head>\n"
        "<body>\n"
        f"{html_body}\n"
        "</body>\n"
        "</html>"
    )
