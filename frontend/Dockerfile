FROM python:3.13-slim

WORKDIR /app

ENV PYTHONPATH=/app/frontend:/app/shared_utils

RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt from frontend folder in root context
COPY frontend/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy utils folder from root context into /app/utils
COPY shared_utils ./shared_utils

# Copy frontend folder from root context into /app/frontend
COPY frontend ./frontend

EXPOSE 8000

CMD ["streamlit", "run", "frontend/main.py", "--server.port=8504", "--server.address=0.0.0.0"]
