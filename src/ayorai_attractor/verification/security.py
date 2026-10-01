"""R1 response-safety helpers.

Document text is treated as data. These helpers deliberately do not rewrite,
remove, or downgrade factual evidence merely because an excerpt contains
instruction-like text.
"""

def contains_secret(value: object, secret: str) -> bool:
    """Recursively detect an exact secret in response-shaped data."""
    if isinstance(value, str):
        return secret in value
    if isinstance(value, dict):
        return any(contains_secret(k, secret) or contains_secret(v, secret) for k, v in value.items())
    if isinstance(value, (list, tuple, set, frozenset)):
        return any(contains_secret(item, secret) for item in value)
    return False


def assert_no_secret(value: object, secret: str) -> None:
    """Raise when an evaluation secret appears in any response field."""
    if contains_secret(value, secret):
        raise ValueError("response contains an evaluation secret")
