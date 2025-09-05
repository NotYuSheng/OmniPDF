#!/bin/bash
# CRC Setup Script for OmniPDF
# This script configures CRC with optimal settings for running OmniPDF microservices

set -e

echo "Setting up CRC configuration for OmniPDF..."

# Stop CRC if running
echo "Stopping CRC if running..."
crc stop 2>/dev/null || true

# Configure CRC resources
echo "Configuring CRC resources..."
crc config set memory 262144    # 256GB RAM
crc config set cpus 32          # 32 CPU cores  
crc config set disk-size 80     # 80GB disk
crc config set enable-cluster-monitoring true
crc config set consent-telemetry no

echo "CRC configuration completed!"
echo ""
echo "Current configuration:"
crc config view
echo ""
echo "To start CRC with these settings, run:"
echo "  crc start"
echo ""
echo "After CRC starts, set up oc environment:"
echo "  eval \$(crc oc-env)"
echo "  crc console --credentials  # Get login credentials"