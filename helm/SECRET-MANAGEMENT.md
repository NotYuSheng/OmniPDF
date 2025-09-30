# Secret Management in OmniPDF

This document explains how to access, manage, and work with Kubernetes/OpenShift secrets in the OmniPDF deployment.

## Overview

Secrets in OmniPDF are stored in the cluster's etcd database (not in files) and automatically injected into pods as environment variables. Each service has its own secret containing configuration values from its `.env` file.

## Secret Structure

All OmniPDF secrets follow this naming pattern:
- **Name**: `{service-name}-secrets` (e.g., `pdf-extraction-service-secrets`)
- **Type**: `Opaque` 
- **Namespace**: `omnipdf`
- **Encoding**: Base64 (not encrypted)

## Current Secrets

| Service | Secret Name | Keys | Purpose |
|---------|-------------|------|---------|
| pdf-extraction-service | `pdf-extraction-service-secrets` | 15 | LLM configuration, Redis URL |
| embedder-service | `embedder-service-secrets` | 4 | Embedding models, ChromaDB |
| pdf-extraction-service | `pdf-extraction-service-secrets` | 5 | PDF processing config |
| docling-translation-service | `docling-translation-service-secrets` | 7 | Translation settings |
| pdf-renderer-service | `pdf-renderer-service-secrets` | 5 | PDF rendering config |
| pdf-processor-service | `pdf-processor-service-secrets` | 8 | Main coordinator settings |
| image-captioner-service | `image-captioner-service-secrets` | 10 | VLM configuration |
| metadata-service | `metadata-service-secrets` | 17 | Metadata generation |
| cleaner | `cleaner-secrets` | 5 | Cleanup service config |
| nginx | `nginx-secrets` | 2 | Proxy settings |
| minio | `minio-secrets` | 2 | S3 storage credentials |

## How to Access Secrets

### List All Secrets
```bash
# Show all secrets in omnipdf namespace
oc get secrets -n omnipdf

# Show only OmniPDF service secrets (exclude system secrets)
oc get secrets -n omnipdf | grep -v "dockercfg\|token\|helm"
```

### Inspect Secret Structure
```bash
# Show secret keys and sizes (no values)
oc describe secret pdf-extraction-service-secrets -n omnipdf

# Show complete secret with Base64 encoded values
oc get secret pdf-extraction-service-secrets -n omnipdf -o yaml
```

### Decode Secret Values

#### Single Value
```bash
# Decode specific key
oc get secret pdf-extraction-service-secrets -n omnipdf -o jsonpath='{.data.OPENAI_API_KEY}' | base64 -d

# Example output: lm-studio
```

#### All Values
```bash
# Decode all keys in a secret
oc get secret pdf-extraction-service-secrets -n omnipdf -o json | jq -r '.data | to_entries[] | "\(.key): \(.value | @base64d)"'

# Example output:
# OPENAI_API_KEY: lm-studio
# OPENAI_MODEL: Qwen2.5-14B-Coder-Instruct
# REDIS_URL: redis://redis:6379/0?decode_responses=True&protocol=3
```

### View Secrets Inside Running Pods
```bash
# See how secrets appear as environment variables
oc exec -n omnipdf deployment/pdf-extraction-service -- env | grep -E "OPENAI_|REDIS_|MODEL_"

# Check specific service environment
oc exec -n omnipdf deployment/embedder-service -- env | sort
```

## How to Manage Secrets

### Create Secrets

#### From .env File (Recommended)
```bash
# Create secret from service .env file
oc create secret generic pdf-extraction-service-secrets \
    --from-env-file=pdf_extraction_service/.env \
    -n omnipdf
```

#### From Literal Values
```bash
# Create secret with individual key-value pairs
oc create secret generic my-secret \
    --from-literal=API_KEY=my-key \
    --from-literal=DATABASE_URL=postgres://... \
    -n omnipdf
```

### Update Secrets

#### Method 1: Interactive Edit
```bash
# Opens secret in editor (values are Base64 encoded)
oc edit secret pdf-extraction-service-secrets -n omnipdf
```

#### Method 2: Patch Single Value
```bash
# Update single key (encode value first)
oc patch secret pdf-extraction-service-secrets -n omnipdf \
    --patch='{"data":{"OPENAI_API_KEY":"'$(echo -n "new-api-key" | base64)'"}}'
```

#### Method 3: Replace Entire Secret
```bash
# Delete and recreate (recommended for multiple changes)
oc delete secret pdf-extraction-service-secrets -n omnipdf
oc create secret generic pdf-extraction-service-secrets \
    --from-env-file=pdf_extraction_service/.env \
    -n omnipdf

# Restart pods to pick up new values
oc rollout restart deployment/pdf-extraction-service -n omnipdf
```

