# Docker deployment

The container runs as a dedicated unprivileged user. Docker Compose publishes the API only on the host loopback interface (127.0.0.1:8000), enables API-key authentication by default, and reads runtime settings from a local .env file.

## Prepare the environment

~~~bash
cp .env.example .env
~~~

Generate a SHA-256 digest for a high-entropy API key. The key is entered without echo and is not printed by this command; only the digest is printed:

~~~bash
python -c "import getpass, hashlib; key=getpass.getpass('API key: '); print(hashlib.sha256(key.encode('utf-8')).hexdigest())"
~~~

Edit .env and set ATTRACTOR_API_KEYS_SHA256 to the generated 64-character digest. Keep the raw key in a secret manager and provide it to clients through a secure channel. Do not commit .env. The example file intentionally leaves the digest empty; with ATTRACTOR_AUTH_MODE=api_key, the application refuses to start until a valid digest is configured. For a deliberately isolated local development environment only, ATTRACTOR_AUTH_MODE can be set to off.

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
- The health check only confirms process/API responsiveness; it does not prove dependency health or application correctness.
