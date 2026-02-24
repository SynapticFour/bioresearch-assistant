FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y \
    gcc g++ \
    ncbi-blast+ \
    curl \
    default-jre-headless && \
    rm -rf /var/lib/apt/lists/*

# Nextflow als Binary installieren (für WES-Pipelines)
RUN curl -s https://get.nextflow.io | bash && \
    mv nextflow /usr/local/bin/ && \
    chmod +x /usr/local/bin/nextflow

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
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
