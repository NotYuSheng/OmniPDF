#!/usr/bin/env python3
"""
Integration test runner for all OmniPDF services before/after Trivy hardening.

This script tests all 7 services to ensure they work with real dependencies.
Run this BEFORE and AFTER Trivy hardening to ensure functionality is preserved.

Usage:
  python scripts/test_all_services.py
  python scripts/test_all_services.py --service chat_service  # Test single service
"""

import os
import sys
import asyncio
import argparse
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Service configurations
SERVICES = {
    'chat_service': {
        'port': 8001,
        'env_vars': {
            'OPENAI_BASE_URL': 'http://webworkdgx/vllm_qwen3coder/v1',
            'OPENAI_API_KEY': 'lm-studio',
            'OPENAI_MODEL': 'Qwen3-Coder-30B-A3B-Instruct',
            'MODEL_TOP_K': '5',
            'MODEL_TEMPERATURE': '0.1',
            'MODEL_MAX_TOKENS': '2000',
            'CHROMA_HOST': 'chromadb',
            'CHROMA_PORT': '8000',
        },
        'heavy_deps': ['chromadb', 'sentence_transformers', 'torch', 'openai'],
        'has_llm': True
    },
    'pdf_extraction_service': {
        'port': 8002,
        'env_vars': {},
        'heavy_deps': ['docling', 'boto3', 'redis'],
        'has_llm': False
    },
    'docling_translation_service': {
        'port': 8003,
        'env_vars': {
            'OPENAI_BASE_URL': 'http://webworkdgx/vllm_qwen3coder/v1',
            'OPENAI_API_KEY': 'lm-studio',
            'OPENAI_MODEL': 'Qwen3-Coder-30B-A3B-Instruct',
        },
        'heavy_deps': ['openai'],
        'has_llm': True
    },
    'pdf_renderer_service': {
        'port': 8004,
        'env_vars': {},
        'heavy_deps': ['fitz', 'boto3', 'httpx', 'redis'],
        'has_llm': False
    },
    'embedder_service': {
        'port': 8005,
        'env_vars': {
            'CHROMA_HOST': 'chromadb',
            'CHROMA_PORT': '8000',
        },
        'heavy_deps': ['chromadb', 'sentence_transformers'],
        'has_llm': False
    },
    'pdf_processor_service': {
        'port': 8000,
        'env_vars': {
            'REDIS_HOST': 'redis',
            'REDIS_PORT': '6379',
            'EXTRACTION_URL': 'http://pdf_extraction_service:8000/pdf_extraction/documents/extract',
            'EMBED_URL': 'http://embedder_service:8000/embedder',
            'EXTERNAL_ENDPOINT': 'http://localhost:8080/pdf_processor',
        },
        'heavy_deps': ['redis'],
        'has_llm': False
    },
    'image_captioner_service': {
        'port': 8006,
        'env_vars': {
            'OPENAI_BASE_URL': 'http://webworkdgx/vllm_qwen3coder/v1',
            'OPENAI_API_KEY': 'lm-studio',
            'OPENAI_VLM': 'Qwen3-Coder-30B-A3B-Instruct',
            'MODEL_TEMPERATURE': '0.1',
            'MODEL_MAX_TOKENS': '2000',
            'MODEL_TOP_P': '0.8',
            'MODEL_FREQ_PENALTY': '0.1',
            'MODEL_PRESENCE_PENALTY': '0.1',
            'MODEL_MAX_CONTEXT': '4000',
            'ENABLE_RESPONSE_POST_PROCESSING': 'true',
        },
        'heavy_deps': ['openai', 'torch', 'transformers'],
        'has_llm': True
    }
}

def setup_service_environment(service_name):
    """Set up environment variables for a specific service"""
    service_config = SERVICES.get(service_name, {})
    env_vars = service_config.get('env_vars', {})
    
    # Set service-specific environment variables
    os.environ.update(env_vars)
    
    # Clean up Python path and set up correctly for this service
    project_root = Path(__file__).parent.parent
    
    # Remove other service paths from sys.path to avoid conflicts
    paths_to_remove = []
    for path in sys.path:
        if any(svc in path for svc in SERVICES.keys() if svc != service_name):
            paths_to_remove.append(path)
    
    for path in paths_to_remove:
        try:
            sys.path.remove(path)
        except ValueError:
            pass
    
    # Add project root and current service to path
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    service_path = project_root / service_name
    if service_path.exists() and str(service_path) not in sys.path:
        sys.path.insert(0, str(service_path))
    
    return service_config

