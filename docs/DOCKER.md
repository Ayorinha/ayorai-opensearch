# Docker deployment

The container runs as a dedicated unprivileged user. Docker Compose publishes the API only on the host loopback interface (127.0.0.1:8000), enables API-key authentication by default, and reads runtime settings from a local .env file.

## Prepare the environment

~~~bash
cp .env.example .env
~~~

Generate a high-entropy 32-byte pepper and store it securely. The printed value is a secret; do not commit it:

~~~bash
python -c "import secrets; print(secrets.token_hex(32))"
~~~

Generate an HMAC-SHA-256 digest for a high-entropy API key. Both the key and pepper are entered without echo; only the digest is printed:

~~~bash
python -c "import getpass, hashlib, hmac; key=getpass.getpass('API key: '); pepper=bytes.fromhex(getpass.getpass('32-byte pepper (64 hex chars): ')); print(hmac.new(pepper, key.encode('utf-8'), hashlib.sha256).hexdigest())"
~~~

Edit .env and set ATTRACTOR_API_KEY_PEPPER to the 64-character hex pepper and ATTRACTOR_API_KEYS_HMAC_SHA256 to the generated 64-character digest. Keep the pepper in a secret manager and restrict access to it separately from the digest list. Keep the raw API key in a secret manager and provide it to clients through a secure channel. Do not commit .env. The example file intentionally leaves the pepper and digest empty; with ATTRACTOR_AUTH_MODE=api_key, the application refuses to start until both are configured. For a deliberately isolated local development environment only, ATTRACTOR_AUTH_MODE can be set to off.

## Build and start

~~~bash
docker compose up --build -d
docker compose ps
docker compose exec attractor id
~~~

The container's user should not be root. The image declares a Docker HEALTHCHECK against the public /health endpoint. The endpoint remains unauthenticated so container health probes do not require a secret.

Verify that the host binding is local-only and that protected routes reject missing credentials:

~~~bash
curl -i http://127.0.0.1:8000/health
curl -i http://127.0.0.1:8000/v1/audit
~~~

The second command should receive HTTP 401 when API-key authentication is enabled. Send a configured key using Authorization: Bearer or X-API-Key. Do not put raw keys in URLs or logs.

## Network and secret handling

- The 127.0.0.1 host binding prevents direct publication on all host interfaces. Do not change it to 0.0.0.0 unless exposure is intentional and protected by suitable network controls.
- The process inside the container listens on 0.0.0.0:8000 so Docker port forwarding can reach it; this does not expose the host port beyond the configured loopback binding.
- Keep .env out of version control and restrict access to the host and container runtime.
- The HMAC pepper should be protected separately from stored digest values. Rotating it requires regenerating all configured API-key digests.
- The health check only confirms process/API responsiveness; it does not prove dependency health or application correctness.
