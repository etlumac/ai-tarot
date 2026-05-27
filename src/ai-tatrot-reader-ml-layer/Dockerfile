FROM python:3.14-slim

WORKDIR /app

# uv для установки зависимостей
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Копируем файлы проекта
COPY pyproject.toml uv.lock .python-version ./
COPY ai_tatrot_reader_ml_layer/ ./ai_tatrot_reader_ml_layer/

# Устанавливаем зависимости без dev-зависимостей
RUN uv sync --frozen --no-dev

# Папка для ML-артефактов (модели кладутся при деплое через volume или вручную)
RUN mkdir -p ai_tatrot_reader_ml_layer/models

EXPOSE 8001

CMD ["uv", "run", "uvicorn", "ai_tatrot_reader_ml_layer.app:app", \
     "--host", "0.0.0.0", "--port", "8001"]