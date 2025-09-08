# HPA Strategy Analysis & Recommendations

## Current State Analysis (14 Services Total)

### ✅ Services WITH HPA Enabled (6 services)
| Service | Current Config | Assessment |
|---------|---------------|------------|
| nginx | 2-10 replicas, 70% CPU, 80% Memory | ✅ **CORRECT** - API gateway handles all traffic |
| chat-service | 2-10 replicas, 70% CPU, 80% Memory | ✅ **CORRECT** - User-facing interactions |
| pdf-processor-service | 2-8 replicas, 70% CPU, 80% Memory | ✅ **CORRECT** - Main orchestrator |
| docling-translation-service | 2-10 replicas, 70% CPU, 80% Memory | ✅ **CORRECT** - LLM calls can burst |
| pdf-extraction-service | 2-10 replicas, 70% CPU, 80% Memory | ✅ **CORRECT** - CPU-intensive processing |
| pdf-renderer-service | 2-10 replicas, 70% CPU, 80% Memory | ✅ **CORRECT** - PDF rendering workload |

### ❌ Services WITHOUT HPA (8 services)

#### 🔄 SHOULD ENABLE HPA (3 services)
| Service | Why Enable HPA | Recommended Config |
|---------|---------------|-------------------|
| **embedder-service** | Text chunking/embedding can have document upload spikes | 1-5 replicas, 70% CPU, 80% Memory |
| **image-captioner-service** | Lightweight HTTP client, can handle concurrent requests | 1-5 replicas, 70% CPU, 80% Memory |
| **metadata-service** | Word cloud generation can have traffic bursts | 1-5 replicas, 70% CPU, 80% Memory |

#### ✅ CORRECTLY DISABLED (4 services)
| Service | Why NO HPA | Reasoning |
|---------|------------|-----------|
| **redis** | Stateful service | Complex clustering, typically single instance |
| **chromadb** | Stateful vector database | Requires careful scaling coordination |
| **minio** | Stateful object storage | Single-node deployment, stateful storage |
| **cleaner** | Event-driven background service | Single instance sufficient for Redis pub/sub |

#### 🤔 OPTIONAL/FUTURE (1 service)
| Service | Status | Reasoning |
|---------|--------|-----------|
| **frontend** | Could enable later | Streamlit app - single instance often sufficient, but could scale for multiple users |

---

## Recommended HPA Strategy (9 Services Total)

### **Tier 1: Critical User-Facing (Aggressive Scaling)**
Services that directly impact user experience - scale proactively:

| Service | Replicas | CPU Threshold | Memory Threshold | Priority |
|---------|----------|---------------|------------------|----------|
| nginx | 2-15 | **60%** ⬇️ | **70%** ⬇️ | **CRITICAL** |
| pdf-processor-service | 2-10 | **60%** ⬇️ | **70%** ⬇️ | **CRITICAL** |
| chat-service | 2-10 | 70% | 80% | **HIGH** |

### **Tier 2: Processing Workload (Standard Scaling)**  
Services handling document processing - scale with workload:

| Service | Replicas | CPU Threshold | Memory Threshold | Priority |
|---------|----------|---------------|------------------|----------|
| pdf-extraction-service | 2-8 | 70% | 80% | **HIGH** |
| docling-translation-service | 2-8 | 70% | 80% | **HIGH** |
| pdf-renderer-service | 2-8 | 70% | 80% | **HIGH** |

### **Tier 3: Burst Services (Conservative Scaling)**
Services with occasional traffic spikes - enable but conservative:

| Service | Replicas | CPU Threshold | Memory Threshold | Priority |
|---------|----------|---------------|------------------|----------|
| embedder-service | 1-5 | 70% | 80% | **MEDIUM** |
| image-captioner-service | 1-5 | 70% | 80% | **MEDIUM** |  
| metadata-service | 1-5 | 70% | 80% | **MEDIUM** |

---

## Key Changes Recommended

### **Enable HPA for 3 Additional Services:**

1. **embedder-service**: 
   - **Why**: Document upload spikes can cause text processing bursts
   - **Impact**: Better handling of bulk document ingestion

2. **image-captioner-service**:
   - **Why**: Lightweight HTTP client can handle many concurrent VLM requests  
   - **Impact**: Better concurrency for image captioning workflows

3. **metadata-service**:
   - **Why**: Word cloud generation can have traffic bursts during document analysis
   - **Impact**: Better responsiveness for metadata generation

### **Optimize Existing HPA Thresholds:**

1. **nginx**: Lower thresholds to 60% CPU, 70% Memory (more aggressive scaling)
2. **pdf-processor-service**: Lower thresholds to 60% CPU, 70% Memory (more aggressive scaling)
3. **pdf-processor-service**: Increase max replicas from 8 to 10 for higher capacity

---

## Resource & Cost Impact

### **Current Setup:**
- **Minimum pods**: ~13 pods (6 services × 2 replicas + 1 replica services)
- **Maximum pods**: ~58 pods (if all HPA services scale to max)

### **Recommended Setup:**  
- **Minimum pods**: ~16 pods (9 services × ~2 avg replicas)
- **Maximum pods**: ~73 pods (if all HPA services scale to max)
- **Typical load**: 18-25 pods under normal traffic

### **Benefits:**
- Better handling of document processing bursts
- Improved user experience during traffic spikes  
- More granular resource allocation
- Better cost efficiency (pay for what you use)

---

## Implementation Priority

### **Phase 1 (High Priority):**
1. Enable HPA for embedder-service, image-captioner-service, metadata-service
2. Optimize nginx and pdf-processor-service thresholds

### **Phase 2 (Future):**
1. Consider frontend HPA based on user growth
2. Monitor and tune thresholds based on actual usage patterns
3. Implement custom metrics (requests/sec) for more accurate scaling

### **Monitoring Requirements:**
- Track HPA scaling events and frequency
- Monitor service response times during scaling
- Analyze cost impact vs performance gains
- Set up alerts for frequent scaling oscillations