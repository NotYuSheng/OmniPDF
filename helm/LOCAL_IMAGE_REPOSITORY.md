# Local Image Repository Setup for Helm Charts

This document explains how to populate and configure local image repositories for OmniPDF Helm charts.

## Overview

OmniPDF Helm charts can work with different types of image repositories:
- **Public registries** (GitHub Container Registry, Docker Hub)
- **Local registries** (OpenShift CRC, Harbor, etc.)
- **Local Docker daemon** (for development)

## Option 1: Using GitHub Container Registry (Recommended)

### Step 1: Pull Images from GHCR
```bash
# Pull the required service image
docker pull ghcr.io/notyusheng/chat_service:dev-v0.0.0-6653136
docker pull ghcr.io/notyusheng/embedder_service:latest
# Add other services as needed
```

### Step 2: Update values.yaml
Edit `helm/<service-name>/values.yaml`:
```yaml
image:
  repository: ghcr.io/notyusheng/chat_service
  tag: "dev-v0.0.0-6653136"
```

### Step 3: Deploy
```bash
make install CHART_NAME=chat-service
```

## Option 2: Using OpenShift CRC Registry (Automated)

### Automated Image Loader Script

Use the provided `load-images.sh` script to automatically pull images from external registries and push them to CRC:

```bash
# Load single image
./helm/load-images.sh ghcr.io/notyusheng/chat_service:dev-v0.0.0-6653136

# Load multiple images
./helm/load-images.sh ghcr.io/notyusheng/chat_service:v1.0.0 ghcr.io/notyusheng/embedder_service:v1.1.0

# Load from file (recommended for multiple services)
./helm/load-images.sh -f images.txt
```

The script automatically handles login, pulling, tagging, and pushing to the CRC registry.

### Manual Process (Alternative)

### Prerequisites
- OpenShift CRC installed and running
- Access to CRC image registry

### Step 1: Start CRC
```bash
crc start
crc console --credentials  # Get login credentials
```

### Step 2: Login to Registry
```bash
# Login to OpenShift
oc login -u <username> -p <password> https://api.crc.testing:6443

# Login to image registry
docker login -u $(oc whoami) -p $(oc whoami -t) default-route-openshift-image-registry.apps-crc.testing
```

### Step 3: Create Project/Namespace
```bash
oc new-project omnipdf
```

### Step 4: Pull, Tag, and Push Images
```bash
# Pull from external registry
docker pull ghcr.io/notyusheng/chat_service:dev-v0.0.0-6653136

# Tag for CRC registry
docker tag ghcr.io/notyusheng/chat_service:dev-v0.0.0-6653136 \
  default-route-openshift-image-registry.apps-crc.testing/omnipdf/chat_service:dev-v0.0.0-6653136

# Push to CRC registry
docker push default-route-openshift-image-registry.apps-crc.testing/omnipdf/chat_service:dev-v0.0.0-6653136
```

### Step 5: Update values.yaml
```yaml
image:
  repository: default-route-openshift-image-registry.apps-crc.testing/omnipdf/chat_service
  pullPolicy: IfNotPresent
  tag: "dev-v0.0.0-6653136"
```

## Option 3: Local Docker Daemon (Development Only)

### Step 1: Build Images Locally
```bash
# Build from Dockerfile
cd chat_service/
docker build -t chat_service:latest .
```

### Step 2: Update values.yaml
```yaml
image:
  repository: chat_service
  pullPolicy: Never  # Forces use of local images only
  tag: "latest"
```

**Note**: This only works with single-node clusters like Docker Desktop or minikube.

## Option 4: Private Harbor Registry

### Step 1: Setup Harbor Registry
```bash
# Install Harbor (example using Docker Compose)
# Follow Harbor installation guide
```

### Step 2: Create Project
- Login to Harbor UI
- Create project `omnipdf`

### Step 3: Push Images
```bash
# Login to Harbor
docker login harbor.yourdomain.com

# Tag and push
docker tag ghcr.io/notyusheng/chat_service:dev-v0.0.0-6653136 \
  harbor.yourdomain.com/omnipdf/chat_service:dev-v0.0.0-6653136

docker push harbor.yourdomain.com/omnipdf/chat_service:dev-v0.0.0-6653136
```

### Step 4: Update values.yaml
```yaml
image:
  repository: harbor.yourdomain.com/omnipdf/chat_service
  pullPolicy: IfNotPresent
  tag: "dev-v0.0.0-6653136"

# If private registry requires authentication
imagePullSecrets:
  - name: harbor-registry-secret
```

### Step 5: Create Image Pull Secret
```bash
kubectl create secret docker-registry harbor-registry-secret \
  --docker-server=harbor.yourdomain.com \
  --docker-username=<username> \
  --docker-password=<password> \
  --docker-email=<email> \
  -n omnipdf
```

## Troubleshooting

### ImagePullBackOff Error
```bash
# Check pod events
kubectl describe pod <pod-name> -n omnipdf
kubectl get events -n omnipdf --sort-by='.lastTimestamp'

# Common causes:
# 1. Image doesn't exist in registry
# 2. Authentication required but not configured
# 3. Network connectivity issues
# 4. Wrong image tag/repository name
```

### Registry Authentication Issues
```bash
# Test registry connectivity
docker pull <registry-url>/<image>:<tag>

# Check image pull secrets
kubectl get secrets -n omnipdf
kubectl describe secret <secret-name> -n omnipdf
```

### Image Pull Policy Guidelines
- `Always`: Always pull the image from registry
- `IfNotPresent`: Pull only if image doesn't exist locally (default)
- `Never`: Only use local images, never pull

## Best Practices

1. **Use specific tags** instead of `latest` for production
2. **Set imagePullPolicy appropriately** based on your deployment strategy
3. **Use image pull secrets** for private registries
4. **Verify image exists** in registry before deployment
5. **Test image pulls** manually before Helm deployment

## Quick Commands

```bash
# Check current image configuration
helm get values chat-service -n omnipdf

# List available images in local Docker
docker images | grep chat_service

# Check pod image and status
kubectl describe pod -n omnipdf -l "app.kubernetes.io/name=chat-service"

# Update deployment with new image
make upgrade CHART_NAME=chat-service
```