FROM python:3.14-slim AS builder

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH" \
    PIP_INDEX_URL="https://mirrors.aliyun.com/pypi/simple" \
    PIP_TRUSTED_HOST="mirrors.aliyun.com" \
    PIP_TIMEOUT=300 \
    PIP_RETRIES=5 \
    UV_INDEX_URL="https://mirrors.aliyun.com/pypi/simple" \
    UV_NO_CACHE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

COPY src/ai-tatrot-reader-ml-layer/pyproject.toml \
     uv.lock \
     src/ai-tatrot-reader-ml-layer/.python-version ./
COPY src/ai-tatrot-reader-ml-layer ./src/ai-tatrot-reader-ml-layer

RUN pip install --no-cache-dir uv && \
    uv sync --frozen --no-dev --package ai-tatrot-reader-ml-layer && \
    rm -rf ~/.cache/pip ~/.cache/uv ~/.cache/huggingface /tmp/*

FROM python:3.14-slim

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH" \
    PIP_INDEX_URL="https://mirrors.aliyun.com/pypi/simple" \
    PIP_TRUSTED_HOST="mirrors.aliyun.com" \
    PIP_TIMEOUT=300 \
    PIP_RETRIES=5 \
    UV_INDEX_URL="https://mirrors.aliyun.com/pypi/simple" \
    UV_NO_CACHE=1 \
    TRANSFORMERS_OFFLINE=0 \
    HF_DATASETS_OFFLINE=0 \
    HF_HOME="/tmp/hf_cache"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

COPY --from=builder /app/.venv /app/.venv

COPY src/ai-tatrot-reader-ml-layer ./src/ai-tatrot-reader-ml-layer

RUN mkdir -p /tmp/hf_cache

EXPOSE 8001

CMD ["uvicorn", "ai_tatrot_reader_ml_layer.app:app", "--host", "0.0.0.0", "--port", "8001"]