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
crc config set memory 32768     # 32GB RAM (adjust based on your system)
crc config set cpus 12          # 12 CPU cores (adjust based on your system)  
crc config set disk-size 120    # 120GB disk (increased for ML workloads)
crc config set enable-cluster-monitoring true
crc config set consent-telemetry no

# Check if CRC VM exists and needs recreation for disk size changes
echo ""
echo "⚠️  Note: CRC disk-size changes require VM recreation if CRC was already created"
echo "If you have an existing CRC VM and need more disk space, run:"
echo "  crc delete"
echo "  crc start"

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
echo ""
echo "💡 For OmniPDF ML workloads, consider:"
echo "  - Regular docker system prune to clean up unused images"
echo "  - Monitor disk usage with: crc status"
echo "  - If disk fills up, delete and recreate CRC with larger disk-size"
echo ""
echo "🧹 To clean up Docker space:"
echo "  docker system prune -f"
echo "  docker image prune -a -f"