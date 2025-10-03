FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

WORKDIR /app

ENV PYTHONPATH=/app/pdf_extraction_service:/app/shared_utils
ENV DEBIAN_FRONTEND=noninteractive

# Install Python 3.13 and build dependencies
RUN apt-get update && apt-get install -y \
    software-properties-common \
    build-essential \
    wget \
    curl \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y python3.13 python3.13-dev python3.13-venv \
    && curl -sS https://bootstrap.pypa.io/get-pip.py | python3.13 \
    && rm -rf /var/lib/apt/lists/*

# Create symbolic links
RUN ln -sf /usr/bin/python3.13 /usr/bin/python && \
    ln -sf /usr/bin/python3.13 /usr/bin/python3

COPY pdf_extraction_service/requirements.txt .

# Install PyTorch with CUDA support first
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cu124

# Install remaining requirements
RUN pip install --no-cache-dir -r requirements.txt

COPY shared_utils ./shared_utils

COPY pdf_extraction_service ./pdf_extraction_service

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

# Expose the FastAPI port
EXPOSE 8000

# Start the FastAPI server
CMD ["sh", "-c", "PYTHONPATH=/app/pdf_extraction_service uvicorn pdf_extraction_service.main:app --host 0.0.0.0 --port 8000"]
