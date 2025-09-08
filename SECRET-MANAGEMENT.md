# Secret Management Strategy

## Per-Service Secret Isolation

OmniPDF implements **per-service secret isolation** where each service manages its own dedicated secret containing all credentials it needs.

## Current Secret Structure

### Service Secrets

| **Service** | **Secret Name** | **Contains** |
|-------------|-----------------|--------------|
| pdf-processor-service | pdf-processor-service-secrets | Service configuration, coordination credentials |
| pdf-extraction-service | pdf-extraction-service-secrets | vLLM API credentials, MinIO credentials |
| docling-translation-service | docling-translation-service-secrets | vLLM API credentials |
| pdf-renderer-service | pdf-renderer-service-secrets | Service-specific configuration |
| embedder-service | embedder-service-secrets | ChromaDB credentials |
| chat-service | chat-service-secrets | vLLM API credentials, ChromaDB credentials |
| image-captioner-service | image-captioner-service-secrets | vLLM VLM API credentials |
| metadata-service | metadata-service-secrets | vLLM API credentials |
| cleaner | cleaner-secrets | MinIO credentials, ChromaDB credentials, Redis credentials |
| frontend | frontend-secrets | PDF Processor API credentials |
| minio | minio-secrets | MinIO root user/password, bucket configuration |
| nginx | nginx-secrets | Nginx configuration secrets |

### Credential Duplication

**Note**: This approach results in intentional credential duplication for security isolation:

- **vLLM API credentials** are duplicated in: `docling-translation-service-secrets`, `chat-service-secrets`, `metadata-service-secrets`, `image-captioner-service-secrets`
- **ChromaDB credentials** are duplicated in: `embedder-service-secrets`, `chat-service-secrets`, `cleaner-secrets`
- **MinIO credentials** are duplicated in: `pdf-extraction-service-secrets`, `cleaner-secrets`, `minio-secrets`

## Security Benefits

### 1. Complete Secret Isolation
- Services cannot access other services' secrets
- Compromise of one service doesn't expose all credentials
- Clear audit trail of which service accesses which credentials

### 2. Principle of Least Privilege
- Each service only has access to its own secret
- RBAC enforces secret access boundaries
- No shared secret access reduces attack surface

### 3. Service Independence
- Services can have different credential formats/versions
- Individual secret rotation without affecting other services
- Easier to trace credential usage per service

## Management Trade-offs

### Challenges

1. **Credential Duplication**: Same API keys stored in multiple secrets
2. **Rotation Complexity**: Must update credentials in multiple secrets
3. **Consistency Risk**: Credentials can become out of sync
4. **Storage Overhead**: More secrets to store and backup

### Mitigation Strategies

1. **Automated Secret Management**: Use external secret managers (Vault, External Secrets Operator)
2. **CI/CD Integration**: Automated secret updates during deployment
3. **Monitoring**: Alert on credential mismatches between services
4. **Documentation**: Clear mapping of which credentials are shared

## Secret Creation Examples

### Create Chat Service Secret
```bash
kubectl create secret generic chat-service-secrets \
  --from-literal=OPENAI_BASE_URL="http://vllm-text:8000/v1" \
  --from-literal=OPENAI_API_KEY="your-vllm-api-key" \
  --from-literal=CHROMADB_HOST="chromadb" \
  --from-literal=CHROMADB_PORT="8000" \
  --namespace omnipdf
```

### Create Cleaner Secret (Multi-service credentials)
```bash
kubectl create secret generic cleaner-secrets \
  --from-literal=MINIO_ENDPOINT="http://minio:9000" \
  --from-literal=MINIO_ACCESS_KEY="minioadmin" \
  --from-literal=MINIO_SECRET_KEY="your-minio-password" \
  --from-literal=CHROMADB_HOST="chromadb" \
  --from-literal=CHROMADB_PORT="8000" \
  --from-literal=REDIS_URL="redis://redis:6379" \
  --namespace omnipdf
```

### Create PDF Extraction Secret
```bash
kubectl create secret generic pdf-extraction-service-secrets \
  --from-literal=MINIO_ENDPOINT="http://minio:9000" \
  --from-literal=MINIO_ACCESS_KEY="minioadmin" \
  --from-literal=MINIO_SECRET_KEY="your-minio-password" \
  --namespace omnipdf
```

## Best Practices

### 1. Secret Content Standards
- Use consistent environment variable naming across services
- Include only necessary credentials per service
- Document secret contents in service documentation

### 2. Rotation Procedures
- Identify all secrets containing the same credential before rotation
- Use rolling updates to prevent service disruption
- Verify connectivity after credential updates

### 3. Monitoring and Alerting
- Monitor secret access patterns for anomalies
- Alert on authentication failures that may indicate stale credentials
- Track credential age and rotation schedules

### 4. Development vs Production
- Use different credentials per environment
- Never share production credentials in development secrets
- Use secret management tools for production deployments

## Alternative Architectures Considered

### Shared Infrastructure Secrets (Rejected)
```yaml
# This approach was rejected for security reasons
omnipdf-infrastructure-secrets:
  VLLM_API_KEY: "shared-key"
  MINIO_CREDENTIALS: "shared-creds"
  CHROMADB_CREDENTIALS: "shared-creds"
```

**Why Rejected**:
- Single point of failure for credential compromise
- Violates principle of least privilege
- Harder to audit which service uses which credential
- Complex RBAC required to limit access

### External Secret Management (Future)
- **External Secrets Operator**: Sync from external systems
- **HashiCorp Vault**: Dynamic credential generation
- **Cloud Provider Secret Managers**: AWS Secrets Manager, Azure Key Vault

## Troubleshooting

### Common Issues

1. **Secret Not Found**: Verify secret name matches values.yaml configuration
2. **Permission Denied**: Check RBAC allows service account to access secret
3. **Stale Credentials**: Verify credentials are current in external systems
4. **Inconsistent Secrets**: Compare credential values across duplicate secrets

### Debug Commands

```bash
# List all secrets
kubectl get secrets -n omnipdf

# Check secret contents (base64 encoded)
kubectl get secret chat-service-secrets -n omnipdf -o yaml

# Decode secret value
kubectl get secret chat-service-secrets -n omnipdf -o jsonpath='{.data.OPENAI_API_KEY}' | base64 -d

# Verify service can access secret
kubectl auth can-i get secret/chat-service-secrets \
  --as=system:serviceaccount:omnipdf:chat-service \
  -n omnipdf
```