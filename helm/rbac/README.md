# OmniPDF RBAC Configuration

This Helm chart provides Role-Based Access Control (RBAC) configuration for all OmniPDF services using a **universal template** that generates precise service-to-service permissions based on the C4 architecture diagram.

## Architecture Overview

The RBAC implementation follows the OmniPDF microservices architecture with **explicit service-to-service access control**:

```
┌─────────────────────────────────────────────────────────────────┐
│                     OmniPDF Service Mesh                       │
├─────────────────────────────────────────────────────────────────┤
│ 🌐 External Entry  │ nginx → istio-gateway                       │
│ 🖥️  Frontend       │ frontend                                    │  
│ 🎯 Orchestrator    │ pdf-processor-service (main coordinator)   │
│ ⚙️  Processing      │ 5 services: extraction, translation, etc.  │
│ 🤖 AI/ML           │ 2 services: image captioning, metadata     │
│ 💾 Data Stores     │ 3 services: MinIO, ChromaDB, Redis         │
│ 🧹 Utility         │ 1 service: Background cleaner              │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Structure

### Universal Template System

**Single Template File**: `templates/service-roles.yaml`
- **Generates**: Role + RoleBinding for each enabled service
- **Configuration**: Driven by explicit `values.yaml` declarations
- **Principle**: Each service declares exactly what it can call/access

### Service Coverage (15/15 Complete)

✅ **All services have RBAC coverage:**

| Layer | Service | Service Account | Status |
|-------|---------|----------------|--------|
| **External** | nginx | `nginx` | ✅ |
| **Gateway** | istio-gateway | `istio-gateway` | N/A |
| **Frontend** | frontend | `frontend` | ✅ |
| **Orchestrator** | pdf-processor-service | `pdf-processor-service` | ✅ |
| **Processing** | pdf-extraction-service | `pdf-extraction-service` | ✅ |
| **Processing** | docling-translation-service | `docling-translation-service` | ✅ |
| **Processing** | pdf-renderer-service | `pdf-renderer-service` | ✅ |
| **Processing** | embedder-service | `embedder-service` | ✅ |
| **Processing** | chat-service | `chat-service` | ✅ |
| **AI/ML** | image-captioner-service | `image-captioner-service` | ✅ |
| **AI/ML** | metadata-service | `metadata-service` | ✅ |
| **Data** | chromadb | `chromadb` | ✅ |
| **Data** | minio | `minio` | ✅ |
| **Data** | redis | `redis` | ✅ |
| **Utility** | cleaner | `cleaner` | ✅ |

## Permission Model

### Service Communication Matrix (Per C4 Diagram)

**External Traffic Flow:**
```
External User → nginx → istio-gateway → frontend/pdf-processor-service
```

**Processing Orchestration:**
```
pdf-processor-service → [all processing services] → [data stores]
```

**Data Access Patterns:**
```
• ChromaDB ← embedder, chat, metadata, cleaner
• MinIO ← pdf-processor, extraction, renderer, translation, embedder, chat, metadata, cleaner  
• Redis ← pdf-processor, extraction, translation, embedder, chat, renderer, metadata, cleaner
```

**External API Calls:**
```
• vLLM Text ← docling-translation, chat, metadata
• vLLM Vision ← image-captioner
```

### Current RBAC Configuration Issues

Based on C4 diagram analysis, current `values.yaml` has missing permissions:

| Service | Missing Permissions | Required by C4 |
|---------|-------------------|----------------|
| **embedder-service** | `minio`, `redis` | ✅ Store job status, file lists |
| **chat-service** | `minio`, `redis` | ✅ File operations, session management |
| **docling-translation-service** | `minio`, `redis` | ✅ Store translated JSON, file lists |
| **pdf-renderer-service** | `redis` | ✅ Session management |
| **metadata-service** | `redis` | ✅ Document file lists |

## Configuration Structure

### Service Declaration Format

Each service declares its permissions explicitly:

```yaml
rbac:
  service-name:
    enabled: true
    canCall:
      target-service: true           # Service discovery permission
    canAccess:
      secrets: ["service-secrets"]   # Secret access
      chromadb: true                 # Data store access
      minio: true
      redis: true
```

### Example: PDF Processor Service

```yaml
pdf-processor-service:
  enabled: true
  canCall:
    # All processing services (orchestration)
    pdf-extraction-service: true
    docling-translation-service: true
    pdf-renderer-service: true
    embedder-service: true
    chat-service: true
    metadata-service: true
  canAccess:
    # Data coordination
    minio: true                     # File storage coordination
    redis: true                     # Session management
    secrets: ["pdf-processor-secrets"]
