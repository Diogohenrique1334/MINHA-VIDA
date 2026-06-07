# Imagem do backend (FastAPI + bot do WhatsApp). Frontend roda no Streamlit Cloud.
FROM python:3.9-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Instala só as dependências do backend (camada cacheável).
COPY requirements-backend.txt .
RUN pip install --no-cache-dir -r requirements-backend.txt

# Copia apenas o necessário para rodar a API e aplicar migrações.
COPY alembic.ini .
COPY alembic ./alembic
COPY backend ./backend

EXPOSE 8000

# Aplica as migrações e sobe a API. PORT é injetável (Render); 8000 por padrão (local).
CMD ["sh", "-c", "alembic upgrade head && uvicorn backend.whats:app --host 0.0.0.0 --port ${PORT:-8000}"]
