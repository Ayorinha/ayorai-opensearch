"""Canonical article IDs, bundles and component IDs (DEC-027, D1). Synthetic IDs only."""

from __future__ import annotations

import pytest
from hypothesis import given, settings, strategies as st

from evals.ptbr.rgc_ids import (
    bundle_id,
    cluster_members,
    component_id,
    is_article_id,
    parse_bundle_id,
    parse_component_id,
    require_article_id,
)


@pytest.mark.parametrize(
    "value",
    [
        "syn-a",
        "syn:a",
        "planalto-lgpd-13709-2018:art-7",
        "planalto-lgpd-13709-2018:art-5-a",
        "syn:art-1:par-2:inc-3",
        "a" * 200,
        "bundle",  # a plain word is not the reserved prefix "bundle:"
    ],
)
def test_valid_article_ids(value: str) -> None:
    assert is_article_id(value)
    assert require_article_id(value, "t") == value


@pytest.mark.parametrize(
    "value",
    [
        "",
        "syn:a+syn:b",
        "Syn:a",
        "syn: a",
        " syn:a",
        "syn:a ",
        "syn::a",
        "syn:-a",
        "syn:a-",
        "syn--a",
        "syn_a",
        "syn:art.5",
        "syn:art-5º",
        "bundle:syn-a",
        "component:syn-a",
        "a" * 201,
        None,
        7,
    ],
)
def test_invalid_article_ids_fail_closed(value: object) -> None:
    assert not is_article_id(value)
    with pytest.raises(ValueError, match="not a canonical article ID"):
        require_article_id(value, "t")


_ARTICLE_ATOM = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=6)
_ARTICLE_GROUP = st.lists(_ARTICLE_ATOM, min_size=1, max_size=3).map("-".join)
_ARTICLE_ID = st.lists(_ARTICLE_GROUP, min_size=1, max_size=3).map(":".join)


@given(st.lists(_ARTICLE_ID, min_size=2, max_size=8, unique=True))
@settings(max_examples=100, deadline=None, derandomize=True)
def test_bundle_and_component_serializers_round_trip_for_generated_ids(
    article_ids: list[str],
) -> None:
    expected = tuple(sorted(article_ids))
    bundle = bundle_id(article_ids)
    component = component_id(article_ids)

    assert parse_bundle_id(bundle) == expected
    assert parse_component_id(component) == expected
    assert bundle_id(reversed(article_ids)) == bundle
    assert component_id(reversed(article_ids)) == component


def test_bundle_round_trip_and_canonical_order() -> None:
    assert bundle_id(["syn:b", "syn:a", "syn:b"]) == "bundle:syn:a+syn:b"
    assert parse_bundle_id("bundle:syn:a+syn:b") == ("syn:a", "syn:b")
    with pytest.raises(ValueError, match="at least 2"):
        bundle_id(["syn:a"])
    for bad in ("bundle:syn:b+syn:a", "bundle:syn:a+syn:a", "bundle:syn:a", "bundle:syn:a+"):
        with pytest.raises(ValueError):
            parse_bundle_id(bad)


def test_component_id_is_dec023_literal_and_reversible() -> None:
    assert component_id(["syn:b", "syn:a"]) == "component:syn:a+syn:b"
    assert component_id(["syn:a"]) == "component:syn:a"
    assert parse_component_id("component:syn:a+syn:b") == ("syn:a", "syn:b")
    with pytest.raises(ValueError):
        component_id(["syn:a+syn:b"])


def test_single_article_and_two_articles_never_collide() -> None:
    # The ambiguity found in the review: "syn:a+syn:b" as one ID versus two IDs.
    assert component_id(["syn:a", "syn:b"]) == "component:syn:a+syn:b"
    with pytest.raises(ValueError):
        component_id(["syn:a+syn:b"])
    with pytest.raises(ValueError):
        cluster_members("syn:a+syn:b", "t")


def test_cluster_members() -> None:
    assert cluster_members("syn:a", "t") == ("syn:a",)
    assert cluster_members("bundle:syn:a+syn:b", "t") == ("syn:a", "syn:b")
    with pytest.raises(ValueError):
        cluster_members("component:syn:a", "t")
