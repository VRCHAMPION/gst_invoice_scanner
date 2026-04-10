# Use a slim Python image for a smaller footprint
FROM python:3.11-slim

# Install system dependencies
# tesseract-ocr: The OCR engine
# libmagic1: Used for file type detection (python-magic)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    libmagic1 \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements from the backend folder and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire backend directory into the container
COPY backend/ ./backend/

# Expose the port (FastAPI default is often 8000, Render uses PORT env var)
EXPOSE 8000

# Start command: Using Gunicorn with Uvicorn workers for production performance
# We use --bind 0.0.0.0:8000 as 8000 is our exposed port
CMD ["sh", "-c", "cd backend && gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT"]
