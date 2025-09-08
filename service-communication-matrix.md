# Service Communication Matrix - Ingress/Egress

| Service | Ingress From | Ingress Port | Egress To | Egress Port | Description |
|---------|--------------|--------------|-----------|-------------|-------------|
| nginx | External users | 443, 80 | istio-gateway | 443, 80 | HTTPS/HTTP from browsers → Route to Istio mesh |
| istio-gateway | nginx | 443, 80 | frontend, pdf-processor | 8501, 8000 | Traffic from external gateway → Route UI/API requests |
| frontend | istio-gateway | 8501 | pdf-processor | 8000 | UI requests from users → Document metadata requests |
| pdf-processor | istio-gateway, frontend | 8000 | pdf-extraction, docling-translate, pdf-renderer, embedder, chat-service, metadata-service, minio, redis | 8000, 8000, 8000, 8000, 8000, 8000, 9000, 6379 | API/metadata requests → Orchestrate all processing services |
| pdf-extraction | pdf-processor | 8000 | image-captioner, minio | 8000, 9000 | Table/image extraction → Caption images & store files |
| docling-translate | pdf-processor | 8000 | vllm-text | 8000 | Translation requests → LLM translation |
| pdf-renderer | pdf-processor | 8000 | - | - | Render requests → No egress |
| embedder | pdf-processor | 8000 | chromadb | 8000 | Chunking/embedding → Store embeddings |
| chat-service | pdf-processor | 8000 | vllm-text, chromadb | 8000, 8000 | RAG requests → LLM chat & query vectors |
| image-captioner | pdf-extraction | 8000 | vllm-vlm | 8000 | Image requests → VLM captioning |
| metadata-service | pdf-processor | 8000 | vllm-text | 8000 | Metadata requests → LLM generation |
| cleaner | None (background) | - | minio, chromadb, redis | 9000, 8000, 6379 | Background worker → Clean expired data |
| vllm-text | docling-translate, chat-service, metadata-service | 8000 | - | - | LLM requests → No egress |
| vllm-vlm | image-captioner | 8000 | - | - | VLM requests → No egress |
| chromadb | embedder, chat-service, cleaner | 8000 | - | - | Vector operations → No egress |
| minio | pdf-processor, pdf-extraction, cleaner | 9000 | - | - | File operations → No egress |
| redis | pdf-processor, cleaner | 6379 | - | - | Session operations → No egress |

## Key Patterns

### Hub Services
- **pdf-processor**: Main orchestrator - connects to 8 services
- **cleaner**: Cleanup hub - connects to all 3 data stores

### LLM Usage
- **vllm-text**: Serves 3 services (docling-translate, chat-service, metadata-service)
- **vllm-vlm**: Serves 1 service (image-captioner)

### Data Access Patterns
- **minio**: Accessed by 3 services (pdf-processor, pdf-extraction, cleaner)
- **chromadb**: Accessed by 3 services (embedder, chat-service, cleaner)
- **redis**: Accessed by 2 services (pdf-processor, cleaner)

### External Access
- Only **nginx** and **istio-gateway** have external ingress
- Only **pdf-processor** receives direct API calls from outside the mesh

## Security Implications

This matrix shows the exact traffic patterns needed for:
1. **NetworkPolicy** configurations (ingress/egress rules)
2. **Service Account** RBAC permissions 
3. **Istio** authorization policies
4. **Zero-trust** network segmentation