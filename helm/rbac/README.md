# OmniPDF RBAC Configuration

This Helm chart provides Role-Based Access Control (RBAC) configuration for all OmniPDF services, organized by architectural layers based on the C4 container diagram.

## Architecture Overview

The RBAC implementation follows the OmniPDF microservices architecture with 6 distinct layers:

```
┌─────────────────────────────────────────────────────────────────┐
│                     C4 Architecture Layers                     │
├─────────────────────────────────────────────────────────────────┤
│ 🎯 Orchestrator    │ PDF Processor Service (main coordinator)   │
│ ⚙️  Processing      │ 5 services: extraction, translation, etc.  │
│ 🤖 AI/ML           │ 2 services: image captioning, metadata     │
│ 💾 Data            │ 3 services: MinIO, ChromaDB, Redis         │
│ 🖥️  Frontend       │ 1 service: Streamlit UI                    │
│ 🚪 Gateway         │ 1 service: Nginx ingress                   │
│ 🧹 Utility         │ 1 service: Background cleaner              │
└─────────────────────────────────────────────────────────────────┘
```

## RBAC Template Structure

### Template Files (14 Total - Individual Service Roles)

| Template | Service | Component | Description |
|----------|---------|-----------|-------------|
| `pdf-processor-service-role.yaml` | pdf-processor-service | Orchestrator | Main coordinator with broad permissions |
| `pdf-extraction-service-role.yaml` | pdf-extraction-service | Processing | PDF extraction with image captioning access |
| `docling-translation-service-role.yaml` | docling-translation-service | Processing | Translation service with minimal permissions |
| `embedder-service-role.yaml` | embedder-service | Processing | Embedding service with ChromaDB access |
| `chat-service-role.yaml` | chat-service | Processing | Chat service with ChromaDB access |
| `pdf-renderer-service-role.yaml` | pdf-renderer-service | Processing | PDF rendering with MinIO access |
| `image-captioner-service-role.yaml` | image-captioner-service | AI/ML | AI endpoint (no outbound calls) |
| `metadata-service-role.yaml` | metadata-service | AI/ML | AI endpoint (no outbound calls) |
| `minio-role.yaml` | minio | Data | Object storage endpoint |
| `chromadb-role.yaml` | chromadb | Data | Vector database endpoint |
| `redis-role.yaml` | redis | Data | Cache/session storage endpoint |
| `frontend-role.yaml` | frontend | Frontend | Streamlit UI service |
| `gateway-role.yaml` | nginx | Gateway | Ingress gateway service |
| `cleaner-role.yaml` | cleaner | Utility | Background cleanup service |

### Service Coverage (14/14 Complete)

✅ **All services from `values.yaml` have RBAC coverage:**

- **Orchestrator Layer**: `pdfProcessor`
- **Processing Layer**: `pdfExtraction`, `doclingTranslate`, `embedder`, `chatService`, `pdfRenderer` (separate template)  
- **AI/ML Layer**: `imageCaptioner`, `metadataService`
- **Data Layer**: `minio`, `chromadb`, `redis`
- **Frontend Layer**: `frontend`
- **Gateway Layer**: `nginx`
- **Utility Layer**: `cleaner`

## Permission Model

### Communication Patterns (Based on C4 Diagram)

```
🎯 Orchestrator (PDF Processor)
├── ⚙️ Processing Services (extraction, translation, etc.)
│   ├── 🤖 AI Services (image captioning, metadata)
│   └── 💾 Data Services (MinIO, ChromaDB, Redis)
└── 💾 Data Services (session management)

🖥️ Frontend ──→ 🎯 Orchestrator
🚪 Gateway ──→ 🖥️ Frontend + 🎯 Orchestrator
🧹 Cleaner ──→ 💾 Data Services (cleanup)
```

### Values.yaml Configuration Flags

The RBAC templates use conditional logic based on `values.yaml` flags:

