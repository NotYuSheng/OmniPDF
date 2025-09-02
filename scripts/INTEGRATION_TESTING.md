# OmniPDF Integration Testing Guide

This guide explains how to create and run integration tests for OmniPDF services before and after Trivy security hardening.

## Overview

The integration tests validate that services can:
- Start up successfully with all dependencies
- Load critical packages (ML libraries, databases, etc.)  
- Connect to real external services (LLM servers, databases)
- Respond to health check endpoints

## Files

- `test_all_services.py` - Core Python test runner for all 7 services
- `test_service_before_trivy.sh` - Bash wrapper for individual service testing
- `test_chat_service.py` - Legacy single-service test (kept for reference)
- `test_before_trivy.sh` - Legacy single-service wrapper (kept for reference)

## Setup Instructions

### 1. Create Integration Test Environment

```bash
# Navigate to project root
cd /home/ubuntu/Desktop/OmniPDF

# Create virtual environment for integration tests
python3 -m venv .venv_integration
source .venv_integration/bin/activate

# Install base chat service dependencies
pip install -r chat_service/requirements.txt

# Install additional service dependencies
pip install docling==2.36.1 PyMuPDF==1.26.1 redis==6.3.0 boto3==1.38.34 python-multipart==0.0.20 httpx==0.28.1 pypdf==5.6.0
```

### 2. Verify Prerequisites

Ensure your LLM inference server is accessible:
- **Server**: `http://webworkdgx/vllm_qwen3coder/v1`
- **Model**: `Qwen3-Coder-30B-A3B-Instruct` 
- **API Key**: `lm-studio`

Test connectivity:
```bash
curl -X POST http://webworkdgx/vllm_qwen3coder/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer lm-studio" \
  -d '{"model": "Qwen3-Coder-30B-A3B-Instruct", "messages": [{"role": "user", "content": "Hello"}], "max_tokens": 5}'
```

### 3. Make Scripts Executable

```bash
chmod +x scripts/test_service_before_trivy.sh
chmod +x scripts/test_before_trivy.sh
```

## How to Run Integration Tests

### Test Individual Services (Recommended)

```bash
# Activate the integration test environment
source .venv_integration/bin/activate

# Test specific service
./scripts/test_service_before_trivy.sh <service_name>

# Examples
./scripts/test_service_before_trivy.sh chat_service
./scripts/test_service_before_trivy.sh pdf_extraction_service
./scripts/test_service_before_trivy.sh docling_translation_service
```

**Available services:**
- `chat_service` - RAG chat with LLM and ChromaDB
- `pdf_extraction_service` - PDF processing with docling  
- `docling_translation_service` - Translation with LLM
- `pdf_renderer_service` - PDF rendering with PyMuPDF
- `embedder_service` - Text embedding with ChromaDB
- `pdf_processor_service` - Central PDF coordinator
- `image_captioner_service` - Image captioning with VLM

### Alternative: Direct Python Script

```bash
# Using Python script directly
python scripts/test_all_services.py --service <service_name>

# List available services
python scripts/test_all_services.py --list
```

## Understanding Test Results

Each service runs 4 tests:

1. **🚀 Service Startup** - FastAPI app can initialize
2. **📦 Dependencies** - Critical packages load correctly
3. **🤖 LLM Connectivity** - External LLM server responds (if applicable)
4. **🌐 Health Endpoint** - `/health` endpoint accessible

### Success Output Example:
```
🔒 TESTING CHAT_SERVICE
============================================================

🚀 Service Startup...
   ✅ Service starts successfully

📦 Dependencies...
   ✅ All dependencies (chromadb, sentence_transformers, torch, openai) load correctly

🤖 LLM Connectivity...
   ✅ LLM responded: "OK"

🌐 Health Endpoint...
   ✅ Health endpoint accessible (Status: 200)

📊 chat_service: 4/4 tests passed

======================================================================
📊 FINAL RESULTS:
   chat_service: ✅ PASS

🎯 Overall: 1/1 services passed
🎉 ALL SERVICES READY FOR TRIVY HARDENING!
```

### Failure Output Example:
```
🚀 Service Startup...
   ❌ Service startup failed: No module named 'docling'

📦 Dependencies...
   ❌ Failed to import docling: No module named 'docling'

📊 pdf_extraction_service: 2/4 tests passed
❌ FAIL
🚨 SOME SERVICES FAILED - Fix before Trivy hardening!
```

## Trivy Hardening Workflow

### Before Trivy Hardening

Test all services you plan to harden to establish a baseline:

