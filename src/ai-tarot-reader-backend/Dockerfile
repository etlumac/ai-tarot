FROM python:3.14-slim

WORKDIR /app

RUN useradd --create-home --shell /bin/bash appuser
ENV PATH="/app/.venv/bin:$PATH"
ENV PIP_INDEX_URL="https://mirrors.aliyun.com/pypi/simple"
ENV PIP_TRUSTED_HOST="mirrors.aliyun.com"
ENV PIP_TIMEOUT=100
ENV PIP_RETRIES=5

ENV UV_INDEX_URL="https://mirrors.aliyun.com/pypi/simple"
ENV UV_NO_CACHE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY src/ai-tarot-reader-backend/pyproject.toml uv.lock src/ai-tarot-reader-backend/.python-version ./
COPY src/ai-tarot-reader-backend ./src/ai-tarot-reader-backend


RUN pip install --no-cache-dir uv && \
    uv sync --frozen --no-dev --package ai-tarot-reader-backend


RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "ai_tarot_reader_backend.app:app", "--host", "0.0.0.0", "--port", "8000"]