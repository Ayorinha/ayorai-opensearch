install:
	python -m pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check .

typecheck:
	mypy src/ayorai_attractor

security:
	pip-audit
	bandit -r src/ayorai_attractor

run:
	uvicorn ayorai_attractor.api.app:app --reload
