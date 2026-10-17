# API key authentication

The API is unauthenticated by default for backwards compatibility. Enable authentication explicitly before exposing a deployment to an untrusted network.

## Configuration

Set ATTRACTOR_AUTH_MODE=api_key and configure one or more SHA-256 digests in ATTRACTOR_API_KEYS_SHA256. The value is a comma-separated list of 64-character hexadecimal SHA-256 digests. Raw API keys must not be stored in this variable.

Generate a digest locally without printing or committing the raw key:

~~~bash
python -c "import getpass, hashlib; key=getpass.getpass('API key: '); print(hashlib.sha256(key.encode('utf-8')).hexdigest())"
~~~

Example configuration (replace the placeholder with a digest generated for your own secret):

~~~bash
export ATTRACTOR_AUTH_MODE=api_key
export ATTRACTOR_API_KEYS_SHA256='REPLACE_WITH_64_CHARACTER_SHA256_HEX_DIGEST'
uvicorn ayorai_attractor.api.app:app --host 127.0.0.1 --port 8000
~~~

The placeholder above is intentionally invalid and must be replaced. In api_key mode, missing or malformed digest configuration prevents the middleware from starting. Supported modes are off and api_key; off is the default.

## Sending authenticated requests

Either a Bearer token or the X-API-Key header is accepted:

~~~bash
curl -H "Authorization: Bearer $ATTRACTOR_API_KEY" http://127.0.0.1:8000/v1/audit
curl -H "X-API-Key: $ATTRACTOR_API_KEY" http://127.0.0.1:8000/v1/audit
~~~

Keep the raw key in a secret manager or environment supplied by the deployment platform. Do not commit it, place it in source code, or print it in logs. The application compares the SHA-256 digest of the presented key against configured digests using constant-time comparisons. Failed authentication returns a generic HTTP 401 response without revealing which part of the credential check failed. The /health endpoint remains public for health checks.

## Operational considerations

- Use HTTPS whenever requests cross an untrusted network.
- Use high-entropy, unique keys and rotate them by replacing the configured digest list.
- Restrict access to environment configuration and deployment logs.
- Authentication is not a substitute for network controls, rate limiting, authorization scopes, or secret rotation procedures.
- The default off mode preserves existing API behavior. Operators must explicitly enable api_key mode when required by their deployment.
