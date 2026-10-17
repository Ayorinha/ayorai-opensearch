# API key authentication

The API is unauthenticated by default for backwards compatibility. Enable authentication explicitly before exposing a deployment to an untrusted network.

## Configuration

Set `ATTRACTOR_AUTH_MODE=api_key`, `ATTRACTOR_API_KEY_PEPPER`, and `ATTRACTOR_API_KEYS_HMAC_SHA256`. The pepper must be a 32-byte secret encoded as 64 hexadecimal characters. The digest setting is a comma-separated list of 64-character HMAC-SHA-256 hex digests. Keep the pepper in a secret manager and restrict access to it separately from the digest list. Never commit either value.

Generate a high-entropy pepper once and store it in your deployment secret manager:

~~~bash
python -c "import secrets; print(secrets.token_hex(32))"
~~~

Generate each API key with a cryptographically secure generator. Keys shorter than 32 characters are always rejected, even if their digest is configured:

~~~bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
~~~

Generate a digest locally without printing the raw API key or pepper:

~~~bash
python -c "import getpass, hashlib, hmac; key=getpass.getpass('API key: '); pepper=bytes.fromhex(getpass.getpass('32-byte pepper (64 hex chars): ')); print(hmac.new(pepper, key.encode('utf-8'), hashlib.sha256).hexdigest())"
~~~

Example configuration (replace both placeholders with your own secrets/digests):

~~~bash
export ATTRACTOR_AUTH_MODE=api_key
export ATTRACTOR_API_KEY_PEPPER='REPLACE_WITH_64_HEX_CHAR_SECRET'
export ATTRACTOR_API_KEYS_HMAC_SHA256='REPLACE_WITH_64_CHARACTER_HMAC_SHA256_HEX_DIGEST'
uvicorn ayorai_attractor.api.app:app --host 127.0.0.1 --port 8000
~~~

The placeholders above are intentionally invalid and must be replaced. In `api_key` mode, missing or malformed pepper/digest configuration prevents the middleware from starting. Supported modes are `off` and `api_key`; `off` is the default.

## Sending authenticated requests

Either a Bearer token or the X-API-Key header is accepted:

~~~bash
curl -H "Authorization: Bearer $ATTRACTOR_API_KEY" http://127.0.0.1:8000/v1/audit
curl -H "X-API-Key: $ATTRACTOR_API_KEY" http://127.0.0.1:8000/v1/audit
~~~

Keep the raw key in a secret manager or environment supplied by the deployment platform. Do not commit it, place it in source code, or print it in logs. The application compares a keyed HMAC-SHA-256 digest of the presented key against configured digests using constant-time comparisons. The separate pepper protects the digest list against offline guessing if that list is leaked without the pepper. Failed authentication returns a generic HTTP 401 response without revealing which part of the credential check failed. The `/health` endpoint remains public for health checks.

## Operational considerations

- Use HTTPS whenever requests cross an untrusted network.
- Use high-entropy, unique keys and rotate them by replacing the configured digest list.
- Protect and rotate the pepper separately; changing the pepper requires regenerating every configured digest.
- Restrict access to environment configuration and deployment logs.
- Authentication is not a substitute for network controls, rate limiting, authorization scopes, or secret rotation procedures.
- The default `off` mode preserves existing API behavior. Operators must explicitly enable `api_key` mode when required by their deployment.

## Why HMAC-SHA-256 and not a password-hashing function

CodeQL rule `py/weak-sensitive-data-hashing` flags any fast hash applied to a value it classifies as a password. That guidance targets low-entropy, human-chosen secrets, where a slow function (Argon2, scrypt, PBKDF2) limits offline guessing. ATTRACTOR API keys are machine-generated tokens of at least 32 characters (about 190 bits when generated as above), enforced by the middleware. Guessing such a key is infeasible with or without a slow function, and a slow function would add CPU cost to every request that an attacker could exploit. The digest list is additionally keyed by a separate 32-byte pepper. This rationale is the basis for dismissing that alert as not applicable; it does not apply if human-chosen passwords are ever accepted.
