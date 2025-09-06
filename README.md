# OmniPDF

OmniPDF is a PDF analyzer capable of translation, summarization, captioning and conversational capabilities through Retrieval-Augmented-Generation (RAG). 

## Port Assignments

The following port mappings are used across the OmniPDF microservices **for development and testing purposes only**. Ports for some core services are defined in the `docker-compose.yml` file, while other services listed are common components in the development setup (potentially run separately or via other configurations). This table aims to ensure clarity and avoid conflicts during local deployment.

> **Note:** These port numbers are **not** intended for production. Actual port exposure should be handled by production-grade routing layers such as **Kubernetes Ingress**, **Istio Service Mesh**, **OpenShift Routes**, or a **reverse proxy** in secured environments.

| Service                   | Description                                               | Port   |
|---------------------------|-----------------------------------------------------------|--------|
| Streamlit Frontend        | Web UI for user interaction                               | 8501   |
| Nginx API Gateway         | Proxies file uploads to PDF Processor                     | 8080   |
| PDF Processor Service     | Main coordinator for processing and routing               | 8000   |
| Chat Service              | Retrieves context chunks and queries LLM                  | 8001   |
| PDF Extraction Service    | Extracts tables and images from PDFs                      | 8002   |
| Docling Translate Service | Translates text fields in docling-style JSON              | 8003   |
| PDF Renderer Service      | Overlays translated tables and text onto the original PDF | 8004   |
| Embedder Service          | Chunks + embeds PDF text and stores in ChromaDB           | 8005   |
| vLLM LLM Server           | LLM backend for chat, translation, captions, summaries    | 1234   |
| Redis                     | In-memory session store                                   | 6379   |
| ChromaDB                  | Temporary in-memory vector store                          | 5100   |
| S3-Compatible Store       | Object storage (e.g., MinIO S3 API)                       | 9000   |
| MinIO Console             | MinIO web-based Admin UI                                  | 9001   |

## Deployment Environments

OmniPDF supports multiple deployment environments with different orchestration methods:

- **Development**: Docker Compose for local development
- **Pre-staging**: CodeReady Containers (CRC) with local OpenShift registry
- **Staging**: Offline OpenShift Container Platform (OCP) with internal registries
- **Production**: Offline OpenShift Container Platform (OCP) with internal registries

**Note**: Staging and production environments are offline/disconnected and cannot access external registries. All container images must be pre-mirrored to internal registries.

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

## Development Workflow

This project uses a `Makefile` to simplify common Helm and Kubernetes operations.

To get started, run:

```bash
make help
```
