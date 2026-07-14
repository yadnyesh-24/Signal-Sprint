FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
# NOTE: libgl1-mesa-glx was renamed to libgl1 in Debian 12+
# Since we use opencv-python-headless, OpenGL is not needed at all.
# Only libglib2.0-0 and libgomp1 (for torch/ultralytics) are required.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first (layer cache: only re-installs if requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend source code
COPY . .

# Expose default port (Railway overrides this with $PORT env var at runtime)
EXPOSE 8000

# Shell form so $PORT is expanded from the Railway environment at runtime
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}
