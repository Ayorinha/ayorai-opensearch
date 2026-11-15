FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Debian security updates published after the pinned base image was built (in
# November 2026, zlib1g CVE-2026-76844 and CVE-2026-85091). The base digest stays
# pinned for provenance; the image scan in .github/workflows/docker.yml fails on
# any high or critical finding that has a fix, so a stale base cannot ship.
RUN apt-get update --error-on=any \
    && apt-get upgrade --yes --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

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
