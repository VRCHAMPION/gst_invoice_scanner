# Use a slim Python image for a smaller footprint
FROM python:3.11-slim

# Install system dependencies
# tesseract-ocr: OCR engine
# curl: used by HEALTHCHECK
# libmagic1: file type detection
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    libmagic1 \
    build-essential \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire backend directory
COPY backend/ ./backend/

# Expose port
EXPOSE 8000

# Item 5: HEALTHCHECK — pings /health endpoint every 30s
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Production start: Gunicorn + Uvicorn workers
CMD ["sh", "-c", "cd backend && gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000}"]
