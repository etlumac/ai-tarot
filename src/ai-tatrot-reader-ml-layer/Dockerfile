FROM python:3.14-slim

WORKDIR /app

RUN useradd --create-home --shell /bin/bash appuser
ENV PATH="/app/.venv/bin:$PATH"
ENV PIP_INDEX_URL="https://mirrors.aliyun.com/pypi/simple"
ENV PIP_TRUSTED_HOST="mirrors.aliyun.com"
ENV PIP_TIMEOUT=300
ENV PIP_RETRIES=5

ENV UV_INDEX_URL="https://mirrors.aliyun.com/pypi/simple"
ENV UV_NO_CACHE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY src/ai-tatrot-reader-ml-layer/pyproject.toml uv.lock src/ai-tatrot-reader-ml-layer/.python-version ./
COPY src/ai-tatrot-reader-ml-layer ./src/ai-tatrot-reader-ml-layer

RUN pip install --no-cache-dir uv && \
    uv sync --frozen --no-dev --package ai-tatrot-reader-ml-layer


RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8001

CMD ["uvicorn", "ai_tatrot_reader_ml_layer.app:app", "--host", "0.0.0.0", "--port", "8001"]