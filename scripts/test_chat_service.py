#!/usr/bin/env python3
"""
Simple integration test for chat_service before/after Trivy hardening.

This script tests that the chat_service works with real dependencies:
- LLM server connectivity  
- Service startup
- API endpoints
- Critical dependencies

Usage:
  python scripts/test_chat_service.py
"""

import os
import sys
import asyncio
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Set environment variables for real services
os.environ.update({
    'OPENAI_BASE_URL': 'http://webworkdgx/vllm_qwen3coder/v1',
    'OPENAI_API_KEY': 'lm-studio',
    'OPENAI_MODEL': 'Qwen3-Coder-30B-A3B-Instruct',
    'MODEL_TOP_K': '5',
    'MODEL_TEMPERATURE': '0.1',
    'MODEL_MAX_TOKENS': '2000',
    'CHROMA_HOST': 'chromadb',
    'CHROMA_PORT': '8000',
})

def test_service_startup():
    """Test that the chat service can start up"""
    try:
        import sys
        import os
        # Add chat_service to path for proper routers import
        chat_service_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'chat_service')
        if chat_service_path not in sys.path:
            sys.path.insert(0, chat_service_path)
        
        from chat_service.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        return True, "Service starts successfully"
    except Exception as e:
        return False, f"Service startup failed: {e}"

def test_dependencies():
    """Test that critical dependencies load"""
    try:
        from chat_service.models.rag_config import RAGConfig, PromptTemplates
        from shared_utils.openai_client import get_openai_client
        from shared_utils.chroma_client import get_chroma_client
        
        config = RAGConfig()
        templates = PromptTemplates()
        return True, "All dependencies load correctly"
    except Exception as e:
        return False, f"Dependency loading failed: {e}"

async def test_llm_connectivity():
    """Test real LLM server connectivity"""
    try:
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(
            base_url='http://webworkdgx/vllm_qwen3coder/v1',
            api_key='lm-studio'
        )
        
        response = await client.chat.completions.create(
            model='Qwen3-Coder-30B-A3B-Instruct',
            messages=[
                {'role': 'system', 'content': 'You are a helpful assistant.'},
                {'role': 'user', 'content': 'What is 2+2?'}
            ],
            max_tokens=10,
            temperature=0.1
        )
        
        result = response.choices[0].message.content.strip()
        return True, f'LLM responded: "{result}"'
    except Exception as e:
        return False, f"LLM connectivity failed: {e}"

def test_api_endpoints():
    """Test that API endpoints work"""
    try:
        import sys
        import os
        # Add chat_service to path for proper routers import
        chat_service_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'chat_service')
        if chat_service_path not in sys.path:
            sys.path.insert(0, chat_service_path)
        
        from chat_service.main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        response = client.get('/health')
        return True, f"Health endpoint accessible (Status: {response.status_code})"
    except Exception as e:
        return False, f"Endpoint test failed: {e}"

def test_ml_stack():
    """Test that ML dependencies are available"""
    try:
        import chromadb
        import sentence_transformers
        import torch
        import numpy
        return True, "ML stack (ChromaDB, Transformers, PyTorch) available"
    except Exception as e:
        return False, f"ML stack test failed: {e}"

async def run_all_tests():
    """Run all integration tests"""
    print('🔒 CHAT SERVICE INTEGRATION TESTS')
    print('=' * 50)
    
    tests = [
        ("🚀 Service Startup", test_service_startup),
        ("📦 Dependencies", test_dependencies),
        ("🤖 LLM Connectivity", test_llm_connectivity),
        ("🌐 API Endpoints", test_api_endpoints),
        ("🧠 ML Stack", test_ml_stack),
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_func in tests:
        print(f'\n{name}...')
        try:
            if asyncio.iscoroutinefunction(test_func):
                success, message = await test_func()
            else:
                success, message = test_func()
            
            if success:
                print(f'   ✅ {message}')
                passed += 1
            else:
                print(f'   ❌ {message}')
        except Exception as e:
            print(f'   ❌ Test failed with exception: {e}')
    
    print(f'\n📊 RESULTS: {passed}/{total} tests passed')
    print('=' * 50)
    
    if passed == total:
        print('🎉 ALL TESTS PASSED!')
        print('🔒 chat_service is ready for Trivy hardening!')
        return True
    else:
        print('🚨 SOME TESTS FAILED!')
        print('🛑 Fix issues before proceeding with Trivy hardening!')
        return False

def main():
    """Main entry point"""
    try:
        # Add project root to Python path
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, project_root)
        os.environ['PYTHONPATH'] = project_root + ':' + os.environ.get('PYTHONPATH', '')
        
        # Run tests
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print('\n🛑 Tests interrupted by user')
        sys.exit(1)
    except Exception as e:
        print(f'🚨 Test runner failed: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()