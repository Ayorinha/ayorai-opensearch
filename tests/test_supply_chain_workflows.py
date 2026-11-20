"""Image scanning and build provenance stay pinned, scoped and wired as documented."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"


def _load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))
    return data


def _step(job: dict[str, Any], name_prefix: str) -> dict[str, Any]:
    (step,) = [s for s in job["steps"] if str(s.get("name", "")).startswith(name_prefix)]
    return step


def test_no_workflow_uses_the_trivy_actions() -> None:
    for path in WORKFLOWS.glob("*.y*ml"):
        text = path.read_text(encoding="utf-8")
        assert "aquasecurity/trivy-action" not in text, path.name
        assert "aquasecurity/setup-trivy" not in text, path.name


def test_the_image_is_scanned_with_a_checksum_pinned_grype() -> None:
    job = _load("docker.yml")["jobs"]["container-smoke"]
    names = [str(s.get("name", "")) for s in job["steps"]]
    build = names.index("Build production image")
    scan = _step(job, "Scan the image")
    assert names.index(scan["name"]) == build + 1
    assert re.fullmatch(r"\d+\.\d+\.\d+", scan["env"]["GRYPE_VERSION"])
    assert re.fullmatch(r"[0-9a-f]{64}", scan["env"]["GRYPE_SHA256"])
    script = scan["run"]
    assert "set -euo pipefail" in script
    assert "sha256sum --check --strict" in script
    assert script.index("sha256sum") < script.index("tar -xzf")
    assert "--only-fixed --fail-on high" in script
    assert "ayorai-attractor:test" in script
    upload = _step(job, "Upload the image vulnerability report")
    assert upload["if"] == "always()"
    assert re.search(r"@[0-9a-f]{40}$", upload["uses"])


def test_the_docker_workflow_stays_read_only() -> None:
    workflow = _load("docker.yml")
    assert workflow["permissions"] == {"contents": "read"}
    assert "permissions" not in workflow["jobs"]["container-smoke"]


def test_distributions_get_verified_signed_provenance_outside_pull_requests() -> None:
    workflow = _load("ci.yml")
    assert workflow["permissions"] == {"contents": "read"}
    job = workflow["jobs"]["build-distributions"]
    assert job["permissions"] == {
        "contents": "read",
        "id-token": "write",
        "attestations": "write",
    }
    attest = _step(job, "Attest build provenance")
    assert re.fullmatch(
        r"actions/attest-build-provenance@[0-9a-f]{40}", attest["uses"].split(" ")[0]
    )
    assert attest["if"] == "github.event_name != 'pull_request'"
    assert set(attest["with"]["subject-path"].split()) == {"dist/*.tar.gz", "dist/*.whl"}
    verify = _step(job, "Verify the provenance attestations")
    assert verify["if"] == attest["if"]
    assert "gh attestation verify" in verify["run"]
    assert ".github/workflows/ci.yml" in verify["run"]
    names = [str(s.get("name", "")) for s in job["steps"]]
    assert names.index(attest["name"]) > names.index("Verify distribution artifact checksums")
    assert names.index(verify["name"]) == names.index(attest["name"]) + 1


def test_the_image_applies_debian_security_updates_and_fails_closed() -> None:
    dockerfile = (WORKFLOWS.parents[1] / "docker" / "Dockerfile").read_text(encoding="utf-8")
    lines = [line.strip() for line in dockerfile.splitlines()]
    (start,) = [i for i, line in enumerate(lines) if line.startswith("RUN apt-get update")]
    block = " ".join(lines[start : start + 4])
    # An unreachable or unsigned archive must fail the build, not ship stale packages.
    assert "apt-get update --error-on=any" in block
    assert "apt-get upgrade --yes --no-install-recommends" in block
    assert "rm -rf /var/lib/apt/lists/*" in block
    assert lines[0].startswith("FROM python:3.12-slim@sha256:")
    pip_install = next(i for i, line in enumerate(lines) if line.startswith("RUN pip install"))
    assert start < pip_install
