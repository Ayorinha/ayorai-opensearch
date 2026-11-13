"""Build a hash-locked requirements file from exact `name==version` pins via the PyPI JSON API.

Only files a CPython 3.12 / Linux x86_64 installer could select are kept (pure-Python
wheels, cp312/abi3 manylinux x86_64 wheels). PyPI never allows a filename to be
re-uploaded, so these digests identify the published artifacts for each version.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request

_KEEP = re.compile(
    r"(py2\.py3-none-any|py3-none-any|cp312-cp312-.*linux.*x86_64|abi3-.*linux.*x86_64)\.whl$"
)


def hashes_for(name: str, version: str) -> list[str]:
    url = f"https://pypi.org/pypi/{name}/{version}/json"
    with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310 - fixed PyPI host
        data = json.load(response)
    files = [
        f for f in data["urls"] if f["packagetype"] == "bdist_wheel" and _KEEP.search(f["filename"])
    ]
    if not files:
        raise SystemExit(f"no compatible wheel for {name}=={version}")
    return sorted({f["digests"]["sha256"] for f in files})


def main(path: str) -> None:
    out: list[str] = []
    for raw in open(path, encoding="utf-8"):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        name, version = line.split("==")
        digests = hashes_for(name, version)
        out.append(
            f"{name}=={version} \\\n" + " \\\n".join(f"    --hash=sha256:{d}" for d in digests)
        )
    sys.stdout.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main(sys.argv[1])
