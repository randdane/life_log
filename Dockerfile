FROM python:3.14-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create migrations directory if it doesn't exist (handled by alembic init usually, but good to have permissions)
# ENTRYPOINT is handled in docker-compose, but we can set a default CMD
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
