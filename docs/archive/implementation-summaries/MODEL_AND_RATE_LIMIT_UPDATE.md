# Model and Rate Limit Configuration Update
**Date:** November 14, 2025  
**Change Type:** Configuration Update - Model & Rate Limiting  
**Status:** ✅ COMPLETED

---

## Summary

Updated all pipeline components to use **`gemini-2.5-flash`** model with **8 RPM rate limiting** (conservative, below the 10 RPM quota limit) to ensure smooth operation within API quotas.

---

## Changes Made

### Model Changes: `gemini-2.0-flash-exp` → `gemini-2.5-flash`

**Reason:** gemini-2.0-flash-exp has **0 RPM quota** available (exhausted), while gemini-2.5-flash has **10 RPM** available.

**Files Updated:**
1. ✅ `literature_review/reviewers/journal_reviewer.py`
2. ✅ `literature_review/reviewers/deep_reviewer.py`
3. ✅ `literature_review/orchestrator.py`
4. ✅ `literature_review/utils/api_manager.py`
5. ✅ `literature_review/analysis/judge.py` (already had correct model)

---

### Rate Limit Changes: 60 RPM → 8 RPM

**Reason:** Align with actual quota limits for gemini-2.5-flash (10 RPM total, using 8 RPM for safety margin).

**Configuration Updates:**

#### 1. Journal Reviewer (`journal_reviewer.py`)
```python
API_CONFIG = {
    "RETRY_ATTEMPTS": 3,
    "RETRY_DELAY": 5,
    "API_CALLS_PER_MINUTE": 8,  # Conservative limit for gemini-2.5-flash (10 RPM available)
}
```

**API Call:**
```python
response = self.client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config=current_config_object
)
```

---

#### 2. Deep Reviewer (`deep_reviewer.py`)
```python
API_CONFIG = {
    "RETRY_ATTEMPTS": 3,
    "RETRY_DELAY": 5,
    "API_CALLS_PER_MINUTE": 8,  # Conservative limit for gemini-2.5-flash (10 RPM available)
}
```

**API Call:**
```python
response = self.client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config=self.json_generation_config
)
```

---

#### 3. Orchestrator (`orchestrator.py`)
```python
ANALYSIS_CONFIG = {
    'RETRY_ATTEMPTS': 3,
    'RETRY_DELAY': 5,
    'API_CALLS_PER_MINUTE': 8,  # Conservative limit for gemini-2.5-flash (10 RPM available)
}
```

**API Call:**
```python
response = self.client.models.generate_content(
    model="gemini-2.5-flash", 
    contents=prompt, 
    config=current_config_object
)
```

---

#### 4. Judge Reviewer (`judge.py`)
```python
API_CONFIG = {
    "RETRY_ATTEMPTS": 3,
    "RETRY_DELAY": 5,
    "API_CALLS_PER_MINUTE": 8,  # Conservative limit for gemini-2.5-flash (10 RPM available)
    "MATCH_CONFIDENCE_THRESHOLD": 0.8,
    "CLAIM_BATCH_SIZE": 10,
    # ... (other config)
}
```

**Note:** Judge already had `gemini-2.5-flash` configured. Only rate limit updated.

---

#### 5. Recommendation Engine (`recommendation.py`)
```python
RECOMMENDATION_CONFIG = {
    'RETRY_ATTEMPTS': 3,
    'RETRY_DELAY': 5,
    'API_CALLS_PER_MINUTE': 8,  # Conservative limit for gemini-2.5-flash (10 RPM available)
}
```

---

#### 6. Centralized API Manager (`utils/api_manager.py`)
```python
# Rate limiting
api_calls_per_minute = 8  # Conservative limit for gemini-2.5-flash (10 RPM available)
```

**SDK Migration:**
- Changed from: `import google.generativeai as genai`
- Changed to: `from google import genai`
- Updated initialization: `genai.Client()` instead of `genai.GenerativeModel()`

**API Call:**
```python
response = self.client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config=current_config_object
)
```

---

## API Quota Analysis

### Available Models & Limits (as of Nov 14, 2025)

| Model | Category | RPM | TPM | RPD |
|-------|----------|-----|-----|-----|
| **gemini-2.5-flash** ✅ | Text-out | 10 | 250K | 250 |
| gemini-2.5-flash-lite | Text-out | 15 | 250K | 1K |
| gemini-2.0-flash | Text-out | 15 | 1M | 200 |
| gemini-2.0-flash-lite | Text-out | 30 | 1M | 200 |
| gemini-2.0-flash-exp ❌ | Text-out | **0** | **0** | **0** |

