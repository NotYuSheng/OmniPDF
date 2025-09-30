# Scripts Directory

This directory contains testing and security scanning utilities for the OmniPDF project.

## Available Scripts

### 🧪 Unit Testing
- **`test-single-service.sh`** - Run tests for individual services
  - Tests a specific service (e.g., `./test-single-service.sh pdf_extraction_service`)
  - Fast focused testing for development and debugging
  - Uses Docker Compose to ensure proper service isolation
  - Colored output with detailed test progress reporting
- **`test-all-services.sh`** - Run comprehensive test suite across all services
  - Tests all 7 services sequentially with timeout protection
  - Provides complete pass/fail summary with test counts
  - Perfect for CI/CD pipelines and pre-deployment validation
  - Generates individual log files for each service test run

### 🔒 Security Scanning
- **`scan_with_trivy.sh`** - Comprehensive Trivy vulnerability scanner
  - Scans ALL docker-compose services (14 services including infrastructure)
  - Covers both custom OmniPDF images and external images (Redis, ChromaDB, MinIO)
  - Configurable severity levels, output formats, and scan types
  - Generates detailed security reports and timestamped logs
  - Creates organized output in `trivy_scan_results/` directory

## Quick Start

### Running Unit Tests

The unit test script automatically creates and manages its own virtual environment.

```bash
# Test all services - comprehensive test suite
./scripts/test-all-services.sh

# Test specific service - fast individual testing
./scripts/test-single-service.sh pdf_extraction_service
./scripts/test-single-service.sh image_captioner_service

# Manual venv setup (optional - script does this automatically)
python3 -m venv .venv_test
source .venv_test/bin/activate
pip install -r scripts/test-requirements.txt
```

### Running Security Scans

```bash
# Scan ALL services (14 total) for HIGH and CRITICAL vulnerabilities
./scripts/scan_with_trivy.sh

# Fast image-only scan (recommended for regular checks)
./scripts/scan_with_trivy.sh --type image

# Scan specific service (custom or external)
./scripts/scan_with_trivy.sh --service pdf_extraction_service
./scripts/scan_with_trivy.sh --service "redis:7.4.4-alpine"
./scripts/scan_with_trivy.sh --service "chromadb/chroma:1.0.13"

# Scan with custom severity levels
./scripts/scan_with_trivy.sh --severity LOW,MEDIUM,HIGH,CRITICAL

# Generate different output formats
./scripts/scan_with_trivy.sh --format json
./scripts/scan_with_trivy.sh --format sarif

# Combined options
./scripts/scan_with_trivy.sh --type image --severity HIGH,CRITICAL --format table

# Get help and see all available services
./scripts/scan_with_trivy.sh --help
```

## Services Covered

### Security Scanning (14 Services)

**Custom OmniPDF Services (10):**
- **pdf_extraction_service** - PDF content extraction with docling
- **pdf_extraction_service** - PDF processing with docling  
- **docling_translation_service** - Translation with LLM
- **pdf_renderer_service** - PDF rendering with PyMuPDF
- **embedder_service** - Text embedding with ChromaDB
- **pdf_processor_service** - Central PDF coordinator
- **image_captioner_service** - Image captioning with VLM
- **frontend** - Streamlit web interface
- **cleaner** - Background cleanup service
- **nginx** - API gateway and proxy

**External Infrastructure (4):**
- **redis:7.4.4-alpine** - Session storage and caching
- **chromadb/chroma:1.0.13** - Vector database for embeddings
- **minio/minio:RELEASE.2025-07-23T15-54-02Z** - S3-compatible object storage
- **minio/mc:RELEASE.2025-07-21T05-28-08Z** - MinIO client (createbucket service)

### Unit Testing
Unit tests support the 8 main custom services (excludes nginx and cleaner).

## Testing Workflow

### Development Testing Workflow
1. **Individual Service**: `./scripts/test-single-service.sh <service>` - Fast, focused testing during development
2. **Full Test Suite**: `./scripts/test-all-services.sh` - Complete validation before commits
3. **Security Scan**: `./scripts/scan_with_trivy.sh` - Vulnerability assessment

