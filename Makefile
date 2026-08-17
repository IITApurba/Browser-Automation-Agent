.PHONY: dev test migrate up

dev:
	uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest

migrate:
	alembic upgrade head

up:
	docker compose up --build
