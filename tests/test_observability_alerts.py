"""The shipped Prometheus alert rules refer only to metrics the service exposes."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from ayorai_attractor.api.http_metrics import HttpMetrics

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "docker" / "observability" / "prometheus-alerts.yml"


def _exposed_metric_names() -> set[str]:
    metrics = HttpMetrics()
    metrics.observe("/v1/check", "POST", 200, 0.1)
    names = set()
    for line in metrics.render().splitlines():
        if line and not line.startswith("#"):
            names.add(re.split(r"[{ ]", line, maxsplit=1)[0])
    return names


def test_alert_rules_are_well_formed_and_use_exposed_metrics() -> None:
    document = yaml.safe_load(RULES.read_text(encoding="utf-8"))
    rules = [rule for group in document["groups"] for rule in group["rules"]]
    assert rules
    exposed = _exposed_metric_names()
    names = set()
    for rule in rules:
        assert set(rule) <= {"alert", "expr", "for", "labels", "annotations"}
        assert rule["labels"]["severity"] in {"page", "ticket"}
        assert rule["annotations"]["summary"]
        names.add(rule["alert"])
        for metric in re.findall(r"\b(attractor_[a-z_]+)", rule["expr"]):
            assert metric in exposed, f"{rule['alert']} uses unknown metric {metric}"
    assert len(names) == len(rules), "alert names must be unique"


def test_every_alert_is_documented() -> None:
    document = yaml.safe_load(RULES.read_text(encoding="utf-8"))
    doc = (ROOT / "docs" / "observability" / "SLO-AND-ALERTS.md").read_text(encoding="utf-8")
    for group in document["groups"]:
        for rule in group["rules"]:
            assert f"`{rule['alert']}`" in doc
