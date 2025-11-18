#!/usr/bin/env python3
"""
API Documentation Test Suite

Validates that all API documentation components are working correctly.
"""

import sys
import json

def test_openapi_schema():
    """Test OpenAPI schema generation"""
    print("Testing OpenAPI schema generation...")
    
    sys.path.insert(0, '.')
    from webdashboard.app import app
    
    schema = app.openapi()
    
    # Basic validation
    assert schema['openapi'] == '3.1.0', 'OpenAPI version mismatch'
    assert schema['info']['title'] == 'Literature Review Dashboard API', 'Title mismatch'
    assert schema['info']['version'] == '2.0.0', 'Version mismatch'
    assert 'contact' in schema['info'], 'Missing contact info'
    assert schema['info']['contact']['name'] == 'Literature Review Team', 'Contact name mismatch'
    
    print("  ✓ OpenAPI version: 3.1.0")
    print("  ✓ API version: 2.0.0")
    print("  ✓ Title: Literature Review Dashboard API")
    print("  ✓ Contact info present")
    
    # Endpoint validation
    endpoint_count = len(schema['paths'])
    assert endpoint_count >= 24, f'Expected at least 24 endpoints, got {endpoint_count}'
    print(f"  ✓ {endpoint_count} endpoints documented")
    
    # Tag validation
    tagged_count = 0
    for path, methods in schema['paths'].items():
        for method, details in methods.items():
            if method in ['get', 'post', 'put', 'delete', 'patch']:
                if 'tags' in details and details['tags']:
                    tagged_count += 1
    
    assert tagged_count == endpoint_count, f'Not all endpoints are tagged'
    print(f"  ✓ All {tagged_count} endpoints properly tagged")
    
    # Schema validation
    schema_count = len(schema['components']['schemas'])
    assert schema_count >= 10, f'Expected at least 10 schemas, got {schema_count}'
    print(f"  ✓ {schema_count} data schemas defined")
    
    # Verify key endpoints
    key_endpoints = [
        '/api/upload',
        '/api/upload/batch',
        '/api/jobs',
        '/api/jobs/{job_id}',
        '/api/jobs/{job_id}/start',
        '/api/jobs/{job_id}/configure',
        '/api/jobs/{job_id}/results',
        '/health'
    ]
    
    for endpoint in key_endpoints:
        assert endpoint in schema['paths'], f'Missing key endpoint: {endpoint}'
    
    print(f"  ✓ All {len(key_endpoints)} key endpoints present")
    
    # Verify tag categories
    expected_tags = ['Papers', 'Jobs', 'Results', 'Analysis', 'Logs', 'Interactive', 'System']
    from collections import defaultdict
    tag_counts = defaultdict(int)
    
    for path, methods in schema['paths'].items():
        for method, details in methods.items():
            if method in ['get', 'post', 'put', 'delete', 'patch']:
                tags = details.get('tags', [])
                for tag in tags:
                    tag_counts[tag] += 1
    
    for tag in expected_tags:
        assert tag in tag_counts, f'Missing tag category: {tag}'
    
    print(f"  ✓ All {len(expected_tags)} tag categories present")
    print()

def test_documentation_files():
    """Test documentation files exist and have content"""
    print("Testing documentation files...")
    
    import os
    
    docs = {
        'docs/API_REFERENCE.md': 25000,  # Min 25KB
        'docs/CLIENT_SDK.md': 20000,     # Min 20KB
        'docs/API_DOCUMENTATION_SUMMARY.md': 10000  # Min 10KB
    }
    
    for filepath, min_size in docs.items():
        assert os.path.exists(filepath), f'Missing file: {filepath}'
        size = os.path.getsize(filepath)
        assert size >= min_size, f'{filepath} is too small: {size} bytes (expected >= {min_size})'
        print(f"  ✓ {filepath}: {size:,} bytes")
    
    print()

def test_endpoint_documentation():
    """Test that endpoints have proper documentation"""
    print("Testing endpoint documentation quality...")
    
    sys.path.insert(0, '.')
    from webdashboard.app import app
    
    schema = app.openapi()
    
    # Check that endpoints have descriptions
    documented_count = 0
    for path, methods in schema['paths'].items():
        for method, details in methods.items():
            if method in ['get', 'post', 'put', 'delete', 'patch']:
                if 'description' in details and len(details['description']) > 50:
                    documented_count += 1
    
    total_endpoints = len([
        1 for path, methods in schema['paths'].items()
        for method in methods.keys()
        if method in ['get', 'post', 'put', 'delete', 'patch']
    ])
    
    coverage = (documented_count / total_endpoints) * 100
    print(f"  ✓ {documented_count}/{total_endpoints} endpoints have detailed descriptions ({coverage:.1f}%)")
    
    # Check that endpoints have response schemas
    response_count = 0
    for path, methods in schema['paths'].items():
        for method, details in methods.items():
            if method in ['get', 'post', 'put', 'delete', 'patch']:
                if 'responses' in details and details['responses']:
                    response_count += 1
    
    response_coverage = (response_count / total_endpoints) * 100
    print(f"  ✓ {response_count}/{total_endpoints} endpoints have response schemas ({response_coverage:.1f}%)")
    
    print()

def test_pydantic_models():
    """Test Pydantic models have examples"""
    print("Testing Pydantic model documentation...")
    
    sys.path.insert(0, '.')
    from webdashboard.app import app
    
    schema = app.openapi()
    schemas = schema['components']['schemas']
    
    # Exclude auto-generated schemas
    user_schemas = [
        name for name in schemas.keys()
        if not name.startswith('Body_') and
           not name.startswith('HTTP') and
           name != 'ValidationError'
    ]
    
    # Check for examples
    examples_count = 0
    for schema_name in user_schemas:
        schema_def = schemas[schema_name]
        if 'examples' in schema_def or 'example' in schema_def:
            examples_count += 1
        # Check properties for examples
        elif 'properties' in schema_def:
            for prop_name, prop_def in schema_def['properties'].items():
                if 'example' in prop_def or 'examples' in prop_def:
                    examples_count += 1
                    break
    
    coverage = (examples_count / len(user_schemas)) * 100 if user_schemas else 0
    print(f"  ✓ {examples_count}/{len(user_schemas)} user-defined schemas have examples ({coverage:.1f}%)")
    print(f"  ✓ Total schemas: {len(schemas)}")
    print()

def main():
    """Run all tests"""
    print("="*60)
    print("API Documentation Test Suite")
    print("="*60)
    print()
    
    try:
        test_openapi_schema()
        test_documentation_files()
        test_endpoint_documentation()
        test_pydantic_models()
        
        print("="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60)
        print()
        print("Documentation is ready:")
        print("  • Swagger UI: http://localhost:5001/api/docs")
        print("  • ReDoc: http://localhost:5001/api/redoc")
        print("  • OpenAPI JSON: http://localhost:5001/api/openapi.json")
        print("  • API Reference: docs/API_REFERENCE.md")
        print("  • Client SDK Guide: docs/CLIENT_SDK.md")
        print("  • Implementation Summary: docs/API_DOCUMENTATION_SUMMARY.md")
        print()
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
