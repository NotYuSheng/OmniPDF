#!/bin/bash

# Simple script to test chat_service before Trivy hardening
# Run this BEFORE and AFTER Trivy to ensure functionality is preserved

echo "🔒 Testing chat_service before Trivy hardening..."
echo ""

# Activate virtual environment if it exists
if [ -d "/home/ubuntu/Desktop/OmniPDF/.venv_integration" ]; then
    echo "📦 Using existing virtual environment..."
    source /home/ubuntu/Desktop/OmniPDF/.venv_integration/bin/activate
else
    echo "❌ Virtual environment not found!"
    echo "Please run: python3 -m venv .venv_integration && source .venv_integration/bin/activate && pip install -r chat_service/requirements.txt"
    exit 1
fi

# Set Python path and run tests
export PYTHONPATH="/home/ubuntu/Desktop/OmniPDF:$PYTHONPATH"
cd /home/ubuntu/Desktop/OmniPDF
python /home/ubuntu/Desktop/OmniPDF/scripts/test_chat_service.py

echo ""
echo "💡 After Trivy hardening, run this same script to verify functionality!"