install:
	python -m pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check .

typecheck:
	mypy attractor agents providers evidence failure_engine

security:
	pip-audit
	bandit -r attractor agents providers evidence failure_engine

run:
	uvicorn attractor.api.app:app --reload
