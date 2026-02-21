# Multi-stage build: builder preloads models, runtime runs the app
FROM python:3.11-slim AS builder

WORKDIR /builder

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download sentence-transformers model (all-MiniLM-L6-v2)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Install spaCy and download models
RUN pip install --no-cache-dir spacy \
    && python -m spacy download de_core_news_sm \
    && python -m spacy download en_core_web_sm

# ---
FROM python:3.11-slim AS runtime

RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy installed packages and pre-downloaded model cache from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /root/.cache /home/appuser/.cache
RUN chown -R appuser:appuser /home/appuser/.cache

# Copy application
COPY --chown=appuser:appuser . .

USER appuser
ENV HOME=/home/appuser
ENV PYTHONPATH=/app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
