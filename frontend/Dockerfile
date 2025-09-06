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

# Remove unnecessary system packages
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get remove --purge -y linux-libc-dev && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user for security and set permissions
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /bin/bash appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8501

ENV STREAMLIT_CLIENT_TOOLBAR_MODE=minimal

CMD ["streamlit", "run", "frontend/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
