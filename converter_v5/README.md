# Conversor PDF → Markdown (v5.0)

## Arquitetura

Workflow em duas etapas para máxima qualidade:

[Sua máquina]                    [Streamlit Cloud]
PDF ──► Marker ──► .md/.zip  ──► Upload ──► Preview ──► Download
        (GPU/CPU)                 (visualização + pós-processamento leve)

### Etapa 1 — Conversão Local (Marker + Ollama)

O Marker roda na sua máquina com acesso a GPU (ou CPU, mais lento).
Opcionalmente, usa Ollama para melhorar tabelas e layout.

### Etapa 2 — Streamlit Cloud (Visualização)

App leve que recebe o Markdown já convertido, exibe preview renderizado,
aplica pós-processamento opcional e oferece download.

---

## Instalação — Etapa 1 (Máquina Local)

### Pré-requisitos

- Python 3.10+
- PyTorch (com CUDA se tiver GPU)
- ~5 GB de VRAM por worker (GPU) ou ~16 GB RAM (CPU)

### 1. Instalar Marker

pip install marker-pdf

Para converter DOCX, PPTX, XLSX além de PDF:

pip install "marker-pdf[all]"

### 2. Instalar Ollama (opcional, para qualidade máxima)

Linux:

curl -fsSL https://ollama.com/install.sh | sh

Baixar modelo recomendado:

ollama pull gemma3

Verificar se está rodando:

curl http://localhost:11434
(Deve retornar: "Ollama is running")

### 3. Converter um PDF

Modo básico (sem LLM):

marker_single documento.pdf --output_dir ./saida --output_format markdown

Modo com Ollama (qualidade máxima):

marker_single documento.pdf \
  --output_dir ./saida \
  --output_format markdown \
  --use_llm \
  --llm_service marker.services.ollama.OllamaService \
  --ollama_base_url http://localhost:11434 \
  --ollama_model gemma3 \
  --langs pt

Modo com Claude API (alternativa ao Ollama):

export ANTHROPIC_API_KEY="sua-chave"
marker_single documento.pdf \
  --output_dir ./saida \
  --output_format markdown \
  --use_llm \
  --llm_service marker.services.claude.ClaudeService \
  --claude_model_name claude-sonnet-4-20250514

Conversão em lote (múltiplos PDFs):

marker ./pasta_pdfs ./pasta_saida --workers 2 --output_format markdown

### 4. Script auxiliar (converte + compacta)

Use o script local_converter/convert.py para facilitar:

python local_converter/convert.py documento.pdf --use-ollama
python local_converter/convert.py ./pasta_com_pdfs --batch --use-ollama

O script gera um .zip com todos os .md e imagens, pronto para upload no Streamlit.

---

## Instalação — Etapa 2 (Streamlit Cloud)

### Deploy no Streamlit Cloud

1. Faça push da pasta streamlit_app/ para seu repositório GitHub.
2. Acesse share.streamlit.io.
3. Aponte para streamlit_app/app.py.
4. Deploy.

### Uso local (teste)

cd streamlit_app
pip install -r requirements.txt
streamlit run app.py

---

## Parâmetros úteis do Marker

| Parâmetro | Descrição |
|-----------|-----------|
| --output_format | markdown, json, html, chunks |
| --use_llm | Usa LLM para melhorar tabelas, math, layout |
| --force_ocr | Força OCR mesmo em PDFs com texto extraível |
| --page_range | Ex: "0,5-10,20" — páginas específicas |
| --langs | Idiomas para OCR. Ex: pt,en |
| --disable_image_extraction | Não extrai imagens (mais rápido) |
| --paginate_output | Adiciona marcadores de página |
| --workers | Nº de PDFs em paralelo (lote) |

---

## Limites

- Tamanho máximo: testado com PDFs de até 200 MB (~1.250 páginas)
- GPU: ~5 GB VRAM por worker; sem GPU, usar CPU (mais lento)
- Ollama: modelos grandes (27B+) exigem ~16 GB RAM; gemma3 (padrão) funciona com 8 GB
- Streamlit Cloud: limite de upload de 200 MB por arquivo
