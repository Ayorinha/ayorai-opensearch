install:
	python -m pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check .
	ruff format --check .

format:
	ruff format .

typecheck:
	mypy src/ayorai_attractor

typecheck-eval:
	mypy --strict evals/ptbr/rgc_eval.py evals/ptbr/rgc_agreement.py

security:
	pip-audit
	bandit -r src/ayorai_attractor

run:
	uvicorn ayorai_attractor.api.app:app --reload --lifespan on --no-access-log

reproduce:
	python scripts/reproduce.py

reproduce-quick:
	python scripts/reproduce.py --quick

.PHONY: install test lint typecheck typecheck-eval security run reproduce reproduce-quick