```bash
# Test each service individually
./scripts/test_service_before_trivy.sh chat_service
./scripts/test_service_before_trivy.sh pdf_extraction_service
./scripts/test_service_before_trivy.sh docling_translation_service
./scripts/test_service_before_trivy.sh pdf_renderer_service
./scripts/test_service_before_trivy.sh embedder_service
./scripts/test_service_before_trivy.sh pdf_processor_service
./scripts/test_service_before_trivy.sh image_captioner_service
```

**All services must show `✅ PASS` before proceeding with Trivy hardening.**

### After Trivy Hardening

Re-run the exact same tests to verify functionality is preserved:

```bash
# Test the same services after hardening
./scripts/test_service_before_trivy.sh <service_name>
```

**If tests fail after hardening, the Trivy changes broke dependencies and need to be reviewed.**

## How the Tests Work

### Environment Configuration

Tests automatically set these environment variables for services:

**LLM Services:**
```bash
OPENAI_BASE_URL=http://webworkdgx/vllm_qwen3coder/v1
OPENAI_API_KEY=lm-studio  
OPENAI_MODEL=Qwen3-Coder-30B-A3B-Instruct
MODEL_TOP_K=5
MODEL_TEMPERATURE=0.1
MODEL_MAX_TOKENS=2000
```

**Storage Services:**
```bash
MINIO_ENDPOINT=http://minio:9000
MINIO_BUCKET=omnifiles
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
S3_ENDPOINT=http://minio:9000
BUCKET_NAME=omnifiles
```

**Database Services:**
```bash
REDIS_URL=redis://redis:6379/0?decode_responses=True&protocol=3
REDIS_HOST=redis
REDIS_PORT=6379
CHROMA_HOST=chromadb
CHROMA_PORT=8000
```

### Service-Specific Tests

Each service is tested based on its capabilities:

**Services with LLM dependency:**
- chat_service
- docling_translation_service  
- image_captioner_service

**Services with heavy ML dependencies:**
- chat_service (ChromaDB, transformers, PyTorch)
- pdf_extraction_service (docling, computer vision)
- embedder_service (ChromaDB, sentence-transformers)
- image_captioner_service (transformers, PyTorch)

**Services with lighter dependencies:**
- pdf_renderer_service (PyMuPDF, file processing)
- pdf_processor_service (Redis, coordination)

## Troubleshooting

### Common Issues

**Import Errors:**
```bash
❌ Service startup failed: No module named 'docling'
```
**Solution:** Install missing dependencies in the integration virtual environment.

**LLM Connectivity Failures:**
```bash
❌ LLM connectivity failed: Connection refused
```
**Solution:** 
- Verify LLM server is running: `curl http://webworkdgx/vllm_qwen3coder/v1/models`
- Check network connectivity to the server
- Ensure model name matches exactly

**Environment Variable Issues:**
```bash
❌ Service startup failed: 'NoneType' object has no attribute 'startswith'
```
**Solution:** 
- Check the service's `example.env` file for required variables
- Add missing variables to the test script configuration
- Verify environment variable names match service expectations

**Python Path Issues:**
```bash
❌ Service startup failed: cannot import name 'routers'
```
**Solution:**
- The test script handles this by changing working directory
- If issues persist, check that service directory structure matches expectations

### Service-Specific Notes

**chat_service:**
- Most comprehensive test (all dependency types)
- Requires heavy ML stack installation
- Good baseline for overall system health

**pdf_extraction_service:**  
- Requires docling and computer vision libraries
- May need additional system libraries for PDF processing
- Large dependency footprint

**docling_translation_service:**
- Requires LLM connectivity but lighter ML dependencies
- Good test for translation pipeline functionality

**pdf_renderer_service:**
- Requires PyMuPDF for PDF manipulation
- File processing focused, lighter than ML services

**embedder_service:**
- Requires ChromaDB and sentence-transformers
- Tests vector database connectivity

**pdf_processor_service:**
- Central coordinator service
- Primarily tests Redis connectivity and coordination logic

**image_captioner_service:**
- Requires LLM connectivity and vision models
- Tests multimodal AI capabilities

## Creating Tests for New Services

To add integration tests for a new service:

1. **Add service configuration** in `test_all_services.py`:
```python
'new_service_name': {
    'port': 8007,
    'env_vars': {
        # Service-specific environment variables
    },
    'heavy_deps': ['dependency1', 'dependency2'],
    'has_llm': True  # or False
},
```

2. **Install service dependencies** in the integration environment:
```bash
source .venv_integration/bin/activate
pip install -r new_service/requirements.txt
```

3. **Test the service**:
```bash
./scripts/test_service_before_trivy.sh new_service_name
```

## Legacy Files

These files are kept for reference but use the new unified scripts instead:

- `test_chat_service.py` - Original single-service test for chat_service only
- `test_before_trivy.sh` - Original wrapper for chat_service only

The new unified approach supports all services and provides better isolation and error handling.