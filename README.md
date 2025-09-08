# OmniPDF

OmniPDF is a PDF analyzer capable of translation, summarization, captioning and conversational capabilities through Retrieval-Augmented-Generation (RAG). 

## Port Assignments

The following port mappings are used across the OmniPDF microservices in both development and production deployments. The architecture uses **nginx as an API gateway** that routes external traffic to backend services, with **standardized port 8000** for all core microservices to simplify service discovery and NetworkPolicy configuration.

> **Note:** In production Kubernetes deployments, services communicate internally via ClusterIP services and are secured with **zero-trust NetworkPolicy** configurations. External access is controlled through **Kubernetes Ingress**, **Istio Service Mesh**, or **OpenShift Routes** that route to the nginx gateway on port 8080.

| Service                   | Description                                               | Port   |
|---------------------------|-----------------------------------------------------------|--------|
| **Frontend Services**     |                                                           |        |
| Streamlit Frontend        | Web UI for user interaction                               | 8501   |
| Nginx API Gateway         | Proxies requests and handles file uploads                 | 8080   |
| **Core Processing Services** |                                                        |        |
| PDF Processor Service     | Main orchestrator - coordinates all processing workflows  | 8000   |
| PDF Extraction Service    | Extracts tables and images from PDFs using docling        | 8000   |
| Docling Translation Service | Translates text fields in docling-format JSON           | 8000   |
| PDF Renderer Service      | Renders translated content onto original PDFs             | 8000   |
| Embedder Service          | Chunks text and creates embeddings for vector storage     | 8000   |
| Chat Service              | RAG chat interface using retrieved context chunks         | 8000   |
| Image Captioner Service   | AI image captioning for extracted images using VLM        | 8000   |
| Metadata Service          | Document metadata and word cloud generation               | 8000   |
| Cleaner                   | Event-driven cleanup of expired sessions and files via Redis notifications | N/A    |
| **AI/ML Services**        |                                                           |        |
| vLLM Text Model           | Text-only LLM (Eg. Qwen2.5) for chat/translation          | 8000   |
| vLLM Vision-Language Model | Multimodal VLM (Eg. Qwen2-VL) for image captioning       | 8000   |
| **Data Services**         |                                                           |        |
| Redis                     | Session storage and caching                               | 6379   |
| ChromaDB                  | Vector database for embeddings                            | 8000   |
| MinIO                     | S3-compatible object storage for files                    | 9000   |
| MinIO Console             | MinIO web-based Admin UI                                  | 9001   |

## Architecture

OmniPDF follows a **microservices architecture** with **centralized orchestration**:

- **pdf-processor-service**: Main hub that coordinates all processing workflows
- **Processing services**: Specialized services for extraction, translation, rendering, embedding, and chat
- **Data layer**: Redis (sessions), ChromaDB (vectors), MinIO (files)
- **AI/ML layer**: vLLM text and vision-language models

## Deployment Environments

OmniPDF supports multiple deployment environments with **Kubernetes + Helm**:

- **Development**: Docker Compose for local development
- **Pre-staging**: CodeReady Containers (CRC) with Helm charts and local OpenShift registry
- **Staging**: Offline OpenShift Container Platform (OCP) with Helm deployment
- **Production**: Offline OpenShift Container Platform (OCP) with Helm deployment

**Container Registry Patterns**:
- **Development**: Local Docker images
- **Pre-staging**: `default-route-openshift-image-registry.apps-crc.testing/omnipdf/SERVICE_NAME`
- **Staging/Production**: Internal/disconnected registries (images must be pre-mirrored)

## Quick Start

### Development (Docker Compose)
```bash
# Start all services
docker compose up --build

# Start with GPU support (for LLM services)
docker compose -f docker-compose.gpu.yml up --build
```

### Kubernetes/OpenShift (Helm)
```bash
# Deploy individual service
helm install chat-service ./helm/chat-service --namespace omnipdf

# Deploy all services
for service in helm/*/; do
  service_name=$(basename "$service")
  helm install "$service_name" "$service" --namespace omnipdf
done

# Deploy RBAC (service accounts and permissions)
helm install omnipdf-rbac ./helm/rbac --namespace omnipdf
```

