FROM python:3.11-slim

WORKDIR /app

# System deps needed to build psycopg2-binary's wheel on some platforms
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# .dockerignore keeps __pycache__/.venv/etc out of this
COPY . .

EXPOSE 8000

# --host 0.0.0.0 is required inside a container -- 127.0.0.1 would only
# accept connections from inside the container itself, not from other
# containers or the host's port mapping.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
