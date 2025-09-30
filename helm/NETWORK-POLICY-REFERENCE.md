# Network Policy Reference - OmniPDF

This document defines the correct network access patterns for all services based on the C4 architecture diagram.

## LLM Service Access Matrix

Based on the C4 diagram external AI connections, only these services should have LLM access:

### ✅ Services with Legitimate LLM Access

| Service | LLM Type | Purpose | Implementation |
|---------|----------|---------|----------------|
| `docling-translation-service` | vLLM Text | Translation requests | External HTTP/HTTPS |
| `metadata-service` | vLLM Text | Metadata generation | External HTTP/HTTPS + Legacy `allowLLMService` |
| `image-captioner-service` | vLLM VLM | Image captioning | External HTTP/HTTPS |

### ❌ Services that Should NOT Have LLM Access

| Service | Reason | Implementation |
|---------|--------|----------------|
| `redis` | Session store only | No LLM sections |
| `minio` | Object storage only | No LLM sections |
| `chromadb` | Vector database only | No LLM sections |
| `nginx` | Reverse proxy only | No LLM sections |
| `pdf-extraction-service` | Uses local docling, not external LLM | No LLM sections |
| `pdf-renderer-service` | Renders content only, no AI generation | No LLM sections |
| `embedder-service` | Uses local embedding models | Zero-trust `allowedTargets` |
| `cleaner` | Background cleanup tasks | Zero-trust `allowedTargets` |
| `frontend` | UI only, no direct LLM calls | Zero-trust `allowedTargets` |

## Network Policy Approaches

### 1. Zero-Trust `allowedTargets` (Recommended)
```yaml
networkPolicy:
  egress:
    allowedTargets:
      - podSelector:
          matchLabels:
            app.kubernetes.io/name: target-service
        ports: [8000]
```

**Used by:** `metadata-service`, `image-captioner-service`, `embedder-service`, `cleaner`, `frontend`

### 2. Legacy `allowLLMService` Section
```yaml
networkPolicy:
  egress:
    allowLLMService: true
    llmServiceSelectors: [...]
    llmServicePorts: [...]
```

**Used by:** `metadata-service`

**Note:** This approach should be migrated to zero-trust `allowedTargets` for consistency.

## Service Communication Patterns (from C4 Diagram)

### External AI Communication
- `docling-translation-service` → `vllm_text` (HTTP/HTTPS)
- `metadata-service` → `vllm_text` (HTTP/HTTPS)
- `image-captioner-service` → `vllm_vlm` (HTTP/HTTPS)

### Internal Service Communication (mTLS within Istio mesh)
- All services → `redis` (session validation)
- Multiple services → `minio` (file storage)
- `embedder-service`, `metadata-service`, `cleaner` → `chromadb` (vector operations and cleanup)
- `cleaner` → All storage services (cleanup)

## Security Principles

1. **Principle of Least Privilege**: Only grant network access that services actually need
2. **Zero-Trust Architecture**: Use explicit `allowedTargets` instead of broad service categories
3. **Defense in Depth**: Multiple network policy layers (Istio + Kubernetes NetworkPolicy)
4. **Architecture Alignment**: Network policies must match the C4 diagram connections

## Maintenance

When adding new services:
1. Identify external dependencies from architecture diagram
2. Use zero-trust `allowedTargets` approach
3. Document the decision in this reference
4. Avoid copy-paste from existing services without reviewing connections

## Recent Fixes

- **2025-01-12**: Fixed `docling-translation-service` NetworkPolicy - restored legitimate vLLM access per C4 diagram
- **2025-01-12**: Corrected documentation to reflect actual service requirements (HTTP/HTTPS to external vLLM)
- **2025-01-12**: Aligned all service configurations with C4 architecture diagram and source code analysis