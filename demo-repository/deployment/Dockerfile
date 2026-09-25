# PLANTED RISK 7: Docker/deployment config not updated for new dependency/command
# The analytics-sdk package was added to requirements.txt but:
# 1. The Dockerfile still uses the old requirements (no rebuild triggered)
# 2. ANALYTICS_SERVICE_URL env var is NOT declared here
# 3. The new /track endpoint's system dependency is missing

FROM python:3.11-slim

WORKDIR /app

# Old requirements — does NOT include analytics-sdk
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Missing: ANALYTICS_SERVICE_URL environment variable declaration
# Missing: healthcheck instruction

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
