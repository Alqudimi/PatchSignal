.PHONY: install test lint check report

install:
	python -m pip install -e '.[dev]'

test:
	python -m pytest --cov=patchsignal --cov-report=term-missing --cov-fail-under=85

lint:
	ruff check .

check: lint test
	python -m compileall -q src

report:
	patchsignal --format markdown --output patchsignal-report.md
