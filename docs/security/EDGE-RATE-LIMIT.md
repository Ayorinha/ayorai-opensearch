# Shared rate limiting across workers and replicas

The application's limiters are deliberately process-local (see [API-AUTH.md](API-AUTH.md)):

| Control | Scope | Variables |
|---|---|---|
| HTTP 429 per IP and per API key | one process | `ATTRACTOR_RATE_LIMIT_REQUESTS`, `ATTRACTOR_RATE_LIMIT_WINDOW_SECONDS`, `ATTRACTOR_RATE_LIMIT_MAX_CLIENTS` |
| HTTP 503 for heavy routes (`/v1/verify`, `/v1/check`, `/v1/fields`, `/v1/audit`, `/v1/opensearch`, `/v2/audit`) | one process, or one host with `ATTRACTOR_INFLIGHT_SCOPE=host` | `ATTRACTOR_MAX_INFLIGHT_HEAVY`, `ATTRACTOR_INFLIGHT_SCOPE`, `ATTRACTOR_INFLIGHT_LOCK_DIR` |

With N workers or N replicas, the effective per-client allowance is up to N times the configured value, and counters reset on restart. A deployment with more than one process MUST enforce the aggregate limit at a trusted gateway or edge that sees every request. The application limits stay on as a second line of defence.

## Requirements for the edge

1. **One counter for all replicas.** Either a single gateway instance in front of every replica, or a gateway whose counters live in a shared store.
2. **A trustworthy client address.** The image starts uvicorn with `--proxy-headers --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}"`. Set `FORWARDED_ALLOW_IPS` to the gateway's address only, never `*`, so that a client cannot forge `X-Forwarded-For`. The gateway must overwrite, not append to, any `X-Forwarded-For` received from the client.
3. **Stricter limits on heavy routes.** Search, adjudication and PDF extraction cost far more than `/health` or a trace lookup (`GET /v1/audit/{trace_id}`).
4. **Bounded bodies.** Keep the gateway body limit no larger than `ATTRACTOR_MAX_BODY_BYTES` (2 MiB by default).
5. **The application stays private.** Bind replicas to an internal network; only the gateway is published.

## Example: nginx in front of several replicas

A minimal, single-instance nginx configuration. The `limit_req_zone` counters are shared by every nginx worker on that instance, so all replicas behind it see one limit per client address. Adjust the rates to your capacity.

```nginx
# http { ... }
limit_req_zone  $binary_remote_addr zone=attractor_all:10m   rate=120r/m;
limit_req_zone  $binary_remote_addr zone=attractor_heavy:10m rate=20r/m;
limit_req_status 429;
limit_conn_zone $binary_remote_addr zone=attractor_conn:10m;

upstream attractor {
    server 10.0.0.11:8000;
    server 10.0.0.12:8000;
    keepalive 16;
}

server {
    listen 443 ssl;
    # ssl_certificate / ssl_certificate_key ...

    client_max_body_size 2m;
    limit_conn attractor_conn 10;

    proxy_set_header Host            $host;
    proxy_set_header X-Forwarded-For $remote_addr;   # overwrite, never append
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_http_version 1.1;
    proxy_set_header Connection "";

    location ~ ^/(v1/(verify|check|fields|audit|opensearch)|v2/audit)$ {
        limit_req zone=attractor_heavy burst=5 nodelay;
        limit_req zone=attractor_all   burst=20 nodelay;
        proxy_read_timeout 120s;
        proxy_pass http://attractor;
    }

    location / {
        limit_req zone=attractor_all burst=20 nodelay;
        proxy_pass http://attractor;
    }
}
```

Start each replica with `FORWARDED_ALLOW_IPS` set to the nginx address, for example `FORWARDED_ALLOW_IPS=10.0.0.5`.

The heavy-route pattern above is an example; derive the list from `HEAVY_PATHS` in `src/ayorai_attractor/api/load_control.py` for the version you deploy.

## Several gateway instances

When the gateway itself runs as several instances, local counters again multiply. Use a gateway that keeps counters in a shared store (for example a Redis-backed rate-limit plugin in the gateway you already operate), or place a single load balancer with a global limit in front. Pick the product by the project's supply-chain criteria in `AGENTS.md` §6: origin, licence, maintenance and transitive dependencies.

## Per-key limits

Limiting by API key at the edge requires the gateway to identify the key. Do not key counters on the raw `Authorization` or `X-API-Key` value in logs or persistent stores; if the gateway supports it, key on a hash of the credential, and keep gateway access logs free of these headers. The application's own per-key limiter remains active in every process.

## Verification

After deploying, confirm from outside the gateway:

```bash
# Expect HTTP 429 once the edge limit is exceeded (nginx does not add
# Retry-After by itself; the application's own 429 does),
# regardless of which replica would have served the request.
# A lookup of a non-existent trace is cheap and still counted.
H="X-API-Key: $ATTRACTOR_TEST_KEY"
for i in $(seq 1 200); do
  curl -s -o /dev/null -w '%{http_code}\n' -H "$H" https://attractor.example/v1/audit/does-not-exist
done | sort | uniq -c
```

and that a forged header does not reset the count (`/health` is exempt from the application limiter, so test with another route):

```bash
curl -s -o /dev/null -w '%{http_code}\n' -H "$H" -H 'X-Forwarded-For: 203.0.113.9' \
  https://attractor.example/v1/audit/does-not-exist
```

Run it right after the loop above: it must still return 429, because it is counted against the caller's real address.

## Limits

This guide describes an operational control outside the repository. The project does not ship, test or certify a gateway configuration; the example is a starting point to adapt and to verify in the target environment.
