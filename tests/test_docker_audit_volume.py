"""The Compose deployment keeps audit traces across container recreation."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_compose_mounts_a_named_volume_on_the_audit_directory() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    service = compose["services"]["attractor"]
    assert "attractor-audit:/app/.attractor" in service["volumes"]
    assert "attractor-audit" in compose["volumes"]


def test_the_image_creates_the_audit_directory_before_handing_app_to_the_user() -> None:
    dockerfile = (ROOT / "docker" / "Dockerfile").read_text(encoding="utf-8")
    assert dockerfile.index("mkdir -p /app/.attractor") < dockerfile.index(
        "chown -R attractor:attractor /app"
    )


def test_env_example_lists_audit_settings_with_safe_defaults() -> None:
    lines = (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    assert "ATTRACTOR_AUDIT_HMAC_KEYS=" in lines
    assert "ATTRACTOR_AUDIT_HMAC_REQUIRED=false" in lines
    assert "ATTRACTOR_AUDIT_RETENTION_DAYS=" in lines


def test_compose_runs_with_a_read_only_root_and_no_capabilities() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    service = compose["services"]["attractor"]
    assert service["read_only"] is True
    assert service["cap_drop"] == ["ALL"]
    assert "no-new-privileges:true" in service["security_opt"]
    assert any(entry.startswith("/tmp:") and "noexec" in entry for entry in service["tmpfs"])