```yaml
rbac:
  # Orchestrator permissions
  pdfProcessor:
    canCallProcessingServices: true    # Controls access to processing layer
    canAccessDataStores: true          # Controls access to data layer
    
  # Processing services permissions  
  processingServices:
    canCallAI: true                    # Controls access to AI services
    canAccessDataStores: true          # Controls access to data stores
    
  # AI services permissions
  aiServices:
    canCallServices: false             # Endpoints only (no outbound calls)
    
  # Data services permissions
  dataServices:
    canCallServices: false             # Endpoints only (no outbound calls)
    
  # Frontend permissions
  frontend:
    canCallProcessor: true             # Can call orchestrator
    
  # Gateway permissions
  gateway:
    canCallFrontendAndProcessor: true  # Can route to frontend + orchestrator
    
  # Cleaner permissions
  cleaner:
    canAccessAllDataStores: true       # Needs access for cleanup operations
    
  # PDF Renderer permissions
  pdfRenderer:
    canAccessStorage: true             # Needs MinIO access for file operations
```

## Deployment

### Install RBAC Only
```bash
helm install omnipdf-rbac ./helm/rbac -n omnipdf
```

### Install with Custom Values
```bash
helm install omnipdf-rbac ./helm/rbac -n omnipdf \
  --set rbac.processingServices.canCallAI=false \
  --set rbac.dataServices.canCallServices=true
```

### Verify Installation
```bash
# Check all roles created
kubectl get roles -n omnipdf

# Check all rolebindings created  
kubectl get rolebindings -n omnipdf

# Verify service account coverage
kubectl get serviceaccounts -n omnipdf
```

## Security Model

### Per-Service Secret Isolation

Each service has access to its own secrets only:
- `pdf-processor-service-secrets`
- `pdf-extraction-service-secrets`
- `chat-service-secrets`
- etc.

### Cross-Service Authentication

The orchestrator (PDF Processor) has conditional access to other service secrets based on `values.yaml` flags, enabling secure inter-service communication.

### Principle of Least Privilege

- **AI Services**: Endpoints only, no outbound service calls
- **Data Services**: Endpoints only, minimal self-discovery
- **Processing Services**: Conditional access based on communication patterns
- **Orchestrator**: Broad access only when enabled via configuration

## Troubleshooting

### Common Issues

1. **Service can't discover other services**
   ```bash
   # Check if the appropriate values.yaml flag is enabled
   helm get values omnipdf-rbac -n omnipdf
   ```

2. **Permission denied accessing secrets**
   ```bash
   # Verify the role includes the required secret
   kubectl describe role <service>-role -n omnipdf
   ```

3. **Missing service account**
   ```bash
   # Ensure service account exists and matches values.yaml
   kubectl get serviceaccount <service-name> -n omnipdf
   ```

### Verification Commands

```bash
# Test service discovery permissions
kubectl auth can-i get services \
  --as=system:serviceaccount:omnipdf:pdf-processor-service \
  -n omnipdf

# Test secret access permissions  
kubectl auth can-i get secrets/minio-secrets \
  --as=system:serviceaccount:omnipdf:pdf-processor-service \
  -n omnipdf
```

## Development

### Adding New Services

1. **Add to `values.yaml`**:
   ```yaml
   serviceAccounts:
     newService: "new-service-name"
   ```

2. **Create individual role template** based on service layer:
   - Copy appropriate template (`pdf-extraction-service-role.yaml`, `minio-role.yaml`, etc.)
   - Create new `new-service-role.yaml` with service-specific permissions
   - Follow pattern: service only accesses its own secrets and required data stores

3. **Update permission flags** if needed in `values.yaml`

### Testing Changes

```bash
# Validate template syntax
helm template ./helm/rbac

# Dry run deployment
helm upgrade --dry-run omnipdf-rbac ./helm/rbac -n omnipdf

# Apply changes
helm upgrade omnipdf-rbac ./helm/rbac -n omnipdf
```

## Related Documentation

- [OmniPDF Architecture](../../CLAUDE.md) - Main project documentation
- [Service Communication Matrix](../README.md) - Inter-service communication patterns
- [NetworkPolicies](../networkpolicies/) - Network-level security controls