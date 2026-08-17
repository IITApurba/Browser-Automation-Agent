FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY apps ./apps
COPY packages ./packages

RUN pip install --no-cache-dir -e . \
    && playwright install --with-deps chromium

EXPOSE 8000

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0"]
