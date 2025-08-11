# OmniPDF Shared Values

This directory contains shared configuration templates that provide consistent settings across all OmniPDF Kubernetes deployments.

**Note**: Development uses `docker-compose.yml` for local development, not Helm.

## File Structure

```
shared-values/
├── common-base.yaml       # Base configuration for all Kubernetes environments
├── common-staging.yaml    # Staging environment overrides  
├── common-prestaging.yaml # Pre-staging environment overrides
├── common-prod.yaml       # Production environment overrides
└── README.md             # This file
```

## Usage

### Development (Local)
```bash
# Use docker-compose for local development
docker-compose up -d                    # Start all services
docker-compose logs -f chat_service     # View logs
docker-compose down                     # Stop all services
```

### Staging Deployment (Kubernetes)
```bash
# Deploy single service with shared staging values
make install CHART_NAME=chat-service ENV=staging

# Deploy all services with shared staging values
make install-all ENV=staging

# Manual deployment with multiple values files
helm install chat-service helm/chat-service \
  -f helm/shared-values/common-base.yaml \
  -f helm/shared-values/common-staging.yaml \
  -f helm/chat-service/values-staging.yaml \
  --namespace omnipdf
```

### Production Deployment (Kubernetes)
```bash
# Deploy single service with shared production values
make install CHART_NAME=chat-service ENV=prod

# Deploy all services with shared production values
make install-all ENV=prod

# Manual deployment with multiple values files
helm install chat-service helm/chat-service \
  -f helm/shared-values/common-base.yaml \
  -f helm/shared-values/common-prod.yaml \
  -f helm/chat-service/values-prod.yaml \
  --namespace omnipdf
```

## Configuration Hierarchy

Values are applied in order (later values override earlier ones):

1. **common-base.yaml** - Base configuration for all Kubernetes environments  
2. **common-{env}.yaml** - Environment-specific shared configuration
3. **{service}/values-{env}.yaml** - Service-specific environment configuration  
4. **{service}/values.yaml** - Service-specific base configuration

## Deployment Environments

| Environment | Purpose | Infrastructure |
|-------------|---------|----------------|
| **Development** | Local coding and testing | `docker-compose.yml` |
| **Staging** | Integration testing | Kubernetes + Helm |  
| **Pre-staging** | Pre-production validation | Kubernetes + Helm |
| **Production** | Live environment | Kubernetes + Helm |

## Benefits

- **Consistency**: All services share common security, monitoring, and deployment patterns
- **Maintainability**: Change network policies once, apply to all services
- **Environment Parity**: Ensure dev/staging/prod environments are configured consistently
- **Service Flexibility**: Services can still override shared values when needed

## Adding New Shared Configuration

1. Add new configuration to `common-base.yaml`
2. Add environment-specific overrides to `common-{env}.yaml` files
3. Test with one service first
4. Deploy to all services

## Service-Specific Overrides

Services can still override shared values in their own values files:

```yaml
# In chat-service/values.yaml
# Override shared resource limits for this service only
resources:
  limits:
    cpu: 3000m  # Higher than shared default
    memory: 4Gi
```