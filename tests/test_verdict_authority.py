from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "ayorai_attractor"
LEGACY_PATH = "evals/baselines/legacy-v0"
NETWORK_MODEL_IMPORTS = {
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
    "google",
    "vertexai",
}
MODEL_IMPORTS = {"agents", "mcp"}


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
        verdict_aliases = {"Verdict"}
        module_aliases: set[str] = set()
        imported_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    bound = alias.asname or alias.name.split(".")[0]
                    module_aliases.add(bound)
                    imported_modules.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    bound = alias.asname or alias.name
                    if alias.name == "Verdict":
                        verdict_aliases.add(bound)
                    else:
                        module_aliases.add(bound)
                    if module:
                        imported_modules.add(module)

        parents: dict[ast.AST, ast.AST] = {}
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                parents[child] = parent

        def inside_comparison(node: ast.AST, parent_map: dict[ast.AST, ast.AST] = parents) -> bool:
            parent = parent_map.get(node)
            while parent is not None:
                if isinstance(parent, ast.Compare):
                    return True
                parent = parent_map.get(parent)
            return False

        def dotted_name(node: ast.AST) -> str | None:
            if isinstance(node, ast.Name):
                return node.id
            if isinstance(node, ast.Attribute):
                prefix = dotted_name(node.value)
                return f"{prefix}.{node.attr}" if prefix else None
            return None

        def is_verdict_type(
            node: ast.AST,
            aliases: set[str] = verdict_aliases,
            modules: set[str] = module_aliases,
            imports: set[str] = imported_modules,
        ) -> bool:
            if isinstance(node, ast.Name):
                return node.id in aliases
            if isinstance(node, ast.Attribute) and node.attr == "Verdict":
                dotted = dotted_name(node)
                prefix = dotted.rsplit(".Verdict", 1)[0] if dotted else ""
                return prefix in modules or prefix in imports
            return False

        if allowed:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if is_verdict_type(node.func):
                    violations.append(f"{relative}:{node.lineno}:constructor")
                elif (
                    isinstance(node.func, ast.Name)
                    and node.func.id == "getattr"
                    and node.args
                    and is_verdict_type(node.args[0])
                ):
                    violations.append(f"{relative}:{node.lineno}:getattr")
            elif isinstance(node, ast.Attribute):
                if is_verdict_type(node.value) and not inside_comparison(node):
                    violations.append(f"{relative}:{node.lineno}:member")
            elif isinstance(node, ast.Subscript):
                if is_verdict_type(node.value) and not inside_comparison(node):
                    violations.append(f"{relative}:{node.lineno}:subscript")
    return sorted(set(violations))


