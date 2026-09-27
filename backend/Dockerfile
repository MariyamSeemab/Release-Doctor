FROM python:3.12-slim

WORKDIR /app

# System dependencies for GitPython, tree-sitter, psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Composes DATABASE_URL from DB_* secret env vars (AWS), runs migrations,
# then starts uvicorn. Works unchanged for local/Railway (DATABASE_URL set
# directly, DB_* absent).
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

CMD ["/app/entrypoint.sh"]
