FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y \
    gcc g++ \
    ncbi-blast+ \
    curl \
    default-jre-headless && \
    rm -rf /var/lib/apt/lists/*

# Nextflow pinned release (no curl|bash). Bump with a reviewed GitHub release tag.
ARG NEXTFLOW_VERSION=24.10.6
RUN curl -fsSL "https://github.com/nextflow-io/nextflow/releases/download/v${NEXTFLOW_VERSION}/nextflow" \
    -o /usr/local/bin/nextflow && \
    chmod +x /usr/local/bin/nextflow

COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
# Pre-download embedding model (~420MB, multilingual DE/EN/50+)
RUN python -c "\
from sentence_transformers import SentenceTransformer; \
SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2'); \
print('Embedding model downloaded.')\
"
COPY . .
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
