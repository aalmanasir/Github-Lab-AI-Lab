.PHONY: install dev run test lint format typecheck docker-build docker-run clean all

install:
	pip install -r requirements.txt

dev:
	pip install -r requirements-dev.txt

run:
	python main.py

test:
	pytest tests/ -v

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy clowdbot/ main.py

docker-build:
	docker build -t clowdbot-agent .

docker-run:
	docker-compose up -d

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.pyc' -delete 2>/dev/null || true
	rm -rf test_data .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage

all: lint typecheck test
