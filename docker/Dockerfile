FROM python:3.15-slim@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY docker/requirements.lock ./docker/requirements.lock
COPY src ./src

# Dependencies come only from the hash-locked file (no resolution, wheels only);
# the project itself is installed without resolving anything else, and the build
# tools it needed are removed afterwards.
RUN pip install --no-cache-dir --require-hashes --only-binary=:all: -r docker/requirements.lock \
    && pip install --no-cache-dir --no-deps --no-build-isolation . \
    && pip uninstall --yes setuptools wheel packaging \
    && groupadd --system attractor \
    && useradd --system --gid attractor --home-dir /app --shell /usr/sbin/nologin attractor \
    && chown -R attractor:attractor /app \
    # The runtime never installs packages: drop pip (and its known advisories)
    # and the setuid/setgid bits that would let a compromised process escalate.
    && python -m pip uninstall --yes pip \
    && find / -xdev -perm /6000 -type f -exec chmod a-s {} +

USER attractor

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).read()"]

CMD ["sh", "-c", "exec uvicorn ayorai_attractor.api.app:app --host 0.0.0.0 --port 8000 --lifespan on --no-access-log --proxy-headers --forwarded-allow-ips \"${FORWARDED_ALLOW_IPS:-127.0.0.1}\""]
