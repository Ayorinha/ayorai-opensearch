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

security:
	pip-audit
	bandit -r src/ayorai_attractor

run:
	uvicorn ayorai_attractor.api.app:app --reload --lifespan on

reproduce:
	python scripts/reproduce.py

reproduce-quick:
	python scripts/reproduce.py --quick

.PHONY: install test lint typecheck security run reproduce reproduce-quick
