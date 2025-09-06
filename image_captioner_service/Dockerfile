FROM python:3.13-slim

WORKDIR /app

ENV PYTHONPATH=/app/image_captioner_service:/app/shared_utils

RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

COPY image_captioner_service/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY shared_utils ./shared_utils

COPY image_captioner_service ./image_captioner_service

# Remove unnecessary system packages
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get remove --purge -y linux-libc-dev && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Expose the FastAPI port
# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /bin/bash appuser
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "image_captioner_service.main:app", "--host", "0.0.0.0", "--port", "8000"]