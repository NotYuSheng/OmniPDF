FROM python:3.13-slim

WORKDIR /app

ENV PYTHONPATH=/app/cleaner

RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt from cleaner folder in root context
COPY cleaner/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy utils folder from root context into /app/utils
COPY shared_utils ./cleaner/shared_utils

# Copy cleaner folder from root context into /app/cleaner
COPY cleaner ./cleaner

CMD ["python3", "cleaner/main.py"]