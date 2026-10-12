#!/usr/bin/env python3
"""Create deterministic, derived Judge 2 Golden files without mutating legacy inputs."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / "rules" / "judge-2.0.0.json"
SOURCES = (
    ("v0", ROOT / "evals" / "golden" / "v0.jsonl"),
    ("v0.1", ROOT / "evals" / "golden" / "v0.1.jsonl"),
)
MIGRATION_METHOD = "adr-009-§11-r2-derived-v1"
MAPPING_VERSION = "judge2-golden-map/1.0.0"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: each JSONL record must be an object")
        records.append(value)
    return records


def dump_jsonl(records: list[dict[str, Any]]) -> bytes:
    return b"".join(
        (
            json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("utf-8")
        for record in records
    )


def map_atomic(label: object, support_clusters: object) -> tuple[object, object, str | None]:
    if label == "VERIFIED":
        return "SUPPORTED", "R3", None
    if label == "SUPPORTED":
        return "SUPPORTED", "R2", None
    if label == "PARTIALLY_SUPPORTED" and support_clusters == 1:
        return "SUPPORTED", "R1", None
    if label == "PARTIALLY_SUPPORTED":
        return label, None, (
            "S não está registrado como 1 no caso de origem; "
            "não inferir clusters a partir de must_cite"
        )
    if label == "UNVERIFIED":
        return label, "R0", None
    if label in {"REFUTED", "CONFLICTING"}:
        return label, None, None
    return label, None, "rótulo de origem não reconhecido pelo mapeamento ADR-009 §11"


def composite_k(labels: list[object]) -> str:
    if not labels:
        raise ValueError("composite claim has no atomic labels")
    if "REFUTED" in labels:
        return "REFUTED"
    if "CONFLICTING" in labels:
        return "CONFLICTING"
    if all(label == "SUPPORTED" for label in labels):
        return "SUPPORTED"
    if "SUPPORTED" in labels:
        return "PARTIALLY_SUPPORTED"
    return "UNVERIFIED"


def transform_case(case: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]], int]:
    transformed = dict(case)
    claims = case.get("expected_claims")
    non_migratable: list[dict[str, str]] = []
    migrated_count = 0
    mapped_claims: list[dict[str, Any]] = []

    if isinstance(claims, list) and claims:
        for index, claim in enumerate(claims):
            if not isinstance(claim, dict) or "verdict" not in claim:
                non_migratable.append({
                    "field": f"expected_claims[{index}]",
                    "reason": "estrutura da claim ou campo verdict ausente",
                })
                continue
            label, robustness, reason = map_atomic(
                claim.get("verdict"), claim.get("support_clusters")
            )
            mapped = dict(claim)
            mapped["verdict"] = label
            mapped["robustness"] = robustness
            mapped_claims.append(mapped)
            if label != claim.get("verdict") or robustness is not None:
                migrated_count += 1
            if reason:
                non_migratable.append({
                    "field": f"expected_claims[{index}]",
                    "reason": reason,
                })
        transformed["expected_claims"] = mapped_claims
        labels = [claim.get("verdict") for claim in mapped_claims]
        if len(mapped_claims) == len(claims) and not any(
            item["field"].startswith("expected_claims[") for item in non_migratable
        ):
            transformed["expected_verdict"] = composite_k(labels)
            transformed["global"] = composite_k(labels)
        else:
            transformed["expected_verdict"] = None
            transformed["global"] = None
            non_migratable.append({
                "field": "expected_verdict/global",
                "reason": (
                    "composição K não derivável sem inventar o mapeamento "
                    "de uma ou mais claims"
                ),
            })
    else:
        non_migratable.append({
            "field": "expected_claims",
            "reason": (
                "caso sem claims atômicas explícitas; veredito composto "
                "não pode ser recalculado por K"
            ),
        })
        transformed["expected_verdict"] = None
        transformed["global"] = None

    transformed["migration"] = {
        "method": MIGRATION_METHOD,
        "mapping_version": MAPPING_VERSION,
        "source_expected_verdict": case.get("expected_verdict", case.get("global")),
    }
    return transformed, non_migratable, migrated_count


def migrate(
    source_name: str,
    source_path: Path,
    output_dir: Path,
    source_commit: str,
) -> dict[str, Any]:
    source_bytes = source_path.read_bytes()
    cases = read_jsonl(source_path)
    derived: list[dict[str, Any]] = []
    unresolved: list[dict[str, str]] = []
    migrated_count = 0
    migrated_cases = 0
    non_migratable_case_ids: set[str] = set()

    for case in cases:
        case_id = str(case.get("id", "<missing-id>"))
        converted, reasons, count = transform_case(case)
        derived.append(converted)
        migrated_count += count
        if reasons:
            non_migratable_case_ids.add(case_id)
        else:
            migrated_cases += 1
        unresolved.extend(
            {"case_id": case_id, **reason} for reason in reasons
        )

    out_name = f"{source_name}-r2.jsonl"
    out_path = output_dir / out_name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_bytes = dump_jsonl(derived)
    out_path.write_bytes(out_bytes)

    rules_bytes = RULES_PATH.read_bytes()
    manifest = {
        "schema_version": "ayorai-golden-r2-manifest/1.0.0",
        "source": {
            "path": str(source_path.relative_to(ROOT)),
            "sha256": sha256_bytes(source_bytes),
            "case_count": len(cases),
        },
        "derived": {
            "path": out_name,
            "sha256": sha256_bytes(out_bytes),
            "case_count": len(derived),
        },
        "migration": {
            "method": MIGRATION_METHOD,
            "mapping_version": MAPPING_VERSION,
            "source_commit": source_commit,
            "rules_path": str(RULES_PATH.relative_to(ROOT)),
            "rules_version": "2.0.0",
            "rules_sha256": sha256_bytes(rules_bytes),
            "migrated_claims": migrated_count,
            "migrated_cases": migrated_cases,
            "non_migratable_cases": len(non_migratable_case_ids),
            "non_migratable_items": len(unresolved),
            "non_migratable": unresolved,
        },
        "preservation": {
            "source_files_modified": False,
            "corpus_modified": False,
            "thresholds_modified": False,
            "existing_manifests_modified": False,
        },
    }
    manifest_path = output_dir / f"{source_name}-r2.MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "evals" / "golden")
    parser.add_argument("--check-determinism", action="store_true")
    args = parser.parse_args()
    source_commit = os.environ.get("SOURCE_COMMIT")
    try:
        if not source_commit:
            source_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
            ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"cannot determine source commit: {exc}") from exc

    if args.check_determinism:
        with (
            tempfile.TemporaryDirectory(prefix="golden-r2-a-") as first_dir,
            tempfile.TemporaryDirectory(prefix="golden-r2-b-") as second_dir,
        ):
            first = [
                migrate(name, path, Path(first_dir), source_commit)
                for name, path in SOURCES
            ]
            second = [
                migrate(name, path, Path(second_dir), source_commit)
                for name, path in SOURCES
            ]
            if first != second:
                raise SystemExit("non-deterministic migration manifest")
            for name, _source_path in SOURCES:
                filenames = [f"{name}-r2.jsonl", f"{name}-r2.MANIFEST.json"]
                for filename in filenames:
                    first_bytes = (Path(first_dir) / filename).read_bytes()
                    second_bytes = (Path(second_dir) / filename).read_bytes()
                    if first_bytes != second_bytes:
                        raise SystemExit(f"non-deterministic output: {filename}")
            manifests = first
    else:
        manifests = [migrate(name, path, args.output_dir, source_commit) for name, path in SOURCES]

    for manifest in manifests:
        migration = manifest["migration"]
        print(
            f"{manifest['derived']['path']}: cases={manifest['derived']['case_count']} "
            f"migrated_cases={migration['migrated_cases']} "
            f"non_migratable_cases={migration['non_migratable_cases']} "
            f"migrated_claims={migration['migrated_claims']} "
            f"non_migratable_items={migration['non_migratable_items']} "
            f"sha256={manifest['derived']['sha256']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
