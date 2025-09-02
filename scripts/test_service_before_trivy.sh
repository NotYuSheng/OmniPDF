#!/bin/bash

# Script to test individual OmniPDF services before Trivy hardening
# Run this BEFORE and AFTER Trivy to ensure service functionality is preserved

if [ -z "$1" ]; then
    echo "🔒 Testing OmniPDF service before Trivy hardening..."
    echo "❌ Please specify a service name!"
    echo ""
    echo "Available services:"
    echo "  - chat_service"
    echo "  - pdf_extraction_service" 
    echo "  - docling_translation_service"
    echo "  - pdf_renderer_service"
    echo "  - embedder_service"
    echo "  - pdf_processor_service"
    echo "  - image_captioner_service"
    echo ""
    echo "Usage: ./scripts/test_service_before_trivy.sh <service_name>"
    echo "Example: ./scripts/test_service_before_trivy.sh chat_service"
    exit 1
fi

echo "🔒 Testing $1 before Trivy hardening..."
echo ""

# Activate virtual environment if it exists
if [ -d "/home/ubuntu/Desktop/OmniPDF/.venv_integration" ]; then
    echo "📦 Using existing virtual environment..."
    source /home/ubuntu/Desktop/OmniPDF/.venv_integration/bin/activate
else
    echo "❌ Virtual environment not found!"
    echo "Please run: python3 -m venv .venv_integration && source .venv_integration/bin/activate"
    echo "Then install dependencies for the services you want to test"
    exit 1
fi

# Set Python path and run tests
export PYTHONPATH="/home/ubuntu/Desktop/OmniPDF:$PYTHONPATH"
cd /home/ubuntu/Desktop/OmniPDF

echo "Testing service: $1"
python /home/ubuntu/Desktop/OmniPDF/scripts/test_all_services.py --service $1

echo ""
echo "💡 After Trivy hardening, run this same script to verify functionality!"
echo "Usage: ./scripts/test_service_before_trivy.sh <service_name>"