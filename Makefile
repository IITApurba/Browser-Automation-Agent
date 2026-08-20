.PHONY: dev test migrate up eval

dev:
	uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest

migrate:
	alembic upgrade head

up:
	docker compose up --build

eval:
	python -m packages.evals.run
