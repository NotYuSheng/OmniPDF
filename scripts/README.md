# Scripts Directory

This directory contains utility scripts for the OmniPDF project.

## Files

### 🧪 Testing Scripts
- **`run_tests.sh`** - Main test runner for all microservices
- **`test-requirements.txt`** - Testing dependencies for all services
- **`test_runner_demo.py`** - Demo script to verify test runner functionality

## Usage

### Running Tests

```bash
# From project root directory

# Run all service tests
./scripts/run_tests.sh

# Run specific service tests
./scripts/run_tests.sh chat_service

# Test the test runner itself
python ./scripts/test_runner_demo.py
```

### Test Runner Features

The test runner (`run_tests.sh`) provides:
- ✅ **Virtual environment isolation** - Creates clean test environment
- 📦 **Automatic dependency management** - Installs all required packages
- 🔄 **Service discovery** - Automatically finds and tests all services
- 📊 **Comprehensive reporting** - Shows passed/failed tests with summary
- 🧹 **Automatic cleanup** - Removes test environment after completion

### Requirements

Ensure you have the required system packages:
```bash
sudo apt update
sudo apt install -y python3.12-venv python3-pip python3-dev
```

## Script Organization

Test-related files have been moved to this `scripts/` directory to keep the project root clean while maintaining easy access to testing tools.