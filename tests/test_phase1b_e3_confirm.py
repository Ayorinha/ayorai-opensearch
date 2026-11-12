"""P1 — DEV-B confirmation of E3b-01 on a synthetic score cache (DEC-024 B, DEC-025)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pytest

from scripts.benchmarks.phase1b import e3_confirm
from scripts.benchmarks.phase1b.calibration_v2.aggregate import COHORTS
from scripts.benchmarks.phase1b.calibration_v2.splits import split_dev_a_b
from scripts.benchmarks.phase1b.e3_confirm import _stratified_bootstrap, run_confirm
from scripts.benchmarks.phase1b.score_cache import EXPERIMENTS, build_score_cache

_ORIGINAL_LOAD_ELIGIBILITY = e3_confirm.load_eligibility
_ORIGINAL_NON_ESTIMABLE_GATE = e3_confirm._require_non_estimable_rule
_ORIGINAL_ATOMIC_LOCK_GATE = e3_confirm._require_persistent_atomic_lock
_ORIGINAL_RESERVATION_GATE = e3_confirm._require_lock_reservation

PER_COHORT = 80


def _rows(noise: dict[str, float], seed: int = 3) -> dict[str, list[dict]]:
    rng = np.random.default_rng(seed)
    rows: dict[str, list[dict]] = {model: [] for model in noise}
    for cohort in COHORTS:
        for index in range(PER_COHORT):
            label = index % 2
            for model, sd in noise.items():
                score = float(np.clip(0.5 + (0.12 if label else -0.12) + rng.normal(0, sd), 0, 1))
                rows[model].append(
                    {
                        "record_id": f"{cohort}-{index:03d}",
                        "cohort": cohort,
                        "gold": "SUPPORTED" if label else "NOT_SUPPORTED",
                        "score": score,
                    }
                )
    return rows


CLAIMS_PER_DOC = 4


def _doc_id(record_id: str) -> str:
    import hashlib

    cohort, index = record_id.rsplit("-", 1)
    return hashlib.sha256(f"{cohort}|{int(index) // CLAIMS_PER_DOC}".encode()).hexdigest()


def _cache(rows: dict[str, list[dict]], *, v2: bool = True) -> dict:
    cache = build_score_cache(
        rows, protocols={}, manifest_sha256="m" * 64, source_run_id="1", calibration_v2=None
    )
    if v2:
        cache["schema_version"] = "phase1b-dev-score-cache-v2"
        for entry in cache["models"].values():
            for record in entry["records"]:
                record["doc_id"] = _doc_id(record["record_id"])
    return cache


NOISE = {"factcg": 0.12, "minicheck": 0.12, "mdeberta": 0.2}


@pytest.fixture(autouse=True)
def _approved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    prereg = tmp_path / "PREREG-E3-CONFIRM-DEV-B-v0.8.md"
    prereg.write_text("**Status:** Aprovado pelo mantenedor em 2026-11-08.\n", encoding="utf-8")
    monkeypatch.setattr(e3_confirm, "PREREGISTRATION_PATH", prereg)
    eligibility = _ORIGINAL_LOAD_ELIGIBILITY()
    eligibility["confirmatory_authorization"] = {
        "decision": "DEC-026",
        "status": "approved",
        "scope": "p1-dev-b-confirmatory",
        "approved_on": "2026-11-09",
        "eligibility_sha256": e3_confirm.ELIGIBILITY_SHA256,
        "selection_exposure": {
            "status": "resolved",
            "decision_ref": "TEST-ONLY-SYNTHETIC-DECISION",
        },
    }
    monkeypatch.setattr(e3_confirm, "load_eligibility", lambda: eligibility)
    # Algorithm tests bypass policy gates only to exercise synthetic data paths.
    # Separate tests assert that production gates fail closed.
    monkeypatch.setattr(e3_confirm, "_require_non_estimable_rule", lambda: None)
    monkeypatch.setattr(e3_confirm, "_require_lock_reservation", lambda: None)


def test_confirmation_report_is_aggregate_and_complete() -> None:
    report = run_confirm(_cache(_rows(NOISE)))
    assert report["experiment"] == "e3-confirm-dev-b"
    expected_partition = " ".join(
        (
            "conditional confirmation on partially used holdout",
            "(DEV-B; calibrated on DEV-A)",
        )
    )
    expected_classification = "confirmação condicional em holdout parcialmente usado (DEV-B)"
    assert report["partition"] == expected_partition
    assert report["confirmation_classification"] == expected_classification
    assert report["configuration"] == "E3b-01"
    assert report["outcome"] in {"CONFIRMED", "NOT_CONFIRMED"}
    assert "Wice" not in report["common_cohorts"]
    assert len(report["common_cohorts"]) == len(COHORTS) - 1
    assert report["dev_a_count"] + report["dev_b_count"] == report["record_count"]
    primary = report["primary_interval"]
    assert primary["replicates"] == 2000 and primary["estimable"] is True
    low, high = primary["ci95_difference"]
    assert low <= report["delta"] <= high + 1e-12
    # Two equally informative, independent members: averaging should help.
    assert report["delta"] > 0
    serialized = json.dumps(report)
    assert "record_id" not in serialized
    assert "AggreFact-CNN-000" not in serialized


def test_confirmation_is_deterministic() -> None:
    cache = _cache(_rows(NOISE))
    assert run_confirm(cache)["report_sha256"] == run_confirm(cache)["report_sha256"]


def test_dev_b_labels_never_reach_fitted_quantities() -> None:
    rows = _rows(NOISE)
    ids = sorted({r["record_id"] for r in rows["factcg"]})
    cohorts = {r["record_id"]: r["cohort"] for r in rows["factcg"]}
    assignments, _ = split_dev_a_b(ids, [cohorts[r] for r in ids])
    flipped = {
        model: [
            dict(
                r,
                gold=(
                    ("NOT_SUPPORTED" if r["gold"] == "SUPPORTED" else "SUPPORTED")
                    if assignments[r["record_id"]] == "DEV-B"
                    else r["gold"]
                ),
            )
            for r in records
        ]
        for model, records in rows.items()
    }
    original = run_confirm(_cache(rows))
    altered = run_confirm(_cache(flipped))
    assert original["thresholds_by_cohort"] == altered["thresholds_by_cohort"]
    assert original["ba_by_cohort"] != altered["ba_by_cohort"]


def test_refuses_repository_preregistration_until_approved(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        e3_confirm,
        "PREREGISTRATION_PATH",
        e3_confirm.REPOSITORY_ROOT / "docs" / "benchmarks" / "PREREG-E3-CONFIRM-DEV-B-v0.8.md",
    )
    with pytest.raises(RuntimeError, match="not approved|not on this revision"):
        run_confirm(_cache(_rows(NOISE)))


def test_refuses_changed_eligibility_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(e3_confirm, "ELIGIBILITY_SHA256", "0" * 64)
    with pytest.raises(RuntimeError, match="eligibility"):
        run_confirm(_cache(_rows(NOISE)))


def test_refuses_v1_cache_without_document_ids() -> None:
    cache = _cache(_rows(NOISE), v2=False)
    assert cache["schema_version"] == "phase1b-dev-score-cache-v1"
    with pytest.raises(ValueError, match="v2 score cache with document ids"):
        run_confirm(cache)


def test_refuses_cache_without_members() -> None:
    with pytest.raises(ValueError, match="lacks members"):
        run_confirm(_cache(_rows({"factcg": 0.1, "mdeberta": 0.1})))


def test_identical_arms_give_zero_interval() -> None:
    y = [0, 1] * 30
    p = [0, 1, 1, 0] * 15
    result = _stratified_bootstrap({"a": (y, p, p), "b": (y, p, p)})
    assert result["ci95_difference"] == [0.0, 0.0]
    assert result["invalid_replicates"] == 0


def test_experiment_is_registered() -> None:
    assert "e3-confirm-dev-b" in EXPERIMENTS


def test_estimand_statement_and_loco_are_descriptive() -> None:
    report = run_confirm(_cache(_rows(NOISE)))
    assert "No superiority claim is made for any individual cohort" in report["estimand_statement"]
    loco = report["leave_one_cohort_out_delta"]
    assert set(loco) == set(report["common_cohorts"])
    assert report["leave_one_cohort_out_role"].startswith("descriptive")


@pytest.mark.parametrize("defect", ["gold", "cohort", "duplicate", "nan", "range", "doc_id"])
def test_strict_member_validation(defect: str) -> None:
    rows = _rows(NOISE)
    cache = _cache(rows)
    target = cache["models"]["minicheck"]["records"]
    if defect == "gold":
        target[0]["gold"] = "SUPPORTED" if target[0]["gold"] == "NOT_SUPPORTED" else "NOT_SUPPORTED"
        message = "disagrees"
    elif defect == "cohort":
        target[0]["cohort"] = "another-cohort"
        message = "disagrees"
    elif defect == "duplicate":
        target.append(dict(target[0]))
        message = "duplicate"
    elif defect == "nan":
        target[0]["score"] = float("nan")
        message = "outside"
    elif defect == "doc_id":
        target[0]["doc_id"] = "z" * 64
        message = "doc_id"
    else:
        target[0]["score"] = 1.5
        message = "outside"
    with pytest.raises(ValueError, match=message):
        run_confirm(cache)


def test_refuses_when_a_confirmation_report_is_published_without_consuming_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    published = tmp_path / "reports" / "benchmarks" / "2026-12-01-p1-dev-b-confirmation"
    published.mkdir(parents=True)
    monkeypatch.setattr(e3_confirm, "REPOSITORY_ROOT", tmp_path)
    lock_calls = []
    monkeypatch.setattr(
        e3_confirm,
        "_require_lock_reservation",
        lambda: lock_calls.append("reserved"),
    )
    with pytest.raises(RuntimeError, match="single-use"):
        run_confirm(_cache(_rows(NOISE)))
    assert lock_calls == []


def test_invalid_cache_is_rejected_before_consuming_persistent_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = _cache(_rows(NOISE))
    records = cache["models"]["minicheck"]["records"]
    records[1]["record_id"] = records[0]["record_id"]
    lock_calls: list[str] = []
    monkeypatch.setattr(
        e3_confirm,
        "_require_lock_reservation",
        lambda: lock_calls.append("reserved"),
    )
    with pytest.raises(ValueError, match="duplicate record_id"):
        run_confirm(cache)
    assert lock_calls == []


def test_dev_a_preflight_failure_is_rejected_before_reservation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lock_calls: list[str] = []
    monkeypatch.setattr(
        e3_confirm,
        "crossfit_folds",
        lambda *_args, **_kwargs: ({}, ["synthetic insufficient stratum"]),
    )
    monkeypatch.setattr(
        e3_confirm,
        "_require_lock_reservation",
        lambda: lock_calls.append("reserved"),
    )
    with pytest.raises(ValueError, match="cross-fitting strata"):
        run_confirm(_cache(_rows(NOISE)))
    assert lock_calls == []


def test_eligibility_cannot_be_injected() -> None:
    import inspect

    assert list(inspect.signature(run_confirm).parameters) == ["cache"]


def test_primary_interval_resamples_documents() -> None:
    report = run_confirm(_cache(_rows(NOISE)))
    primary = report["primary_interval"]
    assert primary["unit"].startswith("document")
    assert "document clusters" in primary["method"]
    assert set(report["dev_b_documents_by_cohort"]) == set(report["common_cohorts"])
    diagnostics = report["diagnostics"]
    assert diagnostics["role"].startswith("exploratory; not inferential")
    assert diagnostics["document_influence"]["documents_used"] > 0
    assert "bca_interval_95" not in diagnostics
    assert "record" in diagnostics["record_level_bootstrap"]["method"]


def test_document_bootstrap_widens_interval_under_within_document_correlation() -> None:
    """When claims of a document share the same outcome, case resampling is too narrow."""

    from scripts.benchmarks.phase1b.e3_confirm import _document_bootstrap, _document_stats

    rng = np.random.default_rng(11)
    stats = {}
    groups = {}
    for cohort in ("a", "b"):
        y, e, f, docs = [], [], [], []
        for doc in range(30):
            ens_right = rng.random() < 0.8
            cmp_right = rng.random() < 0.7
            for claim in range(8):
                label = claim % 2
                y.append(label)
                e.append(label if ens_right else 1 - label)
                f.append(label if cmp_right else 1 - label)
                docs.append(f"{cohort}-{doc}")
        _, stats[cohort] = _document_stats({"y": y, "e": e, "f": f, "docs": docs})
        groups[cohort] = (y, e, f)
    doc_ci = _document_bootstrap(stats)[0]["ci95_difference"]
    case_ci = e3_confirm._stratified_bootstrap(groups)["ci95_difference"]
    assert (doc_ci[1] - doc_ci[0]) > 1.5 * (case_ci[1] - case_ci[0])


def test_document_stats_match_balanced_accuracy() -> None:
    from scripts.benchmarks.phase1b.calibration import balanced_accuracy
    from scripts.benchmarks.phase1b.e3_confirm import _document_stats, _paired_ba_delta

    rng = np.random.default_rng(5)
    y = rng.integers(0, 2, 60).tolist()
    e = rng.integers(0, 2, 60).tolist()
    f = rng.integers(0, 2, 60).tolist()
    docs = [f"d{i // 3}" for i in range(60)]
    _, stats = _document_stats({"y": y, "e": e, "f": f, "docs": docs})
    delta, invalid = _paired_ba_delta(stats.sum(axis=0))
    assert not invalid
    assert abs(float(delta) - (balanced_accuracy(y, e) - balanced_accuracy(y, f))) < 1e-12


def test_v1_cache_is_refused() -> None:
    with pytest.raises(ValueError, match="v2 score cache"):
        run_confirm(_cache(_rows(NOISE), v2=False))


def test_members_must_agree_on_documents() -> None:
    cache = _cache(_rows(NOISE))
    cache["models"]["minicheck"]["records"][0]["doc_id"] = "0" * 64
    with pytest.raises(ValueError, match="documents"):
        run_confirm(cache)


@pytest.mark.parametrize("defect", ["empty", "single_class"])
def test_dev_b_cohort_must_be_estimable(defect: str, monkeypatch: pytest.MonkeyPatch) -> None:
    cache = _cache(_rows(NOISE))
    target = "ClaimVerify"
    original = e3_confirm.split_dev_a_b

    def patched(ids, cohorts):
        assignments, info = original(ids, cohorts)
        for record_id, cohort in zip(ids, cohorts, strict=True):
            if cohort != target or assignments[record_id] != "DEV-B":
                continue
            if defect == "empty":
                assignments[record_id] = "DEV-A"
            elif int(record_id.rsplit("-", 1)[1]) % 2 == 0:
                assignments[record_id] = "DEV-A"
        return assignments, info

    monkeypatch.setattr(e3_confirm, "split_dev_a_b", patched)
    with pytest.raises(ValueError, match="no DEV-B records|lacks a class"):
        run_confirm(cache)


def test_refuses_until_non_estimable_rule_is_implemented(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(e3_confirm, "NON_ESTIMABLE_RULE", {"synthetic": True})
    with pytest.raises(RuntimeError, match="non-null rule object is insufficient"):
        _ORIGINAL_NON_ESTIMABLE_GATE()


def test_non_estimable_gate_blocks_before_consuming_persistent_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def blocked_gate() -> None:
        raise RuntimeError("NON_ESTIMABLE_GATE_SENTINEL")

    def forbidden_lock() -> None:
        pytest.fail("persistent lock must not be consumed before non-estimable gate")

    monkeypatch.setitem(run_confirm.__globals__, "_require_non_estimable_rule", blocked_gate)
    monkeypatch.setitem(run_confirm.__globals__, "_require_lock_reservation", forbidden_lock)
    with pytest.raises(RuntimeError, match="NON_ESTIMABLE_GATE_SENTINEL"):
        run_confirm(_cache(_rows(NOISE)))


def test_refuses_without_persistent_atomic_execution_lock() -> None:
    with pytest.raises(RuntimeError, match="P1"):
        _ORIGINAL_ATOMIC_LOCK_GATE()


class _FakeHttpResponse:
    def __init__(self, payload: dict, status: int = 201) -> None:
        self.payload = json.dumps(payload).encode("utf-8")
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


def _set_github_lock_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_REPOSITORY", "Ayorinha/ayorai-opensearch")
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    monkeypatch.setenv("GITHUB_RUN_ID", "42914353626")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    monkeypatch.setenv("P1_LOCK_TOKEN", "synthetic-short-lived-app-token")


def test_persistent_lock_creates_exact_single_use_branch_ref(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_github_lock_environment(monkeypatch)
    assert e3_confirm.P1_LOCK_REF == "refs/heads/p1-dev-b-confirmation-lock"
    calls: list[dict] = []

    def fake_urlopen(request, timeout):
        calls.append(
            {
                "url": request.full_url,
                "method": request.get_method(),
                "payload": json.loads(request.data) if request.data else None,
                "timeout": timeout,
            }
        )
        if request.get_method() == "DELETE":
            return _FakeHttpResponse({}, status=204)
        return _FakeHttpResponse(
            {
                "ref": e3_confirm.P1_LOCK_REF,
                "object": {"type": "commit", "sha": "a" * 40},
            }
        )

    monkeypatch.setattr(e3_confirm, "urlopen", fake_urlopen)
    created = _ORIGINAL_ATOMIC_LOCK_GATE()
    assert "P1_LOCK_TOKEN" not in os.environ
    assert calls == [
        {
            "url": "https://api.github.com/repos/Ayorinha/ayorai-opensearch/git/refs",
            "method": "POST",
            "payload": {"ref": e3_confirm.P1_LOCK_REF, "sha": "a" * 40},
            "timeout": 15,
        },
        {
            "url": "https://api.github.com/installation/token",
            "method": "DELETE",
            "payload": None,
            "timeout": 15,
        },
    ]
    assert created == {
        "ref": e3_confirm.P1_LOCK_REF,
        "sha": "a" * 40,
        "token_revocation": "revoked",
    }


def test_persistent_lock_never_uses_legacy_github_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_github_lock_environment(monkeypatch)
    monkeypatch.delenv("P1_LOCK_TOKEN")
    monkeypatch.setenv("GITHUB_TOKEN", "synthetic-read-only-token")
    monkeypatch.setenv("GH_TOKEN", "synthetic-legacy-token")

    def forbidden_urlopen(request, timeout):
        raise AssertionError("legacy GitHub tokens must never be used for lock creation")

    monkeypatch.setattr(e3_confirm, "urlopen", forbidden_urlopen)
    with pytest.raises(RuntimeError, match="P1_LOCK_TOKEN"):
        _ORIGINAL_ATOMIC_LOCK_GATE()
    assert os.environ["GITHUB_TOKEN"] == "synthetic-read-only-token"
    assert os.environ["GH_TOKEN"] == "synthetic-legacy-token"


def test_persistent_lock_refuses_existing_reservation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from io import BytesIO
    from urllib.error import HTTPError

    _set_github_lock_environment(monkeypatch)

    def conflict(request, timeout):
        raise HTTPError(request.full_url, 422, "already exists", {}, BytesIO(b"{}"))

    monkeypatch.setattr(e3_confirm, "urlopen", conflict)
    with pytest.raises(RuntimeError, match="already reserved"):
        _ORIGINAL_ATOMIC_LOCK_GATE()


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("GITHUB_ACTIONS", None),
        ("GITHUB_REPOSITORY", "fork/ayorai-opensearch"),
        ("GITHUB_REF", "refs/heads/feature"),
        ("GITHUB_EVENT_NAME", "push"),
        ("GITHUB_RUN_ID", "invalid"),
        ("GITHUB_RUN_ATTEMPT", "2"),
        ("GITHUB_SHA", "not-a-commit"),
        ("NO_TOKENS", None),
    ],
)
def test_persistent_lock_refuses_untrusted_or_incomplete_runner_context(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str | None
) -> None:
    _set_github_lock_environment(monkeypatch)
    if name == "NO_TOKENS":
        monkeypatch.delenv("P1_LOCK_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
    elif value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)
    with pytest.raises(RuntimeError, match="P1|canonical|commit SHA|token|attempt"):
        _ORIGINAL_ATOMIC_LOCK_GATE()


def test_persistent_lock_refuses_non_commit_ref_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_github_lock_environment(monkeypatch)
    monkeypatch.setattr(
        e3_confirm,
        "urlopen",
        lambda request, timeout: _FakeHttpResponse(
            {"ref": e3_confirm.P1_LOCK_REF, "object": {"type": "tag", "sha": "a" * 40}}
        ),
    )
    with pytest.raises(RuntimeError, match="mismatched"):
        _ORIGINAL_ATOMIC_LOCK_GATE()


def test_persistent_lock_refuses_mismatched_github_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_github_lock_environment(monkeypatch)
    monkeypatch.setattr(
        e3_confirm,
        "urlopen",
        lambda request, timeout: _FakeHttpResponse(
            {"ref": e3_confirm.P1_LOCK_REF, "object": {"type": "commit", "sha": "b" * 40}}
        ),
    )
    with pytest.raises(RuntimeError, match="mismatched"):
        _ORIGINAL_ATOMIC_LOCK_GATE()


def test_refuses_when_dec026_has_no_confirmatory_approval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(e3_confirm, "load_eligibility", _ORIGINAL_LOAD_ELIGIBILITY)
    with pytest.raises(RuntimeError, match="DEC-026"):
        run_confirm(_cache(_rows(NOISE)))


def test_confirmatory_eligibility_is_bound_to_matrix_and_selection_decision() -> None:
    eligibility = _ORIGINAL_LOAD_ELIGIBILITY()
    with pytest.raises(RuntimeError, match="DEC-026"):
        e3_confirm._validate_confirmatory_eligibility(
            eligibility, eligibility_sha256=e3_confirm.ELIGIBILITY_SHA256
        )


def test_token_is_revoked_even_when_reservation_conflicts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from io import BytesIO
    from urllib.error import HTTPError

    _set_github_lock_environment(monkeypatch)
    methods: list[str] = []

    def conflict_then_revoke(request, timeout):
        methods.append(request.get_method())
        if request.get_method() == "DELETE":
            return _FakeHttpResponse({}, status=204)
        raise HTTPError(request.full_url, 422, "already exists", {}, BytesIO(b"{}"))

    monkeypatch.setattr(e3_confirm, "urlopen", conflict_then_revoke)
    with pytest.raises(RuntimeError, match="already reserved"):
        _ORIGINAL_ATOMIC_LOCK_GATE()
    assert methods == ["POST", "DELETE"]
    assert "P1_LOCK_TOKEN" not in os.environ


def _reservation_ready(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    _set_github_lock_environment(monkeypatch)
    monkeypatch.delenv("PHASE1B_ARTIFACT_ENCRYPTION_KEY", raising=False)
    monkeypatch.setattr(e3_confirm, "preflight_confirm", lambda: ("2026-11-12", {}, "0" * 64))
    monkeypatch.setattr(e3_confirm, "published_confirmation_exists", lambda: False)
    monkeypatch.setattr(
        e3_confirm,
        "_require_persistent_atomic_lock",
        lambda: {"ref": e3_confirm.P1_LOCK_REF, "sha": "a" * 40, "token_revocation": "revoked"},
    )
    return tmp_path / "p1-lock-reservation.json"


def test_reserve_lock_writes_run_bound_reservation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = _reservation_ready(monkeypatch, tmp_path)
    reservation = e3_confirm.reserve_lock(path, "c" * 64)
    assert json.loads(path.read_text(encoding="utf-8")) == reservation
    assert reservation == {
        "schema_version": "p1-lock-reservation-v1",
        "repository": "Ayorinha/ayorai-opensearch",
        "ref": e3_confirm.P1_LOCK_REF,
        "sha": "a" * 40,
        "run_id": "42914353626",
        "run_attempt": "1",
        "envelope_sha256": "c" * 64,
        "token_revocation": "revoked",
    }
    with pytest.raises(FileExistsError):
        e3_confirm.reserve_lock(path, "c" * 64)


def test_reserve_lock_refuses_while_decryption_key_is_present(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = _reservation_ready(monkeypatch, tmp_path)
    monkeypatch.setenv("PHASE1B_ARTIFACT_ENCRYPTION_KEY", "synthetic-key")
    with pytest.raises(RuntimeError, match="decryption key"):
        e3_confirm.reserve_lock(path, "c" * 64)
    assert not path.exists()


def test_reserve_lock_refuses_when_report_is_published(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = _reservation_ready(monkeypatch, tmp_path)
    monkeypatch.setattr(e3_confirm, "published_confirmation_exists", lambda: True)
    monkeypatch.setattr(
        e3_confirm,
        "_require_persistent_atomic_lock",
        lambda: pytest.fail("published report must stop before the ref is created"),
    )
    with pytest.raises(RuntimeError, match="single-use"):
        e3_confirm.reserve_lock(path, "c" * 64)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("sha", "b" * 40),
        ("run_id", "1"),
        ("run_attempt", "2"),
        ("envelope_sha256", "d" * 64),
        ("ref", "refs/heads/other"),
        ("repository", "fork/ayorai-opensearch"),
    ],
)
def test_lock_reservation_must_match_this_run_and_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, field: str, value: str
) -> None:
    path = _reservation_ready(monkeypatch, tmp_path)
    reservation = e3_confirm.reserve_lock(path, "c" * 64)
    monkeypatch.setenv("P1_LOCK_RESERVATION", str(path))
    monkeypatch.setenv("P1_CACHE_ENVELOPE_SHA256", "c" * 64)
    _ORIGINAL_RESERVATION_GATE()
    path.write_text(json.dumps({**reservation, field: value}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="does not match"):
        _ORIGINAL_RESERVATION_GATE()


def test_lock_reservation_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_github_lock_environment(monkeypatch)
    monkeypatch.delenv("P1_LOCK_RESERVATION", raising=False)
    monkeypatch.delenv("P1_CACHE_ENVELOPE_SHA256", raising=False)
    with pytest.raises(RuntimeError, match="reservation"):
        _ORIGINAL_RESERVATION_GATE()


def test_validate_only_stops_before_reservation_and_outcomes() -> None:
    result = e3_confirm.validate_cache(_cache(_rows(NOISE)))
    assert result == {"experiment": "e3-confirm-dev-b", "cache_preflight": "passed"}