## Security Features

OmniPDF implements **defense-in-depth security** with multiple layers:

### Service Account & RBAC
- **Individual service accounts** for each service with per-service secret isolation
- **RBAC roles** with principle of least privilege:
  - `orchestrator-role`: pdf-processor (full coordination access)
  - `individual-service-roles`: Each service accesses only its own secrets
  - `cleaner-role`: Full data store access for cleanup operations
- **Complete audit trail** for inter-service communication

### NetworkPolicy (Zero-Trust)
- **Network segmentation** between services
- **Ingress/egress controls** based on service communication matrix
- **DNS and HTTPS egress** allowed for external services
- **Pod selector-based** traffic rules

### HPA (Horizontal Pod Autoscaler)
- **6 services** with auto-scaling enabled (nginx, chat-service, pdf-processor, etc.)
- **CPU/Memory thresholds**: 70% CPU, 80% Memory
- **High availability**: Minimum 2 replicas for critical services
- **Resource optimization**: Scale from 2-10 replicas based on load

## Security Configuration

```bash
# Enable NetworkPolicy for production
helm upgrade chat-service ./helm/chat-service \
  --set networkPolicy.enabled=true \
  --namespace omnipdf

# Check service account permissions
kubectl auth can-i get secrets \
  --as=system:serviceaccount:omnipdf:chat-service \
  -n omnipdf

# Monitor HPA status
kubectl get hpa -n omnipdf
```

## CRC (OpenShift Local) Setup

OmniPDF uses Red Hat CodeReady Containers (CRC) for local OpenShift development. Due to the resource-intensive nature of running 8+ microservices, CRC requires significant CPU and memory allocation.

### Recommended CRC Configuration

#### Quick Setup (Recommended)
```bash
# Run the automated setup script
./config/crc/setup-crc.sh

# Start CRC with configured settings
crc start

# Set up oc environment
eval $(crc oc-env)

# Get login credentials and login
crc console --credentials
oc login -u kubeadmin -p <password> https://api.crc.testing:6443 --insecure-skip-tls-verify
```

#### Manual Configuration
Alternatively, configure CRC manually:

```bash
# Stop CRC if running
crc stop

# Configure CRC resources (adjust based on your system)
crc config set memory 262144    # 256GB RAM
crc config set cpus 32          # 32 CPU cores
crc config set disk-size 80     # 80GB disk

# Start CRC with new configuration
crc start
```

### Configuration Notes

- **Memory**: 256GB recommended for running all microservices without constraints
- **CPU**: 32 cores provides abundant processing power for OpenShift + services
- **Disk**: 80GB sufficient for container images and persistent data
- **Configuration saved**: Current settings stored in `config/crc/crc-config.txt`

### Verify Setup

```bash
# Check CRC status
crc status

# Check node resources
oc describe node crc | grep -A 10 "Allocated resources"

# View current configuration
crc config view
```

## Documentation

### Architecture & Design
- [Service Communication Matrix](service-communication-matrix.md): Complete ingress/egress patterns for all services
- [Service Account Matrix](service-account-matrix.md): RBAC permissions and secret access patterns

### Security & Operations
- [Service Account Setup](SERVICE-ACCOUNT-SETUP.md): RBAC implementation and deployment guide
- [Secret Management](SECRET-MANAGEMENT.md): Per-service secret isolation strategy
- [HPA Configuration](HPA-CONFIGURATION.md): Auto-scaling configuration and monitoring

## Testing

```bash
# Run all service unit tests (206+ tests across 7 services)
./scripts/test-all-services.sh

# Run tests for individual service
./scripts/test-single-service.sh chat_service

# Security scanning with Trivy
./scripts/scan_with_trivy.sh

# Lint all Helm charts
for chart in helm/*/; do helm lint "$chart"; done
```

## Development Workflow

This project uses a `Makefile` to simplify common Helm and Kubernetes operations.

To get started, run:

```bash
make help
```
