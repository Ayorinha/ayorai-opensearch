"""Minimal mutation testing (operator swap) on a temporary copy; the project tree is untouched.
Usage: mutate.py <repo> <module relpath> <first_line> <last_line> <max_mutants> <out.json>"""

import ast
import copy
import json
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

repo, rel, lo, hi, cap, out = (
    Path(sys.argv[1]),
    sys.argv[2],
    int(sys.argv[3]),
    int(sys.argv[4]),
    int(sys.argv[5]),
    sys.argv[6],
)
SWAP = {
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
    ast.Lt: ast.LtE,
    ast.LtE: ast.Lt,
    ast.Gt: ast.GtE,
    ast.GtE: ast.Gt,
    ast.In: ast.NotIn,
    ast.NotIn: ast.In,
    ast.Is: ast.IsNot,
    ast.IsNot: ast.Is,
}
src = (repo / rel).read_text()
tree = ast.parse(src)
sites = []
for node in ast.walk(tree):
    ln = getattr(node, "lineno", 0)
    if not lo <= ln <= hi:
        continue
    if isinstance(node, ast.Compare):
        for i, op in enumerate(node.ops):
            if type(op) in SWAP:
                sites.append(("cmp", ln, id(node), i))
    elif isinstance(node, ast.BoolOp):
        sites.append(("bool", ln, id(node), 0))
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        sites.append(("not", ln, id(node), 0))
    elif (
        isinstance(node, ast.Constant)
        and type(node.value) is int
        and node.value in (0, 1, 4, 8, 12, 32, 63, 64, 255, 300, 409, 200)
    ):
        sites.append(("int", ln, id(node), 0))
    elif isinstance(node, ast.Constant) and type(node.value) is bool:
        sites.append(("bool_const", ln, id(node), 0))
random.Random(1).shuffle(sites)
sites = sites[:cap]


def mutate(kind, target, idx):
    t = copy.deepcopy(tree)
    pairs = dict(zip([id(n) for n in ast.walk(tree)], ast.walk(t), strict=True))
    n = pairs[target]
    if kind == "cmp":
        n.ops[idx] = SWAP[type(n.ops[idx])]()
    elif kind == "bool":
        n.op = ast.Or() if isinstance(n.op, ast.And) else ast.And()
    elif kind == "not":

        class R(ast.NodeTransformer):
            def visit_UnaryOp(self, node):
                self.generic_visit(node)
                return node.operand if node is n else node

        t = R().visit(t)
    elif kind == "int":
        n.value = n.value + 1
    elif kind == "bool_const":
        n.value = not n.value
    return ast.unparse(ast.fix_missing_locations(t))


results = []
with tempfile.TemporaryDirectory() as tmp:
    work = Path(tmp) / "src"
    shutil.copytree(repo / "src", work)
    target_file = work / Path(rel).relative_to("src")
    tests = [
        "tests/auditlog",
        "tests/test_verify_log_integrity.py",
        "tests/test_verify_log.py",
        "tests/test_verify_log_idempotency.py",
    ]
    for kind, ln, nid, idx in sites:
        try:
            code = mutate(kind, nid, idx)
        except Exception:
            continue
        target_file.write_text(code)
        r = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-x",
                "-q",
                "-o",
                "addopts=",
                "-p",
                "no:cacheprovider",
                *tests,
            ],
            cwd=repo,
            env={"PYTHONPATH": str(work), "PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": tmp},
            capture_output=True,
            text=True,
            timeout=300,
        )
        killed = r.returncode != 0
        results.append({"kind": kind, "line": ln, "killed": killed})
    target_file.write_text(src)
Path(out).write_text(json.dumps(results))
k = sum(r["killed"] for r in results)
print(
    rel,
    f"killed {k}/{len(results)}",
    "survivors:",
    [(r["kind"], r["line"]) for r in results if not r["killed"]],
)