```

## Generated RBAC Resources

For each enabled service, the template generates:

### Role Resource
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: omnipdf-{service}-role
rules:
  # Default permissions (pods, services, endpoints)
  - apiGroups: [""]
    resources: ["pods", "services", "endpoints"]
    verbs: ["get", "list"]
    
  # Service-specific call permissions
  - apiGroups: [""]
    resources: ["services", "endpoints"]
    resourceNames: ["{allowed-services}"]
    verbs: ["get", "list"]
    
  # Data access permissions
  - apiGroups: [""]
    resources: ["secrets"]
    resourceNames: ["{service}-secrets"]
    verbs: ["get"]
```

### RoleBinding Resource
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: omnipdf-{service}-binding
subjects:
- kind: ServiceAccount
  name: {service}
roleRef:
  kind: Role
  name: omnipdf-{service}-role
```

## Deployment

### Install RBAC Chart
```bash
helm install omnipdf-rbac ./helm/rbac -n omnipdf
```

### Update Configuration
```bash
helm upgrade omnipdf-rbac ./helm/rbac -n omnipdf \
  --set rbac.embedder-service.canAccess.minio=true \
  --set rbac.embedder-service.canAccess.redis=true
```

### Verify Installation
```bash
# Check all roles created
kubectl get roles -n omnipdf | grep omnipdf-

# Check all rolebindings created  
kubectl get rolebindings -n omnipdf | grep omnipdf-

# Verify specific service permissions
kubectl describe role omnipdf-pdf-processor-service-role -n omnipdf
```

## Security Model

### Principle of Least Privilege

- **AI Services**: Endpoint-only access, external API calls via NetworkPolicy
- **Data Services**: Accept connections only, no outbound service calls
- **Processing Services**: Specific access based on C4 communication patterns
- **Orchestrator**: Broad access to coordinate processing workflows

### Secret Isolation

Each service accesses only its own secrets:
- `pdf-processor-secrets`
- `pdf-extraction-secrets` 
- `chat-secrets`
- etc.

### Data Store Security

Data stores accept connections from authorized services only:
- **ChromaDB**: embedder, chat, metadata, cleaner
- **MinIO**: All services that store/retrieve files
- **Redis**: All services using sessions/file lists

## Troubleshooting

### Permission Testing
```bash
# Test service discovery
kubectl auth can-i get services \
  --as=system:serviceaccount:omnipdf:pdf-processor-service \
  -n omnipdf

# Test secret access
kubectl auth can-i get secrets/pdf-processor-secrets \
  --as=system:serviceaccount:omnipdf:pdf-processor-service \
  -n omnipdf

# Test data store access
kubectl auth can-i get services/minio \
  --as=system:serviceaccount:omnipdf:embedder-service \
  -n omnipdf
```

### Common Issues

1. **Service Discovery Fails**
   - Check if target service is in `canCall` configuration
   - Verify role includes service/endpoint permissions

2. **Secret Access Denied**
   - Ensure secret name matches `canAccess.secrets` list
   - Check role has correct secret resourceNames

3. **Data Store Connection Issues**
   - Verify data store access in `canAccess` (minio: true, etc.)
   - Check NetworkPolicy allows traffic (separate concern)

## Required Fixes

To align with C4 diagram, update `values.yaml`:

### Add Missing Data Store Access
```yaml
embedder-service:
  canAccess:
    minio: true      # ADD: Future job status storage
    redis: true      # ADD: Document file list management

chat-service:
  canAccess:
    minio: true      # ADD: File operations
    redis: true      # ADD: Future session management

docling-translation-service:
  canAccess:
    minio: true      # ADD: Store translated JSON
    redis: true      # ADD: Document file list management

pdf-renderer-service:
  canAccess:
    redis: true      # ADD: Future session management

metadata-service:
  canAccess:
    redis: true      # ADD: Document file list management
```

### Add Missing istio-gateway Service
```yaml
serviceAccounts:
  istio-gateway: "istio-gateway"    # ADD

rbac:
  istio-gateway:                    # ADD
    enabled: true
    canCall:
      frontend: true
      pdf-processor-service: true
    canAccess:
      secrets: ["istio-gateway-secrets"]
```

## Related Documentation

- [OmniPDF Architecture](../../CLAUDE.md) - Main project documentation
- [Service Communication Matrix](../../README.md) - Inter-service communication patterns  
- [NetworkPolicies](../*/templates/networkpolicy.yaml) - Network-level security controls
- [C4 Architecture Diagram](../../c4-diagram.puml) - System architecture reference
