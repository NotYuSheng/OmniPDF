# CRC Configuration for OmniPDF

This directory contains configuration files and scripts for setting up Red Hat CodeReady Containers (CRC) to run OmniPDF's microservices.

## Quick Setup

### Option 1: Automated Setup (Recommended)
```bash
# Run the setup script to configure CRC
./config/crc/setup-crc.sh

# Start CRC
crc start
```

### Option 2: Manual Configuration
```bash
# Stop CRC if running
crc stop

# Apply configuration manually
crc config set memory 262144    # 256GB RAM
crc config set cpus 32          # 32 CPU cores
crc config set disk-size 80     # 80GB disk
crc config set enable-cluster-monitoring true
crc config set consent-telemetry no

# Start CRC
crc start
```

## Files in this Directory

- `setup-crc.sh` - Automated configuration script
- `README.md` - This file

## Resource Requirements

The configuration assumes you have sufficient system resources:
- **RAM**: At least 256GB+ available system memory
- **CPU**: At least 32+ CPU cores available
- **Disk**: At least 80GB free disk space

Adjust the values in `setup-crc.sh` based on your system capabilities.

## After CRC Starts

1. Set up oc environment:
   ```bash
   eval $(crc oc-env)
   ```

2. Get login credentials:
   ```bash
   crc console --credentials
   ```

3. Login as admin:
   ```bash
   oc login -u kubeadmin -p <password> https://api.crc.testing:6443 --insecure-skip-tls-verify
   ```

4. Deploy OmniPDF services:
   ```bash
   make install-all
   ```