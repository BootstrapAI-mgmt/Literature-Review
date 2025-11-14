# Google AI SDK Best Practices and Troubleshooting Guide

**Version:** 1.0  
**Date:** 2025-11-14  
**SDK Version:** google-generativeai 0.8.5  
**Status:** ✅ Active

---

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Best Practices](#best-practices)
3. [Common Issues & Solutions](#common-issues--solutions)
4. [Migration Guide](#migration-guide)
5. [Testing Strategy](#testing-strategy)
6. [Troubleshooting Workflow](#troubleshooting-workflow)

---

## Quick Reference

### The Two APIs at a Glance

| Feature | `google.generativeai` | `google.genai` |
|---------|----------------------|----------------|
| **Import** | `import google.generativeai as genai` | `from google import genai` |
| **Client Type** | Model-based (`GenerativeModel`) | Client-based (`Client`) |
| **API Key Setup** | `genai.configure(api_key=key)` | Auto from `GEMINI_API_KEY` env |
| **Model Creation** | `genai.GenerativeModel('model-name')` | `genai.Client()` |
| **Content Gen** | `model.generate_content(prompt)` | `client.models.generate_content(...)` |
| **Has `configure()`** | ✅ Yes | ❌ No |
| **Has `GenerativeModel`** | ✅ Yes | ❌ No |
| **Has `Client`** | ❌ No | ✅ Yes |
| **Thinking Mode** | ❌ No | ✅ Yes |
| **Extended Context** | Limited | ✅ Yes |
| **Use When** | Standard generation | Advanced features, thinking mode |

---

## Best Practices

### 1. Choose the Right API

#### Use `google.generativeai` When:
```python
import google.generativeai as genai
from google.generativeai import types

# ✅ Good for:
# - Standard content generation
# - Chat sessions
# - Fine-tuning models
# - File uploads
# - Caching
# - Simple applications

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')
response = model.generate_content("Your prompt here")
```

#### Use `google.genai` When:
```python
from google import genai
from google.genai import types

# ✅ Good for:
# - Thinking mode (extended reasoning)
# - Client-based architecture
# - Extended context windows
# - Advanced features (live, batches)
# - Multi-modal applications

client = genai.Client()  # Auto-uses GEMINI_API_KEY from env
config = types.GenerateContentConfig(
    temperature=0.1,
    thinking_config=types.ThinkingConfig(thinking_budget=1)
)
response = client.models.generate_content(
    model='gemini-2.0-flash-thinking-exp',
    contents="Your prompt here",
    config=config
)
```

### 2. Consistent Import Patterns

**✅ DO:**
```python
# Pattern 1: Legacy API
import google.generativeai as genai
from google.generativeai import types

# Pattern 2: New SDK
from google import genai
from google.genai import types
```

**❌ DON'T:**
```python
# WRONG: Mixing incompatible imports
import google.generativeai as genai  # Has configure(), GenerativeModel()
client = genai.Client()  # ❌ Client not available here!

# WRONG: Using wrong API for your needs
from google import genai  # Has Client()
genai.configure(api_key=key)  # ❌ configure() not available here!
```

### 3. Environment Variable Management

**✅ Best Practice:**
```python
import os
from dotenv import load_dotenv

load_dotenv()

# Legacy API - explicit configure
import google.generativeai as genai
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found")
genai.configure(api_key=api_key)

# New SDK - automatic from environment
from google import genai
# Client() automatically reads GEMINI_API_KEY
client = genai.Client()
```

### 4. Type Hints and IDE Support

**✅ DO:**
```python
from typing import Optional, Dict, Any
from google.genai import types

def generate_with_thinking(
    client: genai.Client,
    prompt: str,
    config: Optional[types.GenerateContentConfig] = None
) -> str:
    """Generate content with type hints for better IDE support."""
    response = client.models.generate_content(
        model='gemini-2.0-flash-thinking-exp',
        contents=prompt,
        config=config
    )
    return response.text
```

### 5. Error Handling

**✅ Comprehensive Error Handling:**
```python
import logging
from google.api_core import exceptions as google_exceptions

logger = logging.getLogger(__name__)

def safe_api_call(client: genai.Client, prompt: str) -> Optional[str]:
    """API call with proper error handling."""
    retry_attempts = 3
    retry_delay = 5
    
    for attempt in range(retry_attempts):
        try:
            response = client.models.generate_content(
                model='gemini-2.0-flash-thinking-exp',
                contents=prompt
            )
            return response.text
            
        except google_exceptions.ResourceExhausted as e:
            # Rate limit hit
            logger.warning(f"Rate limit on attempt {attempt + 1}: {e}")
            if attempt < retry_attempts - 1:
                time.sleep(retry_delay * (attempt + 2))
                
        except google_exceptions.InvalidArgument as e:
            # Bad request - don't retry
            logger.error(f"Invalid argument: {e}")
            return None
            
        except Exception as e:
            # Unexpected error
            logger.error(f"API error on attempt {attempt + 1}: {e}")
            if attempt < retry_attempts - 1:
                time.sleep(retry_delay)
    
    logger.error(f"API call failed after {retry_attempts} attempts")
    return None
```

### 6. Code Comments for Clarity

**✅ Document Your Import Choice:**
```python
# Use google.genai (new SDK) for Client() interface with thinking mode
from google import genai
from google.genai import types

# OR

# Use google.generativeai (legacy API) for standard generation with configure()
import google.generativeai as genai
from google.generativeai import types
```

---

## Common Issues & Solutions

### Issue 1: `AttributeError: module 'google.generativeai' has no attribute 'Client'`

**Symptoms:**
```python
import google.generativeai as genai
client = genai.Client()  # ❌ AttributeError
```

**Root Cause:**
You're using `google.generativeai` but trying to access `Client` which is only in `google.genai`.

**Solution:**
```python
# Change to:
from google import genai
client = genai.Client()  # ✅ Works!
```

**Prevention:**
Add this comment to your imports:
```python
# Use google.genai (new SDK) for Client() interface
from google import genai
```

---

### Issue 2: `AttributeError: module 'google.genai' has no attribute 'configure'`

**Symptoms:**
```python
from google import genai
genai.configure(api_key=key)  # ❌ AttributeError
```

**Root Cause:**
You're using `google.genai` but trying to access `configure()` which is only in `google.generativeai`.

**Solution:**
```python
# Change to:
import google.generativeai as genai
genai.configure(api_key=key)  # ✅ Works!
```

**Prevention:**
The new SDK uses environment variables automatically:
```python
# No configure needed - just set GEMINI_API_KEY env var
from google import genai
client = genai.Client()  # Automatically uses GEMINI_API_KEY
```

---

### Issue 3: Mixed Imports Across Codebase

**Symptoms:**
Some files use one pattern, others use another, leading to confusion.

**Detection:**
Run our test suite:
```bash
pytest tests/test_google_ai_sdk_imports.py -v -s
```

**Solution:**
Standardize based on actual usage:
```python
# Files using Client() → google.genai
from google import genai
client = genai.Client()

# Files using configure/GenerativeModel → google.generativeai
import google.generativeai as genai
genai.configure(api_key=key)
model = genai.GenerativeModel('model-name')
```

**Prevention:**
Add pre-commit hooks or CI checks using our test suite.

---

### Issue 4: Wrong `types` Import

**Symptoms:**
```python
import google.generativeai as genai
from google.genai import types  # ❌ Wrong types for this API
```

**Solution:**
Match your types import to your main import:
```python
# Pattern 1:
import google.generativeai as genai
from google.generativeai import types

# Pattern 2:
from google import genai
from google.genai import types
```

---

### Issue 5: Thinking Mode Not Working

**Symptoms:**
Model doesn't show extended reasoning despite requesting it.

**Root Cause:**
Thinking mode requires the `google.genai` API and specific models.

**Solution:**
```python
# ✅ Correct setup for thinking mode
from google import genai
from google.genai import types

client = genai.Client()
thinking_config = types.ThinkingConfig(thinking_budget=1)
config = types.GenerateContentConfig(
    temperature=0.1,
    thinking_config=thinking_config
)

response = client.models.generate_content(
    model='gemini-2.0-flash-thinking-exp',  # Must use thinking-enabled model
    contents=prompt,
    config=config
)
```

---

## Migration Guide

### From `google.generativeai` to `google.genai`

**Before:**
```python
import google.generativeai as genai
from google.generativeai import types

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

config = genai.types.GenerationConfig(
    temperature=0.2,
    max_output_tokens=16384
)

response = model.generate_content(
    contents=prompt,
    generation_config=config
)
```

**After:**
```python
from google import genai
from google.genai import types

# No configure needed - uses GEMINI_API_KEY env var automatically
client = genai.Client()

config = types.GenerateContentConfig(
    temperature=0.2,
    max_output_tokens=16384
)

response = client.models.generate_content(
    model='gemini-2.0-flash-exp',
    contents=prompt,
    config=config
)
```

**Key Changes:**
1. Import changes: `from google import genai`
2. No `configure()` call needed
3. Use `Client()` instead of `GenerativeModel()`
4. Call through `client.models.generate_content()`
5. Specify model in the call, not at client creation

---

## Testing Strategy

### 1. Import Validation Tests

**File:** `tests/test_google_ai_sdk_imports.py`

**What It Tests:**
- ✅ Both import patterns work
- ✅ Each API has expected attributes
- ✅ Files use correct imports for their usage
- ✅ No mixed/inconsistent patterns

**Run Tests:**
```bash
# Full test suite
pytest tests/test_google_ai_sdk_imports.py -v -s

# Quick check for incorrect usage
pytest tests/test_google_ai_sdk_imports.py::TestIncorrectUsageDetection -v

# API structure validation
pytest tests/test_google_ai_sdk_imports.py::TestGoogleAISDKImports -v
```

### 2. Manual Verification

**Check Import Pattern:**
```bash
# Find files using google.generativeai
grep -r "import google.generativeai as genai" literature_review/

# Find files using google.genai
grep -r "from google import genai" literature_review/

# Check what they actually use
grep -r "genai.Client()" literature_review/
grep -r "genai.configure(" literature_review/
grep -r "genai.GenerativeModel" literature_review/
```

### 3. Runtime Verification

**Test Script:**
```python
# test_import_runtime.py
def test_imports():
    """Verify imports work at runtime."""
    # Test google.generativeai
    import google.generativeai as genai1
    assert hasattr(genai1, 'configure')
    assert hasattr(genai1, 'GenerativeModel')
    assert not hasattr(genai1, 'Client')
    
    # Test google.genai
    from google import genai as genai2
    assert hasattr(genai2, 'Client')
    assert not hasattr(genai2, 'configure')
    assert not hasattr(genai2, 'GenerativeModel')
    
    print("✅ All import patterns verified!")

if __name__ == '__main__':
    test_imports()
```

---

## Troubleshooting Workflow

### Step 1: Identify the Error

**Common Error Messages:**
1. `AttributeError: module 'google.generativeai' has no attribute 'Client'`
2. `AttributeError: module 'google.genai' has no attribute 'configure'`
3. `AttributeError: module 'google.genai' has no attribute 'GenerativeModel'`
4. `ModuleNotFoundError: No module named 'google.genai'`

### Step 2: Check SDK Version

```bash
pip show google-generativeai
# Should show: Version: 0.8.5 (or higher)
```

**If version < 0.8.5:**
```bash
pip install --upgrade google-generativeai
```

### Step 3: Verify Import Pattern

**Run our diagnostic:**
```bash
pytest tests/test_google_ai_sdk_imports.py::TestIncorrectUsageDetection -v -s
```

**Manual check:**
```python
# What does your file import?
import google.generativeai as genai  # OR
from google import genai

# What does your file use?
client = genai.Client()  # Needs: from google import genai
model = genai.GenerativeModel()  # Needs: import google.generativeai as genai
genai.configure()  # Needs: import google.generativeai as genai
```

### Step 4: Fix the Import

**Decision Tree:**

```
Does your code call genai.Client()?
├─ YES → Use: from google import genai
│         from google.genai import types
│
└─ NO → Does your code call genai.configure() or genai.GenerativeModel()?
    ├─ YES → Use: import google.generativeai as genai
    │         from google.generativeai import types
    │
    └─ NO → File doesn't use genai directly
            → Check if APIManager or other abstraction is used
            → Match import to what abstraction expects
```

### Step 5: Verify Fix

**Run Tests:**
```bash
# Check import consistency
pytest tests/test_google_ai_sdk_imports.py -v

# Check existing functionality still works
pytest tests/unit/ -v
pytest tests/integration/ -v
```

**Manual Verification:**
```python
# Test the fixed file
python -c "from literature_review.analysis import judge; print('✅ Import works')"
```

### Step 6: Document the Change

**Add Comment:**
```python
# Use google.genai (new SDK) for Client() interface
from google import genai
from google.genai import types
```

---

## Repository-Specific Patterns

### Current Usage (Post-Fix)

| File | API | Why |
|------|-----|-----|
| `api_manager.py` | `google.generativeai` | Uses `configure()` and `GenerativeModel()` |
| `judge.py` | `google.genai` | Uses `Client()` for judgment calls |
| `deep_reviewer.py` | `google.genai` | Uses `Client()` with thinking mode |
| `journal_reviewer.py` | `google.genai` | Uses `Client()` for paper analysis |
| `orchestrator.py` | `google.genai` | Uses `Client()` for orchestration |
| `recommendation.py` | `google.generativeai` | Uses APIManager (which uses `generativeai`) |

### Pattern Examples from Codebase

**APIManager (Legacy API):**
```python
# literature_review/utils/api_manager.py
import google.generativeai as genai
from google.generativeai import types

class APIManager:
    def __init__(self, cache_dir='api_cache'):
        api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=api_key)  # ✅ Uses configure()
        
        self.client = genai.GenerativeModel('gemini-1.5-flash')  # ✅ Uses GenerativeModel
        self.json_generation_config = genai.types.GenerationConfig(...)
```

**Deep Reviewer (New SDK):**
```python
# literature_review/reviewers/deep_reviewer.py
from google import genai
from google.genai import types

class DeepReviewer:
    def __init__(self):
        self.client = genai.Client()  # ✅ Uses Client()
        thinking_config = types.ThinkingConfig(thinking_budget=1)
        self.json_generation_config = types.GenerateContentConfig(...)
```

---

## Checklist for New Code

When adding new files that use Google AI SDK:

- [ ] Decide which API you need (`Client()` vs `configure()/GenerativeModel()`)
- [ ] Use correct import pattern
- [ ] Add comment explaining API choice
- [ ] Use correct `types` import to match
- [ ] Add environment variable validation
- [ ] Implement error handling
- [ ] Add tests to verify import usage
- [ ] Run `pytest tests/test_google_ai_sdk_imports.py`

---

## Resources

### Official Documentation
- **google-generativeai (Legacy):** https://ai.google.dev/gemini-api/docs/quickstart
- **google.genai (New SDK):** https://googleapis.github.io/python-genai/

### Internal Documentation
- **Import Analysis:** `docs/assessments/GOOGLE_AI_SDK_IMPORT_ANALYSIS.md`
- **Test Suite:** `tests/test_google_ai_sdk_imports.py`
- **This Guide:** `docs/guides/GOOGLE_AI_SDK_BEST_PRACTICES.md`

### Quick Commands
```bash
# Check SDK version
pip show google-generativeai

# Run import validation tests
pytest tests/test_google_ai_sdk_imports.py -v -s

# Find usage patterns
grep -r "genai.Client()" literature_review/
grep -r "genai.configure(" literature_review/

# Test specific file imports
python -c "from literature_review.analysis import judge"
```

---

**Last Updated:** 2025-11-14  
**Maintainer:** Development Team  
**Review Frequency:** Every SDK major version update
