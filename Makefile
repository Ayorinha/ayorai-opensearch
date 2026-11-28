# Tools run through the project interpreter (python -m), so a tool installed
# outside the project environment (pipx, ~/.local/bin) cannot shadow it.

install:
	python -m pip install -e ".[dev]"

test:
	python -m pytest

lint:
	python -m ruff check .
	python -m ruff format --check .

format:
	python -m ruff format .

typecheck:
	python -m mypy src/ayorai_attractor

typecheck-eval:
	python -m mypy --strict --explicit-package-bases evals/ptbr/rgc_eval.py evals/ptbr/rgc_agreement.py

security:
	python -m pip_audit
	python -m bandit -r src/ayorai_attractor

run:
	python -m uvicorn ayorai_attractor.api.app:app --reload --lifespan on --no-access-log

reproduce:
	python scripts/reproduce.py

reproduce-quick:
	python scripts/reproduce.py --quick

.PHONY: install test lint format typecheck typecheck-eval security run reproduce reproduce-quick
