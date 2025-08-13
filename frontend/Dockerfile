FROM python:3.13-slim

WORKDIR /app

ENV PYTHONPATH=/app/frontend:/app/shared_utils

RUN apt-get update 

# Copy requirements.txt from frontend folder in root context
COPY frontend/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy utils folder from root context into /app/utils
COPY shared_utils ./shared_utils

# Copy frontend folder from root context into /app/frontend
COPY frontend ./frontend

EXPOSE 8504

ENV STREAMLIT_CLIENT_TOOLBAR_MODE=minimal

CMD ["streamlit", "run", "frontend/main.py", "--server.port=8504", "--server.address=0.0.0.0"]
