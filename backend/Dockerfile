FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml requirements.lock ./
COPY app app
RUN pip install --no-cache-dir -c requirements.lock .
COPY alembic alembic
COPY alembic.ini .
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
