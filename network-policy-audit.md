# Network Policy Comprehensive Audit

Based on C4 diagram analysis. Checking all services for correct network policies.

## Services with Network Policies

| Service | Has NetworkPolicy | Ingress Rules | Egress Rules | LLM Access | Status |
|---------|------------------|---------------|--------------|------------|--------|
| chat-service | ✅ | ? | ? | Zero-trust | ? |
| chromadb | ✅ | ? | ? | ❌ Fixed | ? |
| cleaner | ✅ | ? | ? | ❌ | ? |
| docling-translation-service | ✅ | ? | ? | ✅ Legacy | ? |
| embedder-service | ✅ | ? | ? | ❌ | ? |
| image-captioner-service | ✅ | ? | ? | Zero-trust | ? |
| metadata-service | ✅ | ? | ? | ✅ Legacy | ? |
| minio | ✅ | ? | ? | ❌ Fixed | ? |
| nginx | ✅ | ? | ? | ❌ Fixed | ? |
| pdf-extraction-service | ✅ | ? | ? | ❌ Fixed | ? |
| pdf-processor-service | ✅ | ? | ? | ❌ | ? |
| pdf-renderer-service | ✅ | ? | ? | ❌ Fixed | ? |
| redis | ✅ | ? | ? | ❌ Fixed | ? |

## Missing Network Policies

| Service | In C4 Diagram | Missing NetworkPolicy | Risk Level |
|---------|---------------|----------------------|------------|
| frontend | ✅ | ❌ | HIGH |
| istio-gateway | ✅ | ❌ | MEDIUM |

## Critical Issues Found

### ❌ Infrastructure Services with Inappropriate HTTPS Access
| Service | Issue | Risk | Fix Needed |
|---------|-------|------|------------|
| minio (prod) | `allowHTTPS: true` | HIGH | Should be `false` - object storage doesn't call external APIs |
| redis (prod) | `allowHTTPS: true` | HIGH | Should be `false` - cache doesn't call external APIs |
| pdf-extraction-service | `allowHTTPS: true` | MEDIUM | Should be `false` - uses local docling only |
| pdf-renderer-service | `allowHTTPS: true` | MEDIUM | Should be `false` - renders content only |

### ✅ Services with Legitimate HTTPS Access  
| Service | Reason | Status |
|---------|--------|--------|
| chat-service | External vLLM calls | ✅ Correct |
| docling-translation-service | External vLLM calls | ✅ Correct |
| image-captioner-service | External vLLM calls | ✅ Correct |
| metadata-service | External vLLM calls | ✅ Correct |
| embedder-service | May download models | ❓ Needs verification |

## C4 Diagram Connection Analysis

### Expected Ingress Traffic (who calls this service)
- nginx ← External users
- istio-gateway ← nginx  
- frontend ← istio-gateway
- pdf-processor-service ← frontend, istio-gateway
- Other services ← pdf-processor-service (orchestrator)

### Expected Egress Traffic (this service calls)
Based on C4 diagram arrows:
- docling-translation-service → vllm_text (LLM)
- chat-service → vllm_text (LLM)
- metadata-service → vllm_text (LLM)  
- image-captioner-service → vllm_vlm (LLM)
- All services → redis (sessions)
- Multiple services → minio (files)
- embedder-service, chat-service → chromadb (vectors)