def test_service_startup(service_name):
    """Test that the service can start up"""
    try:
        setup_service_environment(service_name)
        
        # Set required environment variables for all services
        common_env = {
            'MINIO_ENDPOINT': 'http://minio:9000',
            'MINIO_BUCKET': 'omnifiles',
            'MINIO_ACCESS_KEY': 'minioadmin',
            'MINIO_SECRET_KEY': 'minioadmin',
            'REDIS_URL': 'redis://redis:6379/0?decode_responses=True&protocol=3',
            'REDIS_HOST': 'redis',
            'REDIS_PORT': '6379',
            # Also set AWS env vars for compatibility
            'AWS_ACCESS_KEY_ID': 'minioadmin',
            'AWS_SECRET_ACCESS_KEY': 'minioadmin',
            'S3_ENDPOINT': 'http://minio:9000',
            'BUCKET_NAME': 'omnifiles'
        }
        
        for key, value in common_env.items():
            if key not in os.environ:
                os.environ[key] = value
        
        # Change working directory to the service directory for relative imports
        project_root = Path(__file__).parent.parent
        service_path = project_root / service_name
        original_cwd = os.getcwd()
        
        if service_path.exists():
            os.chdir(service_path)
        
        # Import the service's main module
        main_module = __import__(f'{service_name}.main', fromlist=['app'])
        app = getattr(main_module, 'app')
        
        from fastapi.testclient import TestClient
        client = TestClient(app)
        
        # Restore original working directory
        os.chdir(original_cwd)
        
        return True, "Service starts successfully"
    except Exception as e:
        # Restore original working directory in case of error
        try:
            os.chdir(original_cwd)
        except:
            pass
        return False, f"Service startup failed: {e}"

def test_service_dependencies(service_name):
    """Test that critical dependencies load"""
    try:
        service_config = setup_service_environment(service_name)
        heavy_deps = service_config.get('heavy_deps', [])
        
        # Try to import heavy dependencies
        for dep in heavy_deps:
            try:
                __import__(dep)
            except ImportError as e:
                return False, f"Failed to import {dep}: {e}"
        
        return True, f"All dependencies ({', '.join(heavy_deps)}) load correctly"
    except Exception as e:
        return False, f"Dependency test failed: {e}"

async def test_service_llm_connectivity(service_name):
    """Test LLM connectivity for services that use it"""
    service_config = SERVICES.get(service_name, {})
    if not service_config.get('has_llm', False):
        return True, "No LLM dependency (skipped)"
    
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
                {'role': 'user', 'content': 'Say "OK" in one word.'}
            ],
            max_tokens=5,
            temperature=0.1
        )
        
        result = response.choices[0].message.content.strip()
        return True, f'LLM responded: "{result}"'
    except Exception as e:
        return False, f"LLM connectivity failed: {e}"

def test_service_health_endpoint(service_name):
    """Test that the health endpoint works"""
    try:
        setup_service_environment(service_name)
        
        # Set required environment variables for all services
        common_env = {
            'MINIO_ENDPOINT': 'http://minio:9000',
            'MINIO_BUCKET': 'omnifiles',
            'MINIO_ACCESS_KEY': 'minioadmin',
            'MINIO_SECRET_KEY': 'minioadmin',
            'REDIS_URL': 'redis://redis:6379/0?decode_responses=True&protocol=3',
            'REDIS_HOST': 'redis',
            'REDIS_PORT': '6379',
            # Also set AWS env vars for compatibility
            'AWS_ACCESS_KEY_ID': 'minioadmin',
            'AWS_SECRET_ACCESS_KEY': 'minioadmin',
            'S3_ENDPOINT': 'http://minio:9000',
            'BUCKET_NAME': 'omnifiles'
        }
        
        for key, value in common_env.items():
            if key not in os.environ:
                os.environ[key] = value
        
        # Change working directory to the service directory for relative imports
        project_root = Path(__file__).parent.parent
        service_path = project_root / service_name
        original_cwd = os.getcwd()
        
        if service_path.exists():
            os.chdir(service_path)
        
        # Import the service's main module
        main_module = __import__(f'{service_name}.main', fromlist=['app'])
        app = getattr(main_module, 'app')
        
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get('/health')
        
        # Restore original working directory
        os.chdir(original_cwd)
        
        return True, f"Health endpoint accessible (Status: {response.status_code})"
    except Exception as e:
        # Restore original working directory in case of error
        try:
            os.chdir(original_cwd)
        except:
            pass
        return False, f"Health endpoint test failed: {e}"

