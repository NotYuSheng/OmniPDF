# Service Account Security Implementation

This document describes the implementation of service account-based security for OmniPDF, providing defense-in-depth alongside NetworkPolicy.

## Overview

**Security Layers Implemented:**
1. **NetworkPolicy**: Controls network traffic between pods
2. **Service Accounts**: Provides service identity and RBAC permissions  
3. **RBAC**: Fine-grained permissions for inter-service communication

## Architecture

### Secret Management Strategy

**Per-Service Secret Isolation**: Each service has its own dedicated secret containing all credentials it needs.

**Trade-offs of This Approach:**
- ✅ **Security**: Complete secret isolation between services
- ✅ **Least Privilege**: Each service only accesses its own secret
- ✅ **Auditability**: Clear ownership of secrets per service
- ❌ **Duplication**: Same credentials (e.g., vLLM API key) stored in multiple secrets
- ❌ **Management Overhead**: More secrets to manage and rotate

**Secret Content Examples:**
```yaml
# chat-service-secrets contains:
OPENAI_BASE_URL: "http://vllm-text:8000/v1"
OPENAI_API_KEY: "shared-api-key"
CHROMADB_HOST: "chromadb"
CHROMADB_PORT: "8000"

# pdf-extraction-service-secrets contains:  
MINIO_ENDPOINT: "http://minio:9000"
MINIO_ACCESS_KEY: "minioadmin" 
MINIO_SECRET_KEY: "shared-key"

# cleaner-secrets contains ALL data store credentials:
MINIO_ENDPOINT: "http://minio:9000"
CHROMADB_HOST: "chromadb"
REDIS_URL: "redis://redis:6379"
# (plus all auth credentials for cleanup access)
```

**Alternative Considered**: Shared infrastructure secrets (e.g., `omnipdf-vllm-secrets`) but rejected to maintain strict service isolation.

### Service Account Roles

| **Role** | **Services** | **Permissions** |
|----------|--------------|-----------------|
| **orchestrator-role** | pdf-processor-service | Can discover and call all processing services, access service secrets for coordination |
| **individual-service-roles** | Each processing service has its own role | Can access only own service secret, limited service discovery |
| **cleaner-role** | cleaner | Access to cleaner-secrets (contains all data store credentials), can discover data services |
| **frontend-role** | frontend | Access to frontend-secrets (contains pdf-processor credentials), limited service discovery |
| **data-services-role** | minio, nginx | Access to own secrets only, minimal self-configuration |

**Key Change**: Replaced shared `processing-services-role` with individual roles per service to enforce per-service secret isolation.

### Communication Matrix

Based on the [service communication matrix](./service-communication-matrix.md), each service has specific RBAC permissions matching their required integrations.

## Deployment

### 1. Deploy RBAC Configuration

```bash
# Install RBAC roles and bindings
helm install omnipdf-rbac ./helm/rbac --namespace omnipdf

# Verify RBAC deployment
kubectl get roles,rolebindings -n omnipdf
```

### 2. Update Pod Labels (Optional)

For enhanced NetworkPolicy integration:

```bash
# Add service account labels to pod templates
./update-pod-labels.sh

# This enables NetworkPolicy to use service account identities
```

### 3. Deploy Services with Service Accounts

All services now have `serviceAccount.create: true` in their values.yaml files:

```bash
# Deploy individual services
helm install chat-service ./helm/chat-service --namespace omnipdf

# Or deploy all services
for service in helm/*/; do
  service_name=$(basename "$service")
  helm install "$service_name" "$service" --namespace omnipdf
done
```

### 4. Enable NetworkPolicy (Production)

```bash
# Enable NetworkPolicy in production environments
helm upgrade chat-service ./helm/chat-service \\
  --set networkPolicy.enabled=true \\
  --namespace omnipdf
```

## Testing Service Account Authentication

### 1. Verify Service Accounts

```bash
# List all service accounts
kubectl get serviceaccounts -n omnipdf

# Check service account tokens
kubectl describe serviceaccount pdf-processor-service -n omnipdf
```

### 2. Test RBAC Permissions

