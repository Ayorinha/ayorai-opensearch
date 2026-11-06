# API key authentication

API-key authentication is enabled by default. The application refuses to start when API-key mode is selected but the pepper or digest list is missing or malformed. For an isolated local development environment only, set `ATTRACTOR_AUTH_MODE=off` explicitly; never use that mode on a network-facing deployment.

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
uvicorn ayorai_attractor.api.app:app --host 127.0.0.1 --port 8000 --lifespan on
~~~

The placeholders above are intentionally invalid and must be replaced. In `api_key` mode, missing or malformed pepper/digest configuration prevents the middleware from starting. Supported modes are `off` and `api_key`; `api_key` is the default. The `/health` endpoint remains public.

## Sending authenticated requests

Either a Bearer token or the X-API-Key header is accepted:

~~~bash
curl -H "Authorization: Bearer $ATTRACTOR_API_KEY" http://127.0.0.1:8000/v1/audit
curl -H "X-API-Key: $ATTRACTOR_API_KEY" http://127.0.0.1:8000/v1/audit
~~~

Keep the raw key in a secret manager or environment supplied by the deployment platform. Do not commit it, place it in source code, or print it in logs. The application compares a keyed HMAC-SHA-256 digest of the presented key against configured digests using constant-time comparisons. The separate pepper protects the digest list against offline guessing if that list is leaked without the pepper. Failed authentication returns a generic HTTP 401 response without revealing which part of the credential check failed. The `/health` endpoint remains public for health checks.

## Application-level request throttling

The API middleware applies a fixed-window request limit to the connecting client IP before authentication, and a second limit to the HMAC digest of an authenticated API key. These are independent limiters with independent bounded tables: IP identities cannot consume or evict authenticated-key entries. Raw API keys are never used as limiter identities. Requests over the limit receive HTTP `429` with a `Retry-After` header containing the remaining seconds in that identity's window. `/health` is exempt so infrastructure health checks continue to work.

Because this is a fixed-window limiter, requests near a window boundary can use nearly the full limit immediately before the boundary and nearly the full limit immediately after it. Thus, over a short boundary-spanning interval, the observed burst can approach **2× the configured limit** (for example, nearly 240 requests around the boundary with a limit of 120 per 60 seconds). This is an inherent fixed-window trade-off, not a rolling-window guarantee.

The IP limiter uses an LRU eviction policy when its table reaches capacity: the least recently used IP entry is evicted and the new identity is admitted. This deliberately avoids rejecting every new client when a flood fills the table. Under sustained high-cardinality IP churn, an evicted IP can receive a fresh window if it returns; this bounded in-process control is not a substitute for edge-level abuse protection. The authenticated-key limiter has capacity equal to the number of distinct configured key digests, so arbitrary IP identities cannot consume its slots.

The defaults are 120 requests per 60 seconds, with at most 10,000 active IP identities in memory. Configure these values with:

~~~bash
export ATTRACTOR_RATE_LIMIT_REQUESTS=120
export ATTRACTOR_RATE_LIMIT_WINDOW_SECONDS=60
export ATTRACTOR_RATE_LIMIT_MAX_CLIENTS=10000
~~~

All three values must be positive integers. With `ATTRACTOR_AUTH_MODE=off`, authentication is disabled but the IP rate limit remains active; `off` does not disable request throttling. The limiters are deliberately bounded and process-local: they protect a single application process from bursts and basic credential guessing, but counters are not shared across workers or replicas and reset on restart. A multi-worker or multi-replica deployment MUST also enforce a shared rate limit at its trusted API gateway or edge.

## Trusted reverse proxies and client IPs

When the API is behind Nginx, a load balancer, Cloudflare, or another reverse proxy, Uvicorn must accept forwarded client addresses only from the exact proxy IP addresses or narrowly scoped CIDRs that you control. The Docker image enables proxy-header support and passes the `FORWARDED_ALLOW_IPS` environment variable to Uvicorn. Docker Compose defaults this allowlist to `127.0.0.1`; replace it in the deployment `.env` with the proxy's actual source address or a narrow, controlled proxy subnet:

~~~bash
FORWARDED_ALLOW_IPS=172.30.0.10
~~~

For a direct Uvicorn deployment, configure the equivalent explicitly:

~~~bash
export FORWARDED_ALLOW_IPS='172.30.0.10'
uvicorn ayorai_attractor.api.app:app --host 0.0.0.0 --port 8000 --lifespan on --proxy-headers --forwarded-allow-ips "$FORWARDED_ALLOW_IPS"
~~~

Do not use `--forwarded-allow-ips '*'` on a network where untrusted clients can connect directly. Never trust `X-Forwarded-For` merely because a client supplied it: the header is authoritative only when Uvicorn receives the request from a proxy in this explicit trusted allowlist and that proxy overwrites/sanitizes incoming forwarding headers. Keep the proxy-to-application network restricted to those trusted proxies.

## Operational considerations

- Use HTTPS whenever requests cross an untrusted network.
- Use high-entropy, unique keys and rotate them by replacing the configured digest list.
- Protect and rotate the pepper separately; changing the pepper requires regenerating every configured digest.
- Restrict access to environment configuration and deployment logs.
- Application-level throttling does not replace shared gateway limits, authorization scopes, tenant isolation, or secret rotation procedures.
- The default mode is `api_key` and the application refuses to start without valid key material. Set `ATTRACTOR_AUTH_MODE=off` explicitly only for isolated local development; never use it for a network-facing deployment.

## Why HMAC-SHA-256 and not a password-hashing function

CodeQL rule `py/weak-sensitive-data-hashing` flags any fast hash applied to a value it classifies as a password. That guidance targets low-entropy, human-chosen secrets, where a slow function (Argon2, scrypt, PBKDF2) limits offline guessing. ATTRACTOR API keys are machine-generated tokens of at least 32 characters (about 190 bits when generated as above), enforced by the middleware. Guessing such a key is infeasible with or without a slow function, and a slow function would add CPU cost to every request that an attacker could exploit. The digest list is additionally keyed by a separate 32-byte pepper. This rationale is the basis for dismissing that alert as not applicable; it does not apply if human-chosen passwords are ever accepted.