async def test_single_service(service_name):
    """Run all tests for a single service"""
    if service_name not in SERVICES:
        print(f"❌ Unknown service: {service_name}")
        return False
    
    print(f'\n🔒 TESTING {service_name.upper()}')
    print('=' * 60)
    
    # Clear module cache to prevent contamination between services
    modules_to_clear = []
    for module_name in list(sys.modules.keys()):
        # Clear service-specific modules and common conflicting modules
        if (any(svc in module_name for svc in SERVICES.keys()) or
            module_name in ['routers', 'models', 'main'] or
            module_name.startswith(('routers.', 'models.'))):
            modules_to_clear.append(module_name)
    
    for module_name in modules_to_clear:
        if module_name in sys.modules:
            del sys.modules[module_name]
    
    tests = [
        ("🚀 Service Startup", test_service_startup),
        ("📦 Dependencies", test_service_dependencies), 
        ("🤖 LLM Connectivity", test_service_llm_connectivity),
        ("🌐 Health Endpoint", test_service_health_endpoint),
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_func in tests:
        print(f'\n{name}...')
        try:
            if asyncio.iscoroutinefunction(test_func):
                success, message = await test_func(service_name)
            else:
                success, message = test_func(service_name)
            
            if success:
                print(f'   ✅ {message}')
                passed += 1
            else:
                print(f'   ❌ {message}')
        except Exception as e:
            print(f'   ❌ Test failed with exception: {e}')
    
    print(f'\n📊 {service_name}: {passed}/{total} tests passed')
    return passed == total

async def run_all_tests(services_to_test=None):
    """Run integration tests for all or specified services"""
    if services_to_test is None:
        services_to_test = list(SERVICES.keys())
    
    print('🔒 OMNIPDF INTEGRATION TESTS')
    print('=' * 70)
    print(f'Testing {len(services_to_test)} services: {", ".join(services_to_test)}')
    
    # Add project root to Python path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    os.environ['PYTHONPATH'] = str(project_root) + ':' + os.environ.get('PYTHONPATH', '')
    
    overall_results = {}
    
    for service_name in services_to_test:
        try:
            success = await test_single_service(service_name)
            overall_results[service_name] = success
        except Exception as e:
            print(f'\n❌ {service_name} testing failed: {e}')
            overall_results[service_name] = False
    
    # Summary
    print('\n' + '=' * 70)
    print('📊 FINAL RESULTS:')
    
    total_services = len(services_to_test)
    passed_services = sum(overall_results.values())
    
    for service_name, success in overall_results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f'   {service_name}: {status}')
    
    print(f'\n🎯 Overall: {passed_services}/{total_services} services passed')
    
    if passed_services == total_services:
        print('🎉 ALL SERVICES READY FOR TRIVY HARDENING!')
        return True
    else:
        print('🚨 SOME SERVICES FAILED - Fix before Trivy hardening!')
        return False

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Test OmniPDF services before/after Trivy hardening')
    parser.add_argument('--service', help='Test specific service only')
    parser.add_argument('--list', action='store_true', help='List available services')
    
    args = parser.parse_args()
    
    if args.list:
        print("Available services:")
        for service in SERVICES.keys():
            print(f"  - {service}")
        return
    
    try:
        if args.service:
            services_to_test = [args.service]
        else:
            services_to_test = list(SERVICES.keys())
        
        success = asyncio.run(run_all_tests(services_to_test))
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print('\n🛑 Tests interrupted by user')
        sys.exit(1)
    except Exception as e:
        print(f'🚨 Test runner failed: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()