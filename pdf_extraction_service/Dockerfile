FROM python:3.13-slim

WORKDIR /app

ENV PYTHONPATH=/app/pdf_extraction_service:/app/shared_utils

RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

COPY pdf_extraction_service/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY shared_utils ./shared_utils

COPY pdf_extraction_service ./pdf_extraction_service

EXPOSE 8000

# Start the FastAPI server
CMD ["sh", "-c", "PYTHONPATH=/app/pdf_extraction_service uvicorn pdf_extraction_service.main:app --host 0.0.0.0 --port 8000"]
