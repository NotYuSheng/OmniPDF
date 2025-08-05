FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app

# Set PYTHONPATH so FastAPI can locate your modules
ENV PYTHONPATH=/app/docling_translation_service:/app/shared_utils

# Install build tools
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY docling_translation_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared_utils ./shared_utils

COPY docling_translation_service ./docling_translation_service

# Expose the FastAPI port
EXPOSE 8000

# Start the FastAPI server
CMD ["sh", "-c", "PYTHONPATH=/app/docling_translation_service uvicorn docling_translation_service.main:app --host 0.0.0.0 --port 8000"]