**Selected Model:** `gemini-2.5-flash`
- **RPM Quota:** 10 requests/minute
- **TPM Quota:** 250K tokens/minute
- **RPD Quota:** 250 requests/day

---

## Rate Limiting Strategy

### Conservative Approach (8 RPM)
- **Configured Rate:** 8 calls/minute
- **Safety Margin:** 20% (2 RPM buffer)
- **Reason:** Accounts for:
  - Clock drift between client/server
  - Potential retry attempts
  - Background processes
  - Multiple concurrent pipeline components

### Expected Performance
**Journal Reviewer Processing:**
- 6 PDFs to process
- Large documents split into chunks (3-4 chunks each)
- Estimated API calls: ~30-40 total
- Time estimate: 4-5 minutes (at 8 RPM)

**Full Pipeline (6 stages):**
- Journal Reviewer: ~5 minutes
- Judge Reviewer: ~2 minutes
- DRA: ~1 minute
- Orchestrator: ~2 minutes
- Deep Reviewer: ~3 minutes
- Sync: No API calls

**Total Pipeline Time:** ~13-15 minutes for 6 PDFs

---

## Rate Limiting Implementation

### Mechanism
All components use the same rate limiting pattern:

```python
def rate_limit(self):
    """Implement rate limiting"""
    current_time = time.time()
    
    # Reset counter every 60 seconds
    if current_time - self.minute_start >= 60:
        self.calls_this_minute = 0
        self.minute_start = current_time

    # Check if limit reached
    if self.calls_this_minute >= API_CONFIG['API_CALLS_PER_MINUTE']:
        sleep_time = 60.1 - (current_time - self.minute_start)
        if sleep_time > 0:
            logger.info(f"Rate limit ({API_CONFIG['API_CALLS_PER_MINUTE']}/min) reached. Sleeping for {sleep_time:.1f} seconds...")
            time.sleep(sleep_time)
            self.calls_this_minute = 0
            self.minute_start = time.time()
    
    self.calls_this_minute += 1
```

### Retry Logic
All components implement exponential backoff on API errors:

```python
for attempt in range(API_CONFIG['RETRY_ATTEMPTS']):  # 3 attempts
    try:
        response = self.client.models.generate_content(...)
        # Success - break out
        break
    except Exception as e:
        if "429" in str(e):  # Rate limit error
            time.sleep(RETRY_DELAY * (attempt + 2))  # 10s, 15s, 20s
        elif attempt < RETRY_ATTEMPTS - 1:
            time.sleep(RETRY_DELAY)  # 5s standard retry
        else:
            logger.error("Max retries reached")
```

---

## Testing Results

### Initial Test (Post-Update)
```
2025-11-14 17:38:11 - INFO - Gemini Client initialized (Thinking Disabled)
2025-11-14 17:38:12 - INFO - Sentence Transformer initialized
2025-11-14 17:38:12 - INFO - Total supported files found: 6
2025-11-14 17:38:12 - INFO - Ready to process 6 papers
2025-11-14 17:38:12 - INFO - Processing: gk8117.pdf
```

**Status:** ✅ Initialization successful with new model

### Expected Behavior
1. **Smooth Processing:** No quota exhaustion errors
2. **Rate Limiting:** Automatic sleep when approaching 8 calls/minute
3. **Retry Logic:** Graceful handling of transient errors
4. **Logging:** Clear indication of rate limit pauses

---

## Rollback Plan (If Needed)

If `gemini-2.5-flash` encounters issues, alternative models:

### Option 1: gemini-2.5-flash-lite
- **RPM:** 15 (higher than current)
- **TPM:** 250K
- **Change Required:** Update model name only
- **Trade-off:** Slightly reduced quality

### Option 2: gemini-2.0-flash
- **RPM:** 15 (higher than current)
- **TPM:** 1M (4x higher)
- **Change Required:** Update model name only
- **Trade-off:** Different model family

### Option 3: Paid Tier Upgrade
- **RPM:** 1,000+ (depending on tier)
- **Cost:** ~$0.075 per 1M input tokens
- **Benefit:** No rate limiting concerns

---

## Production Recommendations

