# Multi-stage build for meal planner backend
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies for Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8000

# Expose FastAPI port
EXPOSE 8000

# Run the application
CMD ["python", "run_server.py"]
