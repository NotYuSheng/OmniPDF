FROM python:3.13-slim

WORKDIR /app

ENV PYTHONPATH=/app/pdf_processor_service:/app/shared_utils

RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt from pdf_processor_service folder in root context
COPY pdf_processor_service/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy utils folder from root context into /app/utils
COPY shared_utils ./shared_utils

# Copy pdf_processor_service folder from root context into /app/pdf_processor_service
COPY pdf_processor_service ./pdf_processor_service

EXPOSE 8000

CMD ["sh", "-c", "PYTHONPATH=/app/pdf_processor_service uvicorn pdf_processor_service.main:app --host 0.0.0.0 --port 8000"]