def _judge_import_violations(src_root: Path) -> list[str]:
    violations: list[str] = []
    dynamic_names = {"__import__", "exec", "eval"}
    for path in _python_files(src_root):
        relative = _relative(path, src_root)
        if not (relative.startswith("verification/judge") and path.suffix == ".py"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        imported: list[tuple[str, int]] = []
        dynamic_aliases = set(dynamic_names)
        importlib_aliases = {"importlib"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.append((alias.name, node.lineno))
                    if alias.name == "importlib":
                        importlib_aliases.add(alias.asname or alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imported.append((module, node.lineno))
                for alias in node.names:
                    imported_name = f"{module}.{alias.name}" if module else alias.name
                    imported.append((imported_name, node.lineno))
                    if module == "builtins" and alias.name in dynamic_names:
                        dynamic_aliases.add(alias.asname or alias.name)
                    if module == "importlib" and alias.name == "import_module":
                        dynamic_aliases.add(alias.asname or alias.name)
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id in dynamic_aliases:
                    violations.append(f"{relative}:{node.lineno}:{func.id}")
                elif (
                    isinstance(func, ast.Attribute)
                    and func.attr == "import_module"
                    and isinstance(func.value, ast.Name)
                    and func.value.id in importlib_aliases
                ):
                    violations.append(f"{relative}:{node.lineno}:importlib.import_module")
        for module, lineno in imported:
            roots = set(module.split("."))
            blocked = (
                roots & NETWORK_MODEL_IMPORTS
                or roots & MODEL_IMPORTS
                or {"providers", "orchestrator", "importlib"} & roots
                or module in dynamic_names
                or module in {f"builtins.{name}" for name in dynamic_names}
            )
            if blocked:
                violations.append(f"{relative}:{lineno}:{module}")
    return sorted(set(violations))


def _legacy_reader_violations(src_root: Path) -> list[str]:
    violations: list[str] = []
    read_methods = {"open", "read_text", "read_bytes"}
    for path in _python_files(src_root):
        relative = _relative(path, src_root)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        mentions_legacy = any(
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and LEGACY_PATH in node.value
            for node in ast.walk(tree)
        )
        if not mentions_legacy:
            continue
        reads = any(
            isinstance(node, ast.Call)
            and (
                (isinstance(node.func, ast.Name) and node.func.id in read_methods)
                or (isinstance(node.func, ast.Attribute) and node.func.attr in read_methods)
            )
            for node in ast.walk(tree)
        )
        if reads and relative != "evaluation/golden.py":
            violations.append(relative)
    return violations


def _symbol_violations(src_root: Path, symbol: str, allowlist: set[str] | None = None) -> list[str]:
    allowlist = allowlist or set()
    return [
        _relative(path, src_root)
        for path in _python_files(src_root)
        if _relative(path, src_root) not in allowlist and symbol in path.read_text(encoding="utf-8")
    ]


def _invalid_judge_catch_violations(src_root: Path) -> list[str]:
    violations: list[str] = []
    for path in _python_files(src_root):
        relative = _relative(path, src_root)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            caught = node.type
            catches_invalid = (
                isinstance(caught, ast.Name) and caught.id == "InvalidJudgeInput"
            ) or (isinstance(caught, ast.Attribute) and caught.attr == "InvalidJudgeInput")
            if not catches_invalid:
                continue
            enclosing = [
                parent
                for parent in ast.walk(tree)
                if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef))
                and any(child is node for child in ast.walk(parent))
            ]
            in_verify_route = relative == "api/app.py" and any(
                fn.name == "verify" for fn in enclosing
            )
            if not in_verify_route:
                violations.append(f"{relative}:{node.lineno}")
    return violations


def _write_source(src_root: Path, relative: str, content: str) -> None:
    path = src_root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_only_allowlisted_modules_construct_verdict() -> None:
    assert _verdict_constructor_violations(SRC) == []


def test_verdict_guard_detects_synthetic_violation(tmp_path: Path) -> None:
    root = tmp_path / "src" / "ayorai_attractor"
    _write_source(root, "api/unauthorized.py", 'result = Verdict("verified")\n')
    assert _verdict_constructor_violations(root) == ["api/unauthorized.py:1:constructor"]


def test_verdict_guard_detects_member_access_and_import_alias(tmp_path: Path) -> None:
    root = tmp_path / "src" / "ayorai_attractor"
    _write_source(root, "api/member.py", "return_value = Verdict.SUPPORTED\n")
    _write_source(
        root,
        "api/alias.py",
        "from package import Verdict as V\nresult = V('verified')\n",
    )
    assert _verdict_constructor_violations(root) == [
        "api/alias.py:2:constructor",
        "api/member.py:1:member",
    ]


def test_verdict_guard_detects_module_alias_and_allows_comparison(tmp_path: Path) -> None:
    root = tmp_path / "src" / "ayorai_attractor"
    _write_source(
        root,
        "api/module_alias.py",
        "import package.models as models\nresult = models.Verdict('verified')\n",
    )
    _write_source(
        root,
        "api/module_comparison.py",
        "import package.models as models\nallowed = verdict is models.Verdict.UNVERIFIED\n",
    )
    assert _verdict_constructor_violations(root) == ["api/module_alias.py:2:constructor"]


def test_verdict_guard_allows_member_comparison(tmp_path: Path) -> None:
    root = tmp_path / "src" / "ayorai_attractor"
    _write_source(root, "api/compare.py", "allowed = verdict is Verdict.UNVERIFIED\n")
    assert _verdict_constructor_violations(root) == []


def test_verdict_guard_detects_subscript_and_imported_alias(tmp_path: Path) -> None:
    root = tmp_path / "src" / "ayorai_attractor"
    _write_source(
        root,
        "api/subscript.py",
        "from package import Verdict as V\nallowed = V['SUPPORTED']\n",
    )
    assert _verdict_constructor_violations(root) == ["api/subscript.py:2:subscript"]


def test_judge_has_no_network_provider_model_or_orchestrator_imports() -> None:
    assert _judge_import_violations(SRC) == []


def test_judge_import_guard_detects_synthetic_violation(tmp_path: Path) -> None:
    root = tmp_path / "src" / "ayorai_attractor"
    _write_source(root, "verification/judge_bad.py", "import requests\n")
    assert _judge_import_violations(root) == ["verification/judge_bad.py:1:requests"]


def test_judge_import_guard_detects_dynamic_import_and_eval(tmp_path: Path) -> None:
    root = tmp_path / "src" / "ayorai_attractor"
    _write_source(
        root,
        "verification/judge_dyn.py",
        "import importlib\nimportlib.import_module('requests')\n"
        "__import__('requests')\neval('1 + 1')\n",
    )
    violations = _judge_import_violations(root)
    assert any(":importlib" in item for item in violations)
    assert any(":importlib.import_module" in item for item in violations)
    assert any(":__import__" in item for item in violations)
    assert any(":eval" in item for item in violations)


def test_verdict_guard_detects_qualified_module_alias_and_comparison_is_allowed(
    tmp_path: Path,
) -> None:
    root = tmp_path / "src" / "ayorai_attractor"
    _write_source(
        root,
        "api/qualified.py",
        "import package.models as models\nresult = models.Verdict.SUPPORTED\n",
    )
    _write_source(
        root,
        "api/compare_alias.py",
        "import package.models as models\nallowed = verdict is models.Verdict.UNVERIFIED\n",
    )
    assert _verdict_constructor_violations(root) == ["api/qualified.py:2:member"]


def test_verdict_guard_detects_getattr_alias(tmp_path: Path) -> None:
    root = tmp_path / "src" / "ayorai_attractor"
    _write_source(
        root,
        "api/getattr.py",
        "from package import Verdict as V\nmember = getattr(V, 'SUPPORTED')\n",
    )
    assert _verdict_constructor_violations(root) == ["api/getattr.py:2:getattr"]


def test_verdict_guard_detects_nested_qualified_verdict(tmp_path: Path) -> None:
    root = tmp_path / "src" / "ayorai_attractor"
    _write_source(
        root,
        "api/nested.py",
        "import x.models as m\nmember = m.Verdict.SUPPORTED\n",
    )
    assert _verdict_constructor_violations(root) == ["api/nested.py:2:member"]


def test_judge_import_guard_detects_aliased_dynamic_imports(tmp_path: Path) -> None:
    root = tmp_path / "src" / "ayorai_attractor"
    _write_source(
        root,
        "verification/judge_dyn.py",
        "import importlib as il\n"
        "il.import_module('requests')\n"
        "from builtins import eval as evaluate\n"
        "evaluate('1 + 1')\n",
    )
    violations = _judge_import_violations(root)
    assert any(":importlib" in item for item in violations)
    assert any(":importlib.import_module" in item for item in violations)
    assert any(":evaluate" in item for item in violations)


def test_only_golden_evaluation_reads_legacy_baseline() -> None:
    assert _legacy_reader_violations(SRC) == []


def test_legacy_reader_guard_detects_synthetic_violation(tmp_path: Path) -> None:
    root = tmp_path / "src" / "ayorai_attractor"
    source = """from pathlib import Path
path = Path("evals/baselines/legacy-v0/predictions.jsonl")
data = path.read_text()
"""
    _write_source(root, "api/unauthorized.py", source)
    assert _legacy_reader_violations(root) == ["api/unauthorized.py"]


def test_verification_status_does_not_reappear_in_source() -> None:
    assert _symbol_violations(SRC, "VerificationStatus") == []


def test_verification_status_guard_detects_synthetic_violation(tmp_path: Path) -> None:
    root = tmp_path / "src" / "ayorai_attractor"
    _write_source(root, "verification/legacy.py", "class VerificationStatus: ...\n")
    assert _symbol_violations(root, "VerificationStatus") == ["verification/legacy.py"]


def test_response_status_is_confined_to_compatibility_modules() -> None:
    assert (
        _symbol_violations(
            SRC,
            "ResponseStatus",
            {"verification/response.py", "verification/__init__.py"},
        )
        == []
    )


def test_response_status_guard_detects_synthetic_violation(tmp_path: Path) -> None:
    root = tmp_path / "src" / "ayorai_attractor"
    _write_source(root, "api/legacy.py", "from package import ResponseStatus\n")
    assert _symbol_violations(
        root,
        "ResponseStatus",
        {"verification/response.py", "verification/__init__.py"},
    ) == ["api/legacy.py"]


def test_invalid_judge_input_is_caught_only_in_verify_route() -> None:
    assert _invalid_judge_catch_violations(SRC) == []


def test_invalid_judge_catch_guard_detects_synthetic_violation(tmp_path: Path) -> None:
    root = tmp_path / "src" / "ayorai_attractor"
    source = """def other():
    try:
        pass
    except InvalidJudgeInput:
        pass
"""
    _write_source(root, "api/other.py", source)
    assert _invalid_judge_catch_violations(root) == ["api/other.py:4"]
