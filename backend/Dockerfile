FROM python:3.11-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for ultra-fast dependency resolution
RUN pip install uv --no-cache-dir

# Copy backend dependencies
COPY pyproject.toml .

# Install dependencies into system Python
RUN uv pip install --system -r pyproject.toml 2>/dev/null || uv pip install --system .

# Copy backend code
COPY . /app/backend

# Create runtime directories
RUN mkdir -p /app/uploads /app/chroma_db

EXPOSE 8000

ENV PYTHONPATH=/app
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
