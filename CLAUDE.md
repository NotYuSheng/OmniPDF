# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OmniPDF is a microservices-based PDF analyzer with translation, summarization, captioning and RAG capabilities. The system consists of 8 main services orchestrated via Docker Compose and deployable with Helm/Kubernetes.

## Core Architecture

### Service Structure
- **pdf_processor_service** (port 8000): Main coordinator for processing and routing
- **chat_service** (port 8001): RAG-based conversational interface with LLM integration
- **pdf_extraction_service** (port 8002): Extracts tables and images from PDFs
- **docling_translation_service** (port 8003): Translates docling-style JSON content
- **embedder_service** (port 8005): Text chunking and embedding with ChromaDB storage
- **nginx** (port 8080): API gateway proxying file uploads
- **cleaner**: Background cleanup service

### Dependencies
- **Redis** (port 6379): Session management
- **ChromaDB** (port 5100): Vector storage for embeddings
- **MinIO** (ports 9000/9001): S3-compatible object storage
- **vLLM** (port 1234): LLM backend server

### Project Structure
```
├── {service_name}/           # Each service follows this pattern:
│   ├── main.py              # FastAPI app with router includes
│   ├── routers/             # API endpoints (health.py always present)
│   ├── models/              # Pydantic models and business logic
│   ├── utils/               # Service-specific utilities
│   ├── Dockerfile           # Container definition
│   └── example.env          # Environment template
├── shared_utils/            # Common utilities across services
│   ├── openai_client.py     # OpenAI/vLLM client wrapper
│   ├── chroma_client.py     # ChromaDB async client
│   ├── redis.py             # Redis connection utilities
│   └── s3_utils.py          # MinIO/S3 operations
└── helm/                    # Kubernetes deployment
    └── chat-service/        # Example Helm chart structure
```

All services use FastAPI with consistent structure: main.py imports routers, routers handle endpoints, models contain business logic.

## Common Commands

### Development with Docker Compose
```bash
# Start all services
docker-compose up -d

# Start with GPU support
docker-compose -f docker-compose.gpu.yml up -d

# View logs for specific service
docker-compose logs -f chat_service

# Rebuild and restart service
docker-compose up -d --build chat_service
```

### Helm/Kubernetes Operations
```bash
# Get help with available commands
make help

# Install single service (defaults to dev environment)
make install CHART_NAME=chat-service ENV=staging

# Install all services
make install-all ENV=prod

# Upgrade service
make upgrade CHART_NAME=chat-service ENV=prod

# Check service status
make status CHART_NAME=chat-service

# Port forward to local machine
make port-forward CHART_NAME=chat-service LOCAL_PORT=8001 REMOTE_PORT=8000

# Lint Helm chart
make lint CHART_NAME=chat-service

# Uninstall service
make uninstall CHART_NAME=chat-service
```

### Environment Configuration
- Services use `.env` files (see `example.env` in each service directory)
- Helm uses environment-specific values: `values-{dev,staging,prestaging,prod}.yaml`
- Default namespace: `omnipdf`
- Use hyphens (not underscores) in chart names for Kubernetes compliance

## Key Implementation Details

### Service Communication
- Services communicate via HTTP APIs using shared utilities
- All services expose `/health` endpoint for monitoring
- nginx serves as API gateway for external requests
- Internal service discovery uses container names in Docker Compose

### Data Flow
1. Files uploaded via nginx (8080) → pdf_processor_service (8000)
2. pdf_processor_service orchestrates other services as needed:
   - pdf_extraction_service for tables/images
   - docling_translation_service for content translation
   - embedder_service for text processing
3. embedder_service chunks text → ChromaDB for vector storage
4. chat_service queries ChromaDB + LLM for RAG responses
5. Session data managed via Redis, file storage via MinIO

### Shared Utilities
- `openai_client.py`: Configurable OpenAI-compatible client (works with vLLM)
- `chroma_client.py`: Async ChromaDB client with environment-based config
- `redis.py`: Redis connection utilities for session management
- `s3_utils.py`: MinIO/S3 operations for file storage
- All shared utilities use environment variables for configuration

## Code Standards

### File Organization
- Follow the established `models/`, `routers/`, `utils/` structure within services
- Place cross-service utilities in `shared_utils/`
- Each service must have a health router

### Code Review Process
- All changes require peer review before merge
- Focus on correctness, clarity, structure, and security
- Use comment labels: `nit:`, `suggest:`, `blocking:`
- Final review by designated senior reviewer before merge

### Kubernetes Naming
- Use hyphens (not underscores) in resource names
- Follow RFC 1123 naming conventions
- Chart names should match service names with hyphens

## Testing and Quality

### Service Testing
- Each service should be tested independently
- Use the `/health` endpoints for basic connectivity testing
- Helm charts include test connections via `test-connection.yaml`
- E2E testing setup available in `cypress/` directory

### Development Dependencies
Each service uses minimal dependencies:
- **FastAPI** + **uvicorn** for web framework
- **OpenAI client** for LLM integration (compatible with vLLM)
- Service-specific requirements in each `{service}/requirements.txt`

### Port Assignments (Development Only)
Development ports are documented in README.md. Production deployments should use proper routing layers (Ingress, Service Mesh, etc.).