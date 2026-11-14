"""Canonical article IDs and the cluster/component IDs built from them (DEC-027, D1).

A canonical article ID matches ARTICLE_ID_RE, has at most 200 characters and does not
start with a reserved prefix. Because "+" never occurs inside an article ID, the
literal formats of DEC-019 ("bundle:" + IDs joined by "+") and DEC-023
("component:" + IDs joined by "+") are unambiguous and reversible. IDs outside the
grammar are rejected, never normalised (fail closed).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import cast

ARTICLE_ID_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*(?::[a-z0-9]+(?:-[a-z0-9]+)*)*")
MAX_ARTICLE_ID_LENGTH = 200
BUNDLE_PREFIX = "bundle:"
COMPONENT_PREFIX = "component:"
RESERVED_PREFIXES = (BUNDLE_PREFIX, COMPONENT_PREFIX)
SEPARATOR = "+"


def is_article_id(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) <= MAX_ARTICLE_ID_LENGTH
        and ARTICLE_ID_RE.fullmatch(value) is not None
        and not value.startswith(RESERVED_PREFIXES)
    )


def require_article_id(value: object, where: str) -> str:
    if not is_article_id(value):
        raise ValueError(
            f"{where}: {value!r} is not a canonical article ID "
            "(lowercase ASCII letters, digits, '-' and ':' segments; no '+'; "
            f"at most {MAX_ARTICLE_ID_LENGTH} characters; not bundle:/component:)"
        )
    return cast(str, value)


def _join(prefix: str, article_ids: Iterable[str], where: str, *, minimum: int) -> str:
    members = sorted({require_article_id(item, where) for item in article_ids})
    if len(members) < minimum:
        raise ValueError(f"{where}: {prefix} needs at least {minimum} distinct article IDs")
    return prefix + SEPARATOR.join(members)


def _split(prefix: str, value: object, where: str, *, minimum: int) -> tuple[str, ...]:
    if not isinstance(value, str) or not value.startswith(prefix):
        raise ValueError(f"{where}: {value!r} does not start with {prefix!r}")
    members = value.removeprefix(prefix).split(SEPARATOR)
    for member in members:
        require_article_id(member, where)
    if len(members) < minimum or members != sorted(set(members)):
        raise ValueError(f"{where}: {prefix} must contain at least {minimum} unique, sorted IDs")
    return tuple(members)


def bundle_id(article_ids: Iterable[str], where: str = "bundle") -> str:
    """DEC-019 bundle: two or more articles without a single main one."""

    return _join(BUNDLE_PREFIX, article_ids, where, minimum=2)


def parse_bundle_id(value: object, where: str = "bundle") -> tuple[str, ...]:
    return _split(BUNDLE_PREFIX, value, where, minimum=2)


def component_id(article_ids: Iterable[str], where: str = "component") -> str:
    """DEC-023 component ID: "component:" + unique article IDs, sorted, joined by "+"."""

    return _join(COMPONENT_PREFIX, article_ids, where, minimum=1)


def parse_component_id(value: object, where: str = "component") -> tuple[str, ...]:
    return _split(COMPONENT_PREFIX, value, where, minimum=1)


def cluster_members(value: object, where: str) -> tuple[str, ...]:
    """Article IDs named by a bootstrap_cluster_id: one article or a bundle."""

    if isinstance(value, str) and value.startswith(BUNDLE_PREFIX):
        return parse_bundle_id(value, where)
    return (require_article_id(value, where),)
