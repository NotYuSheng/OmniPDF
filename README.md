# OmniPDF Translate

> [!NOTE]
> This is a minimal staged release of OmniPDF focused exclusively on PDF translation functionality. Additional features (metadata, chat, image captioning) are available in other branches and will be released in future stages.

OmniPDF Translate is a microservices-based PDF translation application that preserves document layout and formatting while translating content to multiple languages.

## Features

- **PDF Upload**: Simple web interface for uploading PDF documents
- **AI-Powered Translation**: Leverages LLM models for accurate, context-aware translation
- **Layout Preservation**: Maintains original document structure, fonts, and formatting
- **Multi-Language Support**: Translate to various languages through configurable LLM endpoints
- **Session Management**: Redis-backed sessions for tracking document processing state
- **Scalable Architecture**: Microservices design ready for container orchestration

## Architecture

OmniPDF Translate follows a **microservices architecture** with **centralized orchestration**:

### Core Services
- **pdf-processor-service**: Central coordinator that orchestrates PDF translation workflows
- **pdf-extraction-service**: Extracts text and structure from PDFs using docling
- **docling-translation-service**: Translates docling-format JSON structures using LLM
- **pdf-renderer-service**: Overlays translated content onto original PDFs

### Frontend & Gateway
- **frontend**: Streamlit web interface with upload and translate pages
- **nginx**: API gateway that routes requests and handles file uploads

### Data Services
- **redis**: Session storage and caching
- **minio**: S3-compatible object storage for PDFs and intermediate files

## Translation Pipeline

1. **Upload**: User uploads PDF via frontend → nginx → pdf_processor_service → MinIO
2. **Extraction**: pdf_processor_service → pdf_extraction_service (docling extracts document structure)
3. **Translation**: docling JSON → docling_translation_service (translates text content using LLM)
4. **Rendering**: Translated content → pdf_renderer_service (generates translated PDF)
5. **Download**: Frontend retrieves translated PDF via presigned URL from MinIO

## Quick Start

### Development (Docker Compose)

```bash
# Start all services
docker compose up --build

# Access the application
# Open browser to http://localhost:8080
```

### Environment Setup

Each service requires environment variables configured in `.env` files. Copy the `example.env` files:

```bash
# For each service directory
cp service_name/example.env service_name/.env
# Edit .env files with your configuration (LLM endpoints, credentials, etc.)
```

Key configuration:
- **LLM Configuration**: Set OPENAI_BASE_URL, OPENAI_MODEL for translation service
- **MinIO Storage**: Configure MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY
- **Redis**: Configure REDIS_URL for session management

## Testing

```bash
# Run tests for individual services
./scripts/test-single-service.sh pdf_extraction_service
./scripts/test-single-service.sh pdf_renderer_service
./scripts/test-single-service.sh docling_translation_service
```

## Project Structure

```
service_name/
├── main.py              # FastAPI app entry point
├── Dockerfile
├── requirements.txt
├── .env                 # Environment configuration (create from example.env)
├── example.env          # Environment template
├── models/              # Pydantic models and business logic
├── routers/             # API route handlers
└── tests/               # Unit tests
```

## Roadmap

This minimal release focuses on core translation functionality. Future stages will include:

- **Stage 2**: Metadata extraction and word cloud generation
- **Stage 3**: Image captioning and visual content analysis
- **Stage 4**: Chat/Q&A with RAG over translated documents
- **Stage 5**: Kubernetes/OpenShift deployment with Helm charts

## License

[Add your license information here]
