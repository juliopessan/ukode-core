.PHONY: install dev test lint fmt api worker db-up db-down

install:
	python3 -m venv .venv
	.venv/bin/pip install -q --upgrade pip
	.venv/bin/pip install -q -e ".[dev]"

test:
	.venv/bin/pytest -q

lint:
	.venv/bin/ruff check .

fmt:
	.venv/bin/ruff check --fix .

api:
	.venv/bin/uvicorn ukode_core.api.app:app --reload

worker:
	.venv/bin/python -m ukode_core.worker.main

db-up:
	docker compose up -d postgres

db-down:
	docker compose down