```bash
# Test if chat-service can access secrets
kubectl auth can-i get secrets \\
  --as=system:serviceaccount:omnipdf:chat-service \\
  -n omnipdf

# Test specific secret access
kubectl auth can-i get secret/chromadb-secrets \\
  --as=system:serviceaccount:omnipdf:chat-service \\
  -n omnipdf
```

### 3. Verify Inter-Service Communication

```bash
# Check if services can discover each other
kubectl exec -n omnipdf deployment/chat-service -- \\
  nslookup chromadb.omnipdf.svc.cluster.local

# Test HTTP connectivity (if service exposes health endpoint)
kubectl exec -n omnipdf deployment/chat-service -- \\
  curl -f http://chromadb:8000/health
```

### 4. Monitor Authentication Logs

```bash
# Check for authentication errors
kubectl logs -n omnipdf deployment/chat-service | grep -i auth

# Check RBAC denials in API server logs
kubectl logs -n kube-system deployment/kube-apiserver | grep RBAC
```

## Security Benefits

### Defense in Depth

1. **Network Layer**: NetworkPolicy blocks unauthorized network connections
2. **Identity Layer**: Service accounts provide authenticated service identity
3. **Authorization Layer**: RBAC controls what authenticated services can access

### Attack Scenarios Mitigated

| **Attack Vector** | **NetworkPolicy Protection** | **Service Account Protection** |
|-------------------|-------------------------------|--------------------------------|
| Pod Compromise | ✅ Blocks network access to unauthorized services | ✅ Limits API permissions to service role |
| Credential Theft | ❌ Attacker inherits network access | ✅ RBAC prevents privilege escalation |
| Code Vulnerability | ✅ Network segmentation | ✅ Principle of least privilege |
| Insider Threat | ✅ Zero-trust network model | ✅ Audit trail and fine-grained permissions |

## Troubleshooting

### Common Issues

**Service Account Not Created:**
```bash
# Check values.yaml
grep -A 5 "serviceAccount:" helm/*/values.yaml

# Should show: create: true
```

**RBAC Permission Denied:**
```bash
# Check role bindings
kubectl describe rolebinding chat-service-binding -n omnipdf

# Verify role permissions
kubectl describe role processing-services-role -n omnipdf
```

**NetworkPolicy Blocking Traffic:**
```bash
# Temporarily disable for testing
helm upgrade chat-service ./helm/chat-service \\
  --set networkPolicy.enabled=false

# Check pod labels for NetworkPolicy selectors
kubectl get pod -n omnipdf --show-labels
```

### Debug Commands

```bash
# Check service account token mount
kubectl exec -n omnipdf deployment/chat-service -- \\
  ls -la /var/run/secrets/kubernetes.io/serviceaccount/

# Verify service account permissions
kubectl auth can-i --list \\
  --as=system:serviceaccount:omnipdf:chat-service \\
  -n omnipdf

# Test network connectivity
kubectl exec -n omnipdf deployment/chat-service -- \\
  nc -zv chromadb 8000
```

## Security Best Practices

1. **Principle of Least Privilege**: Each service has minimal required permissions
2. **Service Isolation**: NetworkPolicy + RBAC prevent unauthorized access  
3. **Audit Logging**: All service-to-service calls are logged and traceable
4. **Regular Review**: Periodically audit RBAC permissions and communication patterns
5. **Secret Rotation**: Implement automatic service account token rotation

## Integration with Istio (Future)

When Istio is enabled, service accounts become the foundation for:
- **mTLS Authentication**: Automatic certificate generation per service account
- **Authorization Policies**: Fine-grained traffic policies based on service identity
- **Observability**: Service-level metrics and tracing
- **Traffic Management**: Service account-based routing and load balancing

## Monitoring

### Key Metrics to Monitor

- Service account authentication failures
- RBAC permission denials  
- Inter-service communication patterns
- Unauthorized network access attempts

### Alerts to Configure

- Repeated authentication failures from same service
- RBAC denials above baseline threshold
- Network traffic bypassing expected patterns
- Service accounts accessing unauthorized resources