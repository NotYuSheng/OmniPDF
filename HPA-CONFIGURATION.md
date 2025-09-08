# Horizontal Pod Autoscaler (HPA) Configuration

## Overview

HPA automatically scales the number of pods based on CPU and memory utilization metrics to handle varying workloads efficiently.

## Services WITH HPA Enabled (6 services)

| **Service** | **Min Replicas** | **Max Replicas** | **CPU Target** | **Memory Target** | **Scaling Strategy** |
|-------------|------------------|------------------|----------------|-------------------|---------------------|
| chat-service | 2 | 10 | 70% | 80% | High demand during chat interactions |
| docling-translation-service | 2 | 10 | 70% | 80% | Scales with translation workload |
| pdf-processor-service | 2 | 8 | 70% | 80% | Main orchestrator - handles all requests |
| pdf-extraction-service | 2 | 10 | 70% | 80% | CPU-intensive PDF processing |
| pdf-renderer-service | 2 | 10 | 70% | 80% | Scales with rendering requests |
| nginx | 2 | 10 | 70% | 80% | API gateway - handles all external traffic |

## Services WITH HPA Disabled (8 services)

| **Service** | **Status** | **Min/Max Replicas** | **Reason for Disabling** |
|-------------|-----------|---------------------|--------------------------|
| redis | `enabled: false` | 1/3 | **Stateful service** - Redis clustering is complex, typically single instance |
| chromadb | `enabled: false` | 1/3 | **Vector database** - Stateful, requires careful scaling coordination |
| frontend | `enabled: false` | 1/3 | **Streamlit app** - Single instance sufficient, stateful sessions |
| cleaner | `enabled: false` | N/A | **Background worker** - Single scheduled job, no need to scale |
| minio | `enabled: false` | 1/3 | **Object storage** - Single-node deployment, stateful storage |
| embedder-service | `enabled: false` | 1/5 | Not explicitly stated - likely low/predictable load |
| metadata-service | `enabled: false` | 1/3 | Disabled by default - likely infrequent usage |
| image-captioner-service | `enabled: false` | 1/3 | Disabled by default for VLM service - expensive operations |

## HPA Configuration Details

### Standard Thresholds
- **CPU Target**: 70% utilization (most services)
- **Memory Target**: 80% utilization (most services)
- **Scaling Frequency**: Every 15 seconds (Kubernetes default)
- **Cooldown Period**: 3-5 minutes between scale events

### Replica Strategy
- **High Availability**: Minimum 2 replicas for critical services
- **Load Distribution**: Maximum 8-10 replicas for reasonable resource bounds
- **Cost Optimization**: Services start at minimum replicas during low load

## Service Categories

### **1. Auto-Scaling Services (Traffic-Dependent)**
**Services**: nginx, chat-service, pdf-processor-service
- Handle user traffic directly
- Need to scale with concurrent users
- High availability requirements

### **2. Processing Services (Workload-Dependent)**  
**Services**: pdf-extraction-service, docling-translation-service, pdf-renderer-service
- Scale based on processing queue depth
- CPU/Memory intensive operations
- Can have bursts during bulk processing

### **3. Stateful Services (No Scaling)**
**Services**: redis, chromadb, minio
- Maintain persistent state
- Complex clustering requirements
- Typically single instance or manual scaling

### **4. Utility Services (Low/Predictable Load)**
**Services**: embedder-service, metadata-service, image-captioner-service, frontend, cleaner
- Predictable or infrequent usage patterns
- Either expensive operations or simple functionality
- Manual scaling sufficient

## Monitoring and Tuning

### Key Metrics to Watch
- **Pod CPU/Memory utilization** across services
- **Request latency** during scaling events
- **Queue depth** for processing services
- **Scale-up/scale-down frequency**

### Common Tuning Scenarios

**Scale Too Aggressively:**
- Increase CPU/Memory thresholds (70% → 80%)
- Reduce maximum replicas

**Scale Too Slowly:**
- Decrease thresholds (70% → 60%)
- Reduce cooldown periods (advanced configuration)

**Resource Waste:**
- Lower minimum replicas for less critical services
- Implement custom metrics (requests/second vs CPU)

## Production Recommendations

### **Consider Enabling HPA For:**
1. **embedder-service**: If document ingestion has spikes
2. **metadata-service**: If metadata generation becomes frequent

### **Advanced Configuration:**
```yaml
# Example: Custom metrics for API services
metrics:
- type: Pods
  pods:
    metric:
      name: http_requests_per_second
    target:
      type: AverageValue
      averageValue: "100"
```

### **Multi-Metric Scaling:**
Most services use both CPU and Memory metrics. HPA scales based on whichever metric suggests more replicas needed.

## Troubleshooting

### Common Issues
1. **HPA not scaling**: Check if metrics-server is running
2. **Frequent scaling**: Adjust thresholds or cooldown periods  
3. **Resource requests missing**: HPA requires resource requests to be defined
4. **Scale-down stuck**: Check PodDisruptionBudget settings

### Debug Commands
```bash
# Check HPA status
kubectl get hpa -n omnipdf

# Detailed HPA information
kubectl describe hpa chat-service-hpa -n omnipdf

# Check current CPU/Memory usage
kubectl top pods -n omnipdf
```

## Cost Optimization

### Current Resource Allocation
- **Minimum pods running**: ~13 pods (assuming all minimums)
- **Maximum pods possible**: ~63 pods (if all services scale to max)
- **Typical running state**: 15-20 pods under normal load

### Optimization Strategies
1. **Profile actual usage** before adjusting min/max replicas
2. **Use Vertical Pod Autoscaler (VPA)** for right-sizing resources
3. **Consider cluster autoscaler** for node-level scaling
4. **Implement graceful degradation** for non-critical services during high load