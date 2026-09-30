FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY attractor ./attractor
COPY agents ./agents
COPY providers ./providers
COPY evidence ./evidence
COPY failure_engine ./failure_engine

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "attractor.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
