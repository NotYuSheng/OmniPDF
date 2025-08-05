# Chat Service Helm Chart

This Helm chart deploys the chat-service microservice with production-ready configurations.

## Prerequisites

Before installing this chart, you must create the required Kubernetes secret:

```bash
# Create the secret with your actual API key
kubectl create secret generic chat-service-secrets \
  --from-literal=OPENAI_API_KEY=your-actual-api-key-here \
  --namespace omnipdf

# Or create from a file (more secure)
echo -n 'your-actual-api-key-here' > /tmp/api-key
kubectl create secret generic chat-service-secrets \
  --from-file=OPENAI_API_KEY=/tmp/api-key \
  --namespace omnipdf
rm /tmp/api-key
```

## Installation

```bash
# Install using Makefile
make install CHART_NAME=chat-service

# Or install directly with Helm
helm upgrade --install chat-service . \
  --namespace omnipdf \
  --create-namespace
```

## Security

- **Secrets**: API keys are stored in Kubernetes Secrets, not in values.yaml
- **Non-root**: Container runs as user 65534 (nobody)
- **Read-only filesystem**: Container filesystem is read-only
- **Dropped capabilities**: All Linux capabilities are dropped
- **Resource limits**: CPU and memory limits are enforced

## Configuration

Key configuration options in `values.yaml`:

```yaml
# Scaling
replicaCount: 2
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10

# Resources
resources:
  limits:
    cpu: 200m
    memory: 256Mi
  requests:
    cpu: 50m
    memory: 64Mi

# Image
image:
  repository: ghcr.io/notyusheng/chat-service
  pullPolicy: Never  # For offline environments
```

## Monitoring

The service exposes a `/health` endpoint on port 8000 for health checks.

## Troubleshooting

**Secret not found error:**
```bash
# Check if secret exists
kubectl get secret chat-service-secrets -n omnipdf

# Create the secret if missing (see Prerequisites above)
```

**Image pull errors with pullPolicy: Never:**
```bash
# Ensure image exists locally
docker images | grep chat-service

# Pull and tag image if needed
docker pull ghcr.io/notyusheng/chat-service:dev-v0.0.0-6653136
```