## Requirements

### System Dependencies
```bash
sudo apt update
sudo apt install -y python3-venv python3-pip python3-dev
```

### For Security Scanning
```bash
# Install Trivy
sudo apt-get install wget apt-transport-https gnupg lsb-release
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee -a /etc/apt/sources.list.d/trivy.list
sudo apt-get update && sudo apt-get install trivy
```

## Output Examples

### Unit Tests
**Single Service Testing:**
```
🧪 OmniPDF Unit Test Runner
==========================================
Testing specific service: pdf_extraction_service
🚀 Starting services with docker-compose...
✅ Services started
📦 Testing pdf_extraction_service
========== test session starts ==========
pdf_extraction_service/tests/test_chat.py::TestChatService::test_basic_chat PASSED [50%]
pdf_extraction_service/tests/test_chat.py::TestChatService::test_rag_response PASSED [100%]
========== 20 passed in 2.45s ==========
✅ pdf_extraction_service tests PASSED
🎉 All unit tests passed!
```

**Comprehensive Testing:**
```
🧪 OmniPDF Complete Unit Test Suite
=================================================
📦 Testing pdf_extraction_service
✅ pdf_extraction_service tests PASSED
📦 Testing pdf_extraction_service  
✅ pdf_extraction_service tests PASSED
...
📊 COMPLETE UNIT TEST SUMMARY
pdf_extraction_service: ✅ PASSED (20 tests passed)
pdf_extraction_service: ✅ PASSED (17 tests passed)
...
Final Results: 7/7 services passed
🎉 All unit tests passed!
```

### Security Scan
```
🔒 OmniPDF Trivy Security Scanner
==========================================
✅ Trivy 0.65.0 found

📦 Scanning configuration:
Severity levels: HIGH,CRITICAL
Output format: table
Scan type: image

📋 Services to scan: 14 total
  1. pdf_extraction_service
  2. pdf_extraction_service
  ...
  14. minio/mc:RELEASE.2025-07-21T05-28-08Z

Progress: Scanning service 1/14
🔍 Scanning pdf_extraction_service
✅ pdf_extraction_service: No vulnerabilities found

📊 TRIVY SCAN SUMMARY
pdf_extraction_service: ✅ CLEAN
pdf_extraction_service: ✅ CLEAN
...
minio/mc:RELEASE.2025-07-21T05-28-08Z: ✅ CLEAN

Results: 14/14 services clean
📄 Detailed reports and logs available in: trivy_scan_results/
🎉 All scanned services are clean!
```

## Output Structure

### Security Scan Results

The Trivy scanner creates organized output in the `trivy_scan_results/` directory:

```
trivy_scan_results/
├── [service]-report.txt          # Comprehensive vulnerability scan results
├── [service]-scan.log           # Detailed scan logs with timestamps
└── archive/                    # Previous scan results for comparison
```

**Example files:**
- `pdf_extraction_service-report.txt` - Comprehensive security scan results for extraction service
- `redis:7.4.4-alpine-scan.log` - Timestamped scan log for Redis
- `minio_minio:RELEASE.2025-07-23T15-54-02Z-report.txt` - MinIO scan results

**Report Structure:** Each report file contains:
- Service metadata (name, image, scan date, severity levels)
- Docker image scan results (for all services)
- Filesystem scan results (for custom services with --type all)
- Complete vulnerability details and recommendations

Each log file includes:
- Timestamped scan start/completion entries
- Trivy version and configuration details
- OS and package detection information
- Complete vulnerability analysis output
- Final scan status and results

## Troubleshooting

### Common Issues

**Docker image not found:**
```bash
docker build -t omnipdf-pdf_extraction_service:latest pdf_extraction_service/
```

**Trivy not installed:**
```bash
sudo snap install trivy
```

**Permission denied:**
```bash
chmod +x scripts/*.sh
```