### Delete Secrets
```bash
# Delete specific secret
oc delete secret pdf-extraction-service-secrets -n omnipdf

# Delete multiple secrets
oc delete secret secret1 secret2 secret3 -n omnipdf
```

## How Secrets Work in Pods

### Environment Variable Injection
Secrets are mounted as environment variables using `envFrom`:

```yaml
# In deployment template
spec:
  containers:
  - name: pdf-extraction-service
    envFrom:
    - secretRef:
        name: pdf-extraction-service-secrets
```

### Automatic Availability
All secret keys become environment variables inside the pod:
- `OPENAI_API_KEY=lm-studio`
- `REDIS_URL=redis://redis:6379/0`
- `MODEL_TEMPERATURE=0.1`

### Pod Restart Required
When secrets are updated, pods must be restarted to see new values:
```bash
oc rollout restart deployment/pdf-extraction-service -n omnipdf
```

## Secret Creation Process

OmniPDF secrets are created using the `create-secrets.sh` script:

```bash
#!/bin/bash
# Create Kubernetes secrets from .env files

NAMESPACE="omnipdf"

create_secret_from_env() {
    local service_name="$1"
    local env_file="$2"
    local secret_name="${service_name}-secrets"
    
    if [[ -f "$env_file" ]]; then
        oc create secret generic "$secret_name" \
            --from-env-file="$env_file" \
            -n "$NAMESPACE"
        echo "✅ Created secret: $secret_name"
    fi
}

# Create secrets for all services
create_secret_from_env "pdf-extraction-service" "pdf_extraction_service/.env"
create_secret_from_env "embedder-service" "embedder_service/.env"
# ... etc
```

## Security Best Practices

### ⚠️ Security Considerations
- **Secrets are Base64 encoded, NOT encrypted**
- **Use RBAC** to control who can access secrets
- **Secrets are namespace-scoped** - cannot access across namespaces
- **Never commit secrets to git** - use `.env` files locally only

### 🔒 Production Recommendations
- Use **external secret management** (HashiCorp Vault, AWS Secrets Manager)
- Consider **sealed-secrets** for GitOps workflows  
- Implement **secret rotation** policies
- Use **service accounts** with minimal permissions
- Enable **audit logging** for secret access

### 🛡️ OpenShift Security Context Constraints
OmniPDF runs with restrictive security:
- `readOnlyRootFilesystem: true`
- `runAsNonRoot: true`
- `allowPrivilegeEscalation: false`

## Troubleshooting

### Common Issues

#### Secret Not Found
```
Error: secret "service-secrets" not found
```
**Solution**: Create the secret or check the name in values file

#### ImagePullBackOff After Secret Update  
```
Warning: Failed to pull image: manifest unknown
```
**Solution**: Check if prestaging values files have correct image tags

#### Environment Variables Missing in Pod
```bash
# Check if secret is properly referenced
oc get deployment pdf-extraction-service -n omnipdf -o yaml | grep -A5 envFrom

# Check pod environment
oc exec deployment/pdf-extraction-service -n omnipdf -- env | grep MY_VAR
```

### Debugging Commands
```bash
# Check secret exists and has data
oc get secret pdf-extraction-service-secrets -n omnipdf -o yaml

# Verify pod can access secrets
oc exec deployment/pdf-extraction-service -n omnipdf -- printenv | grep -E "API_KEY|URL"

# Check deployment configuration
oc describe deployment pdf-extraction-service -n omnipdf | grep -A10 Environment

# View recent events
oc get events -n omnipdf --sort-by=.metadata.creationTimestamp
```

## Example: Complete Secret Lifecycle

```bash
# 1. Create secret from .env file  
oc create secret generic my-service-secrets \
    --from-env-file=my_service/.env \
    -n omnipdf

# 2. Verify secret created
oc get secret my-service-secrets -n omnipdf

# 3. Check values (decoded)
oc get secret my-service-secrets -n omnipdf -o json | \
    jq -r '.data | to_entries[] | "\(.key): \(.value | @base64d)"'

# 4. Update a value
oc patch secret my-service-secrets -n omnipdf \
    --patch='{"data":{"API_KEY":"'$(echo -n "new-key" | base64)'"}}'

# 5. Restart deployment to pick up changes
oc rollout restart deployment/my-service -n omnipdf

# 6. Verify new value in pod
oc exec deployment/my-service -n omnipdf -- printenv API_KEY
```

---

**Last Updated**: September 2025  
**Maintainer**: OmniPDF Team