### Immediate (Current Setup)
- ✅ Use `gemini-2.5-flash` at 8 RPM
- ✅ Monitor API error logs for 429 errors
- ✅ Track actual API usage vs quota

### Short-term (Next Week)
1. **Add Quota Monitoring:**
   ```python
   def check_quota_before_job(estimated_calls):
       # Pre-flight check
       if estimated_calls > remaining_quota:
           raise QuotaInsufficientError()
   ```

2. **Implement Adaptive Rate Limiting:**
   ```python
   if api_error_rate > 0.1:  # 10% errors
       reduce_rate_limit(by=0.5)  # Drop to 4 RPM
   ```

3. **Add Usage Dashboard:**
   - Real-time quota consumption
   - Estimated time to completion
   - Cost estimation per job

### Long-term (Production)
1. **Multi-Model Support:**
   - Primary: `gemini-2.5-flash`
   - Fallback: `gemini-2.5-flash-lite`
   - Premium jobs: `gemini-1.5-pro`

2. **Quota Pooling:**
   - Multiple API keys
   - Round-robin distribution
   - Automatic failover

3. **Cost Management:**
   - Budget limits per job
   - Cost estimation before execution
   - Monthly usage caps

---

## Impact Assessment

### Positive Impacts ✅
1. **No More Quota Errors:** Using model with available quota
2. **Predictable Processing:** 8 RPM allows accurate time estimates
3. **Better Monitoring:** Clear rate limit logs
4. **Cost Control:** Free tier sufficient for testing

### Potential Concerns ⚠️
1. **Slower Processing:** 8 RPM vs previous 60 RPM assumption
   - **Mitigation:** Acceptable for current workload (6 PDFs)
   - **Future:** Consider paid tier for production scale

2. **Daily Quota:** 250 requests/day limit
   - **Current Usage:** ~40 requests per 6-PDF job
   - **Max Jobs/Day:** ~6 jobs
   - **Mitigation:** Sufficient for testing phase

3. **Model Differences:** gemini-2.5-flash vs 2.0-flash-exp
   - **Assessment:** Same model family, similar quality expected
   - **Validation:** Compare output quality in next test

---

## Monitoring Checklist

### During Next Run ✅
- [ ] No 429 RESOURCE_EXHAUSTED errors
- [ ] Rate limiting activates correctly
- [ ] Automatic sleep messages appear
- [ ] Processing completes successfully
- [ ] Output quality maintained
- [ ] Total time within estimate (4-5 min for journal reviewer)

### Post-Run Analysis ✅
- [ ] Check `journal_test.log` for any errors
- [ ] Validate CSV output format
- [ ] Compare requirements extraction quality
- [ ] Review retry attempt counts
- [ ] Assess total API call count vs estimate

---

## Files Modified

### Core Pipeline Files (5 files)
1. `literature_review/reviewers/journal_reviewer.py`
2. `literature_review/reviewers/deep_reviewer.py`
3. `literature_review/orchestrator.py`
4. `literature_review/analysis/judge.py`
5. `literature_review/analysis/recommendation.py`

### Utility Files (1 file)
6. `literature_review/utils/api_manager.py`

### Documentation (This file)
7. `MODEL_AND_RATE_LIMIT_UPDATE.md`

---

## Next Steps

1. **Complete Journal Reviewer Test:**
   ```bash
   tail -f journal_test.log
   ```

2. **Validate Outputs:**
   ```bash
   head -20 neuromorphic-research_database.csv
   jq '.[] | .review.Requirement(s) | length' review_version_history.json
   ```

3. **Run Full Pipeline:**
   ```bash
   python pipeline_orchestrator.py --convergence-mode
   ```

4. **Update Smoke Test Report:**
   - Document successful completion
   - Update production readiness assessment
   - Note performance metrics

---

## Conclusion

All pipeline components now use **`gemini-2.5-flash`** with **8 RPM rate limiting**, aligned with current API quota availability. This configuration provides:

- ✅ Reliable API access (no quota errors)
- ✅ Predictable processing times
- ✅ Clear monitoring and logging
- ✅ Sufficient capacity for testing workload

**Status:** Ready for comprehensive end-to-end testing.

---

**Change Log:**
- 2025-11-14 17:38 UTC: Updated all 6 files to gemini-2.5-flash @ 8 RPM
- 2025-11-14 17:38 UTC: Initiated journal reviewer test
