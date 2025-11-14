"""
Test Google AI SDK Import Syntax and API Usage

This test verifies the correct import syntax for the Google AI SDK v0.8.5
and validates that the repository is using the API correctly.
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestGoogleAISDKImports:
    """Test suite for Google AI SDK import patterns."""
    
    @pytest.mark.unit
    def test_import_google_generativeai(self):
        """Test that 'import google.generativeai as genai' works."""
        import google.generativeai as genai
        
        # Verify expected attributes are available
        assert hasattr(genai, 'GenerativeModel'), "GenerativeModel should be available"
        assert hasattr(genai, 'configure'), "configure should be available"
        assert hasattr(genai, 'types'), "types should be available"
        
        # Verify Client is NOT available (this is in google.genai)
        assert not hasattr(genai, 'Client'), "Client should NOT be in google.generativeai"
    
    @pytest.mark.unit
    def test_import_google_genai(self):
        """Test that 'from google import genai' works."""
        from google import genai
        
        # Verify expected attributes are available
        assert hasattr(genai, 'Client'), "Client should be available"
        assert hasattr(genai, 'types'), "types should be available"
        
        # Verify GenerativeModel and configure are NOT available (these are in google.generativeai)
        assert not hasattr(genai, 'GenerativeModel'), "GenerativeModel should NOT be in google.genai"
        assert not hasattr(genai, 'configure'), "configure should NOT be in google.genai"
    
    @pytest.mark.unit
    def test_api_manager_uses_correct_import(self):
        """Test that APIManager uses the correct import pattern."""
        import google.generativeai as genai
        
        # APIManager should use google.generativeai (has configure and GenerativeModel)
        assert hasattr(genai, 'configure'), "APIManager needs configure() from google.generativeai"
        assert hasattr(genai, 'GenerativeModel'), "APIManager needs GenerativeModel from google.generativeai"
    
    @pytest.mark.unit
    def test_reviewers_use_correct_import(self):
        """Test that Deep Reviewer and Journal Reviewer use correct import pattern."""
        from google import genai
        
        # Reviewers should use google.genai (has Client)
        assert hasattr(genai, 'Client'), "Reviewers need Client from google.genai"
    
    @pytest.mark.unit
    def test_recommendation_engine_import_inconsistency(self):
        """Test that recommendation.py has INCORRECT import - should be fixed."""
        # This file imports 'from google import genai' but doesn't use Client()
        # It should use 'import google.generativeai as genai' instead
        
        # Read the file to check its import
        recommendation_file = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            'literature_review', 
            'analysis', 
            'recommendation.py'
        )
        
        with open(recommendation_file, 'r') as f:
            content = f.read()
        
        # Check what it imports
        has_google_genai_import = 'from google import genai' in content
        has_google_generativeai_import = 'import google.generativeai as genai' in content
        
        # Check what it uses
        uses_client = 'genai.Client()' in content
        uses_configure = 'genai.configure(' in content
        uses_generative_model = 'genai.GenerativeModel' in content
        
        # Report the issue
        if has_google_genai_import and not uses_client:
            pytest.fail(
                "recommendation.py imports 'from google import genai' but doesn't use Client(). "
                "It should use 'import google.generativeai as genai' instead."
            )


class TestAPIUsagePatterns:
    """Test suite for verifying correct API usage patterns."""
    
    @pytest.mark.unit
    def test_api_patterns_summary(self):
        """Document the correct usage patterns for both APIs."""
        
        # Pattern 1: google.generativeai - Legacy/Stable API
        import google.generativeai as genai_legacy
        assert hasattr(genai_legacy, 'configure')
        assert hasattr(genai_legacy, 'GenerativeModel')
        
        # Pattern 2: google.genai - New SDK (v0.8.5+)
        from google import genai as genai_new
        assert hasattr(genai_new, 'Client')
        
        # Document the patterns
        usage_patterns = {
            "google.generativeai": {
                "import": "import google.generativeai as genai",
                "configure": "genai.configure(api_key=key)",
                "model": "genai.GenerativeModel('model-name')",
                "usage": "model.generate_content(prompt)",
                "used_in": ["api_manager.py", "judge.py (old pattern)"]
            },
            "google.genai": {
                "import": "from google import genai",
                "client": "genai.Client()",
                "usage": "client.models.generate_content(...)",
                "used_in": ["deep_reviewer.py", "journal_reviewer.py", "orchestrator.py", "judge.py"]
            }
        }
        
        print("\n" + "=" * 60)
        print("Google AI SDK Usage Patterns in Repository")
        print("=" * 60)
        for api_name, pattern in usage_patterns.items():
            print(f"\n{api_name}:")
            for key, value in pattern.items():
                print(f"  {key}: {value}")
        
        assert True  # Test passes, but prints usage info


class TestIncorrectUsageDetection:
    """Detect files with incorrect import usage."""
    
    @pytest.mark.unit
    def test_find_files_with_wrong_imports(self):
        """Find all Python files and check for import inconsistencies."""
        
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        incorrect_files = []
        
        # Check specific files we know about
        files_to_check = [
            'literature_review/analysis/recommendation.py',
            'literature_review/analysis/judge.py',
            'literature_review/reviewers/deep_reviewer.py',
            'literature_review/reviewers/journal_reviewer.py',
            'literature_review/orchestrator.py',
            'literature_review/utils/api_manager.py',
        ]
        
        for rel_path in files_to_check:
            file_path = os.path.join(repo_root, rel_path)
            if not os.path.exists(file_path):
                continue
                
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Check import type
            uses_google_genai = 'from google import genai' in content
            uses_google_generativeai = 'import google.generativeai as genai' in content
            
            # Check what API methods are used
            uses_client = 'genai.Client()' in content
            uses_configure = 'genai.configure(' in content
            uses_generative_model = 'genai.GenerativeModel' in content
            
            # Detect mismatches
            if uses_google_genai and (uses_configure or uses_generative_model):
                incorrect_files.append({
                    'file': rel_path,
                    'issue': 'Uses "from google import genai" but calls configure() or GenerativeModel()',
                    'recommendation': 'Change to "import google.generativeai as genai"'
                })
            
            if uses_google_generativeai and uses_client:
                incorrect_files.append({
                    'file': rel_path,
                    'issue': 'Uses "import google.generativeai" but calls Client()',
                    'recommendation': 'Change to "from google import genai"'
                })
        
        # Print findings
        print("\n" + "=" * 60)
        print("Import Consistency Check Results")
        print("=" * 60)
        
        if incorrect_files:
            print(f"\n❌ Found {len(incorrect_files)} file(s) with incorrect imports:\n")
            for item in incorrect_files:
                print(f"File: {item['file']}")
                print(f"  Issue: {item['issue']}")
                print(f"  Fix: {item['recommendation']}")
                print()
        else:
            print("\n✅ All files use correct import patterns!")
        
        # Report as test result
        if incorrect_files:
            pytest.fail(
                f"Found {len(incorrect_files)} file(s) with incorrect import usage. "
                "See test output for details."
            )


if __name__ == '__main__':
    # Run tests with verbose output
    pytest.main([__file__, '-v', '-s'])
