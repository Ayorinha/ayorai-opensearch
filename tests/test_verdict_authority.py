from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "ayorai_attractor"
LEGACY_PATH = "evals/baselines/legacy-v0"

_NETWORK_AND_MODEL_IMPORTS = {
    "aiohttp",
    "anthropic",
    "boto3",
    "cohere",
    "ftplib",
    "http",
    "httpx",
    "huggingface_hub",
    "litellm",
    "ollama",
    "openai",
    "requests",
    "sentence_transformers",
    "socket",
    "telnetlib",
    "transformers",
    "urllib",
    "urllib3",
    "vllm",
    "websocket",
    "websockets",
}


def _python_files(src_root: Path) -> list[Path]:
    return sorted(src_root.rglob("*.py")) if src_root.exists() else []


def _relative(path: Path, src_root: Path) -> str:
    return path.relative_to(src_root).as_posix()


def _verdict_constructor_violations(src_root: Path) -> list[str]:
    violations: list[str] = []
    for path in _python_files(src_root):
        relative = _relative(path, src_root)
        allowed = relative == "verification/models.py" or (
            relative.startswith("verification/judge") and path.suffix == ".py"
        )
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            called_name = (
                func.id if isinstance(func, ast.Name)
                else func.attr if isinstance(func, ast.Attribute)
                else ""
            )
            if called_name == "Verdict" and not allowed:
                violations.append(f"{relative}:{node.lineno}")
    return violations


def _judge_import_violations(src_root: Path) -> list[str]:
    violations: list[str] = []
    for path in _python_files(src_root):
        relative = _relative(path, src_root)
        if not (relative.startswith("verification/judge") and path.suffix == ".py"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        for node in ast.walk(tree):
            imported: list[str] = []
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imported.append(module)
                imported.extend(
                    f"{module}.{alias.name}" if module else alias.name
                    for alias in node.names
                )
            for module in imported:
                roots = set(module.split("."))
                if roots & _NETWORK_AND_MODEL_IMPORTS or {
                    "providers", "orchestrator"
                } & roots:
                    violations.append(f"{relative}:{node.lineno}:{module}")
    return violations


def _legacy_baseline_reader_violations(src_root: Path) -> list[str]:
    violations: list[str] = []
    read_methods = {"open", "read_text", "read_bytes"}
    for path in _python_files(src_root):
        relative = _relative(path, src_root)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        has_legacy_path = any(
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and LEGACY_PATH in node.value
            for node in ast.walk(tree)
        )
        if not has_legacy_path:
            continue
        reads_file = any(
            isinstance(node, ast.Call)
            and (
                (isinstance(node.func, ast.Name) and node.func.id in read_methods)
                or (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr in read_methods
                )
            )
            for node in ast.walk(tree)
        )
        if reads_file and relative != "evaluation/golden.py":
            violations.append(relative)
    return violations


def _symbol_violations(
    src_root: Path, symbol: str, allowed_paths: set[str] | None = None
) -> list[str]:
    allowed_paths = allowed_paths or set()
    return [
        _relative(path, src_root)
        for path in _python_files(src_root)
        if _relative(path, src_root) not in allowed_paths
        and symbol in path.read_text(encoding="utf-8")
    ]


def _write_source(src_root: Path, relative: str, content: str) -> None:
    path = src_root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_only_allowlisted_modules_construct_verdict() -> None:
    assert _verdict_constructor_violations(SRC) == []


def test_verdict_constructor_guard_detects_synthetic_violation(tmp_path: Path) -> None:
    src_root = tmp_path / "src" / "ayorai_attractor"
    _write_source(
        src_root,
        "api/unauthorized.py",
        'from ayorai_attractor.verification.models import Verdict\nresult = Verdict("verified")\n',
    )
    assert _verdict_constructor_violations(src_root) == ["api/unauthorized.py:2"]


def test_judge_has_no_network_provider_model_or_orchestrator_imports() -> None:
    assert _judge_import_violations(SRC) == []


def test_judge_import_guard_detects_synthetic_violation(tmp_path: Path) -> None:
    src_root = tmp_path / "src" / "ayorai_attractor"
    _write_source(src_root, "verification/judge_bad.py", "import requests\n")
    assert _judge_import_violations(src_root) == [
        "verification/judge_bad.py:1:requests"
    ]


def test_only_golden_evaluation_reads_legacy_baseline() -> None:
    assert _legacy_baseline_reader_violations(SRC) == []


def test_legacy_baseline_guard_detects_synthetic_reader(tmp_path: Path) -> None:
    src_root = tmp_path / "src" / "ayorai_attractor"
    _write_source(
        src_root,
        "api/unauthorized.py",
        'from pathlib import Path\npath = Path("evals/baselines/legacy-v0/predictions.jsonl")\ndata = path.read_text()\n',
    )
    assert _legacy_baseline_reader_violations(src_root) == ["api/unauthorized.py"]


def test_verification_status_does_not_reappear_in_source() -> None:
    assert _symbol_violations(SRC, "VerificationStatus") == []


def test_verification_status_guard_detects_synthetic_violation(tmp_path: Path) -> None:
    src_root = tmp_path / "src" / "ayorai_attractor"
    _write_source(src_root, "verification/legacy.py", "class VerificationStatus: ...\n")
    assert _symbol_violations(src_root, "VerificationStatus") == [
        "verification/legacy.py"
    ]


def test_response_status_is_confined_to_compatibility_modules() -> None:
    assert _symbol_violations(
        SRC,
        "ResponseStatus",
        {"verification/response.py", "verification/__init__.py"},
    ) == []


def test_response_status_guard_detects_synthetic_violation(tmp_path: Path) -> None:
    src_root = tmp_path / "src" / "ayorai_attractor"
    _write_source(
        src_root,
        "api/legacy.py",
        "from ayorai_attractor.verification.response import ResponseStatus\n",
    )
    assert _symbol_violations(
        src_root,
        "ResponseStatus",
        {"verification/response.py", "verification/__init__.py"},
    ) == ["api/legacy.py"]
