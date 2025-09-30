# OmniPDF Istio Gateway Installation Guide

This guide helps you set up Istio service mesh for OmniPDF prestaging environment in CRC (CodeReady Containers).

## Prerequisites

1. **CRC Environment** running with sufficient resources:
   ```bash
   crc config set memory 12288  # 12GB RAM minimum
   crc config set cpus 6        # 6 CPUs minimum  
   crc start
   ```

2. **Istio CLI** installed (already available in `istio-1.27.1/bin/istioctl`)

## Installation Steps

### 1. Install Istio Control Plane

```bash
# Login to CRC cluster
oc login -u kubeadmin $(crc console --credentials | grep "kubeadmin" | cut -d' ' -f2)

# Install Istio using the downloaded binary
cd /home/ubuntu/Desktop/OmniPDF
./istio-1.27.1/bin/istioctl install --set values.defaultRevision=default -y

# Verify Istio installation
./istio-1.27.1/bin/istioctl verify-install
```

### 2. Create OmniPDF Prestaging Namespace

```bash
# Create namespace with Istio injection enabled
oc create namespace omnipdf-prestaging
oc label namespace omnipdf-prestaging istio-injection=enabled

# Verify namespace labels
oc get namespace omnipdf-prestaging --show-labels
```

### 3. Deploy Istio Gateway Configuration

```bash
# Install the Istio Gateway Helm chart
helm install istio-gateway ./helm/istio-gateway \
  --namespace omnipdf-prestaging \
  --values ./helm/istio-gateway/values-prestaging.yaml

# Verify Gateway resources
oc get gateway,virtualservice,destinationrule,serviceentry -n omnipdf-prestaging
```

### 4. Deploy OmniPDF Services with Istio

```bash
# Deploy services with prestaging values (includes sidecar injection)
for service in frontend pdf-processor-service pdf-extraction-service embedder-service chromadb redis minio cleaner pdf-extraction-service docling-translation-service pdf-renderer-service image-captioner-service metadata-service; do
  echo "Deploying $service with Istio sidecar..."
  helm install $service ./helm/$service \
    --namespace omnipdf-prestaging \
    --values ./helm/$service/values-prestaging.yaml
done
```

### 5. Configure External Access

```bash
# Get Istio Gateway external IP/hostname
export GATEWAY_HOST=$(oc get route istio-gateway -n istio-system -o jsonpath='{.spec.host}')
echo "OmniPDF will be available at: https://$GATEWAY_HOST"

# Or for local testing
echo "Local access: http://localhost:8080"
```

## Verification

### Check Service Mesh Status

```bash
# Verify all pods have Istio sidecars (should show 2/2 ready)
oc get pods -n omnipdf-prestaging

# Check Istio proxy status  
./istio-1.27.1/bin/istioctl proxy-status -n omnipdf-prestaging

# Verify mTLS is working
./istio-1.27.1/bin/istioctl authn tls-check pdf-processor-service.omnipdf-prestaging.svc.cluster.local
```

### Test Application Access

```bash
# Test through Istio Gateway
curl -H "Host: omnipdf-prestaging.apps-crc.testing" http://$GATEWAY_HOST/health

# Test internal service communication (should use mTLS)
oc exec -n omnipdf-prestaging deployment/pdf-processor-service -c pdf-processor-service -- \
  curl -s http://pdf-extraction-service:8000/health
```

## Architecture Overview

```
External Traffic → Istio Gateway → VirtualService → OmniPDF Services (with Envoy sidecars)
                                                     ↓
                                               mTLS within mesh
```

### Traffic Flow

1. **External** → `https://omnipdf-prestaging.apps-crc.testing`
2. **Istio Gateway** → Routes based on path:
   - `/` → `frontend-service:8501` 
   - `/api/` → `pdf-processor-service:8000`
   - `/pdf_processor/` → `pdf-processor-service:8000`
3. **Service Mesh** → All internal communication uses automatic mTLS

## Troubleshooting

### Common Issues

1. **Sidecar not injected**: Check namespace has `istio-injection=enabled` label
2. **Gateway not accessible**: Verify OpenShift Route is created for istio-gateway
3. **mTLS failures**: Check DestinationRule configurations
4. **High resource usage**: Adjust sidecar resource limits in values files

### Debugging Commands

```bash
# Check Istio configuration
./istio-1.27.1/bin/istioctl analyze -n omnipdf-prestaging

# View sidecar configuration
./istio-1.27.1/bin/istioctl proxy-config cluster -n omnipdf-prestaging pdf-processor-service-xxxx

# Check certificate status
./istio-1.27.1/bin/istioctl authn tls-check -n omnipdf-prestaging
```

## Migration to Organization Istio

For staging/production environments using organization's Istio:

1. **Remove** `istio-gateway` chart deployment
2. **Modify** VirtualService to reference organization's Gateway:
   ```yaml
   gateways:
   - platform/shared-gateway  # Organization's gateway
   ```
3. **Coordinate** with platform team for:
   - Gateway configuration
   - Certificate management  
   - External DNS setup