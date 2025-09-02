# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OmniPDF is a microservices-based PDF analyzer with translation, summarization, captioning, and chat capabilities through RAG. The system uses Docker containers orchestrated via docker-compose.

## Development Commands

### Running the System
```bash
# Start all services
docker-compose up --build

# Start with GPU support (for LLM services)
docker-compose -f docker-compose.gpu.yml up --build

# Stop all services
docker-compose down

# View service logs
docker-compose logs <service_name>
```

### Testing
```bash
# End-to-end tests with Cypress
cd cypress
npx cypress open
```

## Architecture Overview

### Core Services
- **pdf_processor_service** (port 8000): Central coordinator that orchestrates PDF processing workflows
- **pdf_extraction_service** (port 8002): Extracts tables, images, and text from PDFs using docling
- **embedder_service** (port 8005): Chunks text and creates embeddings for vector storage in ChromaDB
- **chat_service** (port 8001): Handles RAG queries using retrieved context chunks
- **docling_translation_service** (port 8003): Translates docling-format JSON structures
- **pdf_renderer_service** (port 8004): Overlays translated content onto original PDFs
- **image_captioner_service**: Generates captions for extracted images using VLM

### Frontend & Gateway
- **frontend** (port 8501): Streamlit web interface with multi-page navigation
- **nginx** (port 8080): API gateway that routes requests and handles file uploads

### Data Services
- **redis** (port 6379): Session storage and caching
- **chromadb** (port 5100): Vector database for embeddings
- **minio** (ports 9000/9001): S3-compatible object storage for files

### Service Communication
Services communicate via HTTP REST APIs. The nginx gateway routes external requests to appropriate services. Session management is handled through Redis with session IDs passed between services.

## File Structure Patterns

### Service Structure
Each service follows this pattern:
```
service_name/
├── main.py              # FastAPI app entry point
├── Dockerfile
├── requirements.txt
├── .env                 # Environment configuration
├── example.env          # Environment template
├── models/              # Pydantic models and business logic
│   ├── __init__.py
│   └── *.py
└── routers/             # API route handlers
    ├── __init__.py
    ├── health.py        # Health check endpoint
    └── *.py
```

### Shared Components
- **shared_utils/**: Common utilities for ChromaDB, OpenAI, Redis, and S3 connections

## Environment Configuration

Each service requires a `.env` file based on its `example.env` template. Key environment variables include service URLs, database connections, and API keys.

## Code Review Process

All changes follow a structured review process:
1. Open Pull Request
2. Address Gemini auto-review suggestions  
3. Peer review (rotation-based)
4. Senior reviewer final approval and merge

Focus areas for reviews: correctness, clarity, structure (models/routers pattern), security, and unnecessary files.