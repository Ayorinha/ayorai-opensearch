FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY rules /usr/local/lib/python3.12/rules

RUN pip install --no-cache-dir . \
    && groupadd --system attractor \
    && useradd --system --gid attractor --home-dir /app --shell /usr/sbin/nologin attractor \
    && chown -R attractor:attractor /app

USER attractor

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).read()"]

CMD ["uvicorn", "ayorai_attractor.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
