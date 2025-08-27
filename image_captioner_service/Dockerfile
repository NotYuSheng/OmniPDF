FROM python:3.13-slim

WORKDIR /app

ENV PYTHONPATH=/app/image_captioner_service:/app/shared_utils

RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

COPY image_captioner_service/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY shared_utils ./shared_utils

COPY image_captioner_service ./image_captioner_service

EXPOSE 8000

CMD ["uvicorn", "image_captioner_service.main:app", "--host", "0.0.0.0", "--port", "8000"]