FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies for OpenCV, torch (libgomp1), and YOLO
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first (Docker layer cache: only re-installs if requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend source code
COPY . .

# Expose default port (Railway overrides this via $PORT env var at runtime)
EXPOSE 8000

# Shell form CMD so that $PORT is expanded from the Railway environment variable
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}
