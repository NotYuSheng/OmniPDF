FROM python:3.13-slim

WORKDIR /app

ENV PYTHONPATH=/app/pdf_processor_service:/app/shared_utils

RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt from chat_service folder in root context
COPY chat_service/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy utils folder from root context into /app/utils
COPY shared_utils ./shared_utils

# Copy chat_service folder from root context into /app/chat_service
COPY chat_service ./chat_service

EXPOSE 8000

CMD ["sh", "-c", "PYTHONPATH=/app/chat_service uvicorn chat_service.main:app --host 0.0.0.0 --port 8000"]