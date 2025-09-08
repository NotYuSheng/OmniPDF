# Service Account Permission Matrix

## RBAC Permissions by Service Account

| Service Account | Role | Secret Access | Service Discovery | ConfigMap Access | Special Permissions |
|---|---|---|---|---|---|
| pdf-processor-service | orchestrator-role | pdf-extraction-service-secrets, docling-translation-service-secrets, pdf-renderer-service-secrets, embedder-service-secrets, chat-service-secrets, metadata-service-secrets, image-captioner-service-secrets, minio-secrets | services, endpoints (get, list, watch) | pdf-processor-config | Full orchestration access |
| pdf-extraction-service | pdf-extraction-service-role | pdf-extraction-service-secrets | image-captioner-service, minio (get, list) | - | Contains vLLM, MinIO credentials |
| docling-translation-service | docling-translation-service-role | docling-translation-service-secrets | - | - | Contains vLLM credentials |
| pdf-renderer-service | processing-services-role | pdf-renderer-service-secrets | - | - | Contains service-specific credentials |
| embedder-service | embedder-service-role | embedder-service-secrets | chromadb (get, list) | - | Contains ChromaDB credentials |
| chat-service | chat-service-role | chat-service-secrets | chromadb (get, list) | - | Contains vLLM, ChromaDB credentials |
| image-captioner-service | image-captioner-service-role | image-captioner-service-secrets | - | - | Contains vLLM VLM credentials |
| metadata-service | metadata-service-role | metadata-service-secrets | - | - | Contains vLLM credentials |
| cleaner | cleaner-role | cleaner-secrets | minio, chromadb, redis (get, list) | cleaner-config | Contains all data store credentials |
| frontend | frontend-role | frontend-secrets | pdf-processor-service (get, list) | frontend-config | Contains PDF Processor credentials |
| nginx | data-services-role | nginx-secrets | nginx (get) | nginx-config | Minimal self-configuration |
| minio | data-services-role | minio-secrets | minio (get) | minio-config | Minimal self-configuration |
| chromadb | data-services-role | N/A | chromadb (get) | chromadb-config | Externally managed |
| redis | data-services-role | N/A | redis (get) | redis-config | Externally managed |

## Service Communication Permissions

| Source Service | Target Service | Permission Type | RBAC Rule | NetworkPolicy Rule |
|---|---|---|---|---|
| **External Traffic** | | | | |
| nginx | istio-gateway | Network only | N/A | Allow ingress 443,80 |
| istio-gateway | frontend, pdf-processor | Network only | N/A | Allow egress 8501,8000 |
| | | | | |
| **Frontend → Backend** | | | | |
| frontend | pdf-processor | Secret access | frontend-secrets (contains PDF processor credentials) | Allow egress 8000 |
| | | | | |
| **Orchestration (PDF Processor)** | | | | |
| pdf-processor | pdf-extraction | Secret + Discovery | pdf-extraction-service-secrets | Allow egress 8000 |
| pdf-processor | docling-translate | Secret + Discovery | docling-translation-service-secrets | Allow egress 8000 |
| pdf-processor | pdf-renderer | Secret + Discovery | pdf-renderer-service-secrets | Allow egress 8000 |
| pdf-processor | embedder | Secret + Discovery | embedder-service-secrets | Allow egress 8000 |
| pdf-processor | chat-service | Secret + Discovery | chat-service-secrets | Allow egress 8000 |
| pdf-processor | metadata-service | Secret + Discovery | metadata-service-secrets | Allow egress 8000 |
| pdf-processor | minio | Secret + Discovery | minio-secrets | Allow egress 9000 |
| | | | | |
| **Processing → AI Services (via own secrets)** | | | | |
| docling-translate | vllm-text | Own secret access | docling-translation-service-secrets (contains vLLM credentials) | Allow egress 8000 |
| chat-service | vllm-text | Own secret access | chat-service-secrets (contains vLLM credentials) | Allow egress 8000 |
| metadata-service | vllm-text | Own secret access | metadata-service-secrets (contains vLLM credentials) | Allow egress 8000 |
| image-captioner | vllm-vlm | Own secret access | image-captioner-service-secrets (contains vLLM VLM credentials) | Allow egress 8000 |
| | | | | |
| **Processing → Data Services (via own secrets)** | | | | |
| pdf-extraction | minio | Own secret access | pdf-extraction-service-secrets (contains MinIO credentials) | Allow egress 9000 |
| embedder | chromadb | Own secret access | embedder-service-secrets (contains ChromaDB credentials) | Allow egress 8000 |
| chat-service | chromadb | Own secret access | chat-service-secrets (contains ChromaDB credentials) | Allow egress 8000 |
| pdf-extraction | image-captioner | Discovery only | Service discovery via role | Allow egress 8000 |
| | | | | |
| **Cleanup Operations** | | | | |
| cleaner | minio | Own secret access | cleaner-secrets (contains MinIO credentials) | Allow egress 9000 |
| cleaner | chromadb | Own secret access | cleaner-secrets (contains ChromaDB credentials) | Allow egress 8000 |
| cleaner | redis | Own secret access | cleaner-secrets (contains Redis credentials) | Allow egress 6379 |

## Permission Levels Explained

### **orchestrator-role** (pdf-processor)
- **Full orchestration access**: Can discover and communicate with all processing services
- **Data store access**: Can read secrets for all data stores (MinIO, ChromaDB, Redis)
- **Service discovery**: Can list all services and endpoints for dynamic routing

### **processing-services-role** (6 services)
- **AI service access**: Can communicate with vLLM services for text/vision processing
- **Limited data access**: Can only access specific data stores needed for their function
- **No inter-processing communication**: Cannot directly call other processing services

### **cleaner-role** (cleaner)
- **Full data store access**: Can access all data stores for cleanup operations
- **No processing access**: Cannot call processing services or AI services

### **frontend-role** (frontend)
- **Orchestrator only**: Can only communicate with pdf-processor service
- **No direct data access**: Must go through pdf-processor for all operations

### **data-services-role** (minio, chromadb, redis, nginx)
- **Minimal permissions**: Only self-configuration and health checks
- **No outbound calls**: Cannot initiate calls to other services

## Security Principles Applied

1. **Principle of Least Privilege**: Each service has only the minimum permissions needed
2. **Defense in Depth**: RBAC + NetworkPolicy provide multiple security layers
3. **Service Isolation**: Processing services cannot directly communicate with each other
4. **Hub-and-Spoke Model**: pdf-processor acts as central orchestrator
5. **Data Access Control**: Only authorized services can access specific data stores

## Audit and Monitoring Points

- **Secret Access**: Monitor which services access which secrets
- **Service Discovery**: Track service-to-service discovery patterns
- **Permission Denials**: Alert on RBAC permission denials
- **Network vs RBAC**: Compare NetworkPolicy allows vs RBAC permits
- **Anomaly Detection**: Flag unusual communication patterns