# Global Rate Limiter - Monitoring Guide

**Quick Reference for Production Monitoring**

## Quick Stats Check

```python
from literature_review.utils.global_rate_limiter import global_limiter

stats = global_limiter.get_statistics()
print(f"Success rate: {stats['success_rate']:.1%}")
print(f"Total requests: {stats['total_requests']}")
print(f"Failed: {stats['failed_requests']}")
```

## Real-Time Monitoring Script

```bash
# Monitor during pipeline execution
watch -n 5 'python3 -c "
from literature_review.utils.global_rate_limiter import global_limiter
stats = global_limiter.get_statistics()
print(f\"Requests: {stats['total_requests']} | Success: {stats['success_rate']:.1%} | Errors: {stats['consecutive_errors']}\")
if stats['errors_by_category']:
    print(\"Top errors:\", list(stats['errors_by_category'].items())[:3])
"'
```

## Health Check Indicators

### 🟢 Healthy Pipeline
- Success rate > 90%
- Consecutive errors < 3
- No ABORT_PIPELINE actions
- Quota pauses proportional to request rate

### 🟡 Warning Signs
- Success rate 70-90%
- Consecutive errors 3-7
- Increasing SKIP_DOCUMENT actions
- Frequent RATE_LIMIT errors

### 🔴 Critical Issues
- Success rate < 70%
- Consecutive errors > 7
- ABORT_PIPELINE triggered
- AUTHENTICATION errors

## Common Error Patterns

### Pattern 1: Rate Limit Errors
```
Errors: RATE_LIMIT: 15
Actions: RETRY_LONG_DELAY: 15
```
**Solution:** Pipeline hitting quota, delays working correctly

### Pattern 2: Malformed Responses
```
Errors: MALFORMED_RESPONSE: 8
Actions: RETRY_IMMEDIATE: 8
```
**Solution:** Check prompt quality, may need validation improvements

### Pattern 3: Content Policy Violations
```
Errors: CONTENT_POLICY: 3
Actions: SKIP_DOCUMENT: 3
```
**Solution:** Normal for some papers, documents skipped automatically

### Pattern 4: Service Issues
```
Errors: SERVICE_UNAVAILABLE: 20
Actions: RETRY_LONG_DELAY: 20
```
**Solution:** Google API having issues, retries with backoff

## Statistics Breakdown

```python
stats = global_limiter.get_statistics()

# Request statistics
total_requests = stats['total_requests']
successful = stats['successful_requests']
failed = stats['failed_requests']
success_rate = stats['success_rate']
error_rate = stats['error_rate']

# Rate limiting
calls_this_minute = stats['calls_this_minute']
quota_pauses = stats['quota_pauses']

# Error tracking
consecutive_errors = stats['consecutive_errors']
total_calls = stats['total_calls']

# Error breakdown
errors_by_category = stats['errors_by_category']  # Dict[str, int]
actions_taken = stats['actions_taken']  # Dict[str, int]

# Document handling
documents_skipped = stats['documents_skipped']
documents_requeued = stats['documents_requeued']
```

## Error Categories Reference

| Category | Severity | Auto-Action |
|----------|----------|-------------|
| SERVICE_OVERLOADED | High | RETRY_LONG_DELAY (10s) |
| SERVICE_UNAVAILABLE | Medium | RETRY_WITH_DELAY (5s) |
| RATE_LIMIT | Medium | RETRY_LONG_DELAY (10s) |
| INVALID_REQUEST | Low | SKIP_DOCUMENT |
| AUTHENTICATION | Critical | ABORT_PIPELINE |
| CONTENT_POLICY | Low | SKIP_DOCUMENT |
| MALFORMED_RESPONSE | Low | RETRY_IMMEDIATE (2s) |
| EMPTY_INPUT | Low | SKIP_DOCUMENT |
| INVALID_FORMAT | Low | SKIP_DOCUMENT |
| TOO_LARGE | Low | SKIP_DOCUMENT |
| UNKNOWN | Medium | RETRY_WITH_DELAY (5s) |

## Alert Thresholds

### Set up alerts for:

1. **High Error Rate:** `error_rate > 0.5` (50%)
2. **Consecutive Errors:** `consecutive_errors >= 5`
3. **Quota Issues:** `quota_pauses > expected`
4. **Auth Failures:** `AUTHENTICATION errors > 0`
5. **Abort Triggered:** `should_abort_pipeline() == True`

## Troubleshooting Commands

### Reset statistics
```python
# Note: Stats auto-reset on new import/process
# For manual reset, restart the Python process
```

### Check if pipeline should abort
```python
if global_limiter.should_abort_pipeline():
    print("⚠️ Pipeline abort recommended!")
    print(f"Consecutive errors: {global_limiter.consecutive_errors}")
    print(f"Recent error rate: {len([e for e in global_limiter.last_errors[-20:] if e]) / 20:.1%}")
```

### Validate a request before sending
```python
prompt = "Your API prompt here..."
is_valid, reason = global_limiter.validate_request(prompt, {'response_mime_type': 'application/json'})
if not is_valid:
    print(f"❌ Request invalid: {reason}")
```

### Get last 10 errors
```python
recent_errors = global_limiter.last_errors[-10:]
for error in recent_errors:
    if error:  # (category, action) tuple
        print(f"{error[0].name} → {error[1].name}")
```

## Performance Optimization

### Current Configuration
- Global RPM: 10 (conservative)
- Available: 1000 RPM
- Max consecutive errors: 10
- Abort threshold: 90% error rate in 20 calls

### To increase throughput
1. Monitor error rate at 10 RPM for 1 week
2. If error rate < 10%, increase to 15 RPM
3. If error rate < 5%, increase to 20 RPM
4. Never exceed 50% of available quota (500 RPM)

### To decrease error rate
1. If error rate > 30%, decrease to 8 RPM
2. Add request-specific validation
3. Improve prompt quality
4. Filter documents before processing

## Integration with Monitoring Systems

### Export to JSON
```python
import json
stats = global_limiter.get_statistics()
with open('rate_limiter_stats.json', 'w') as f:
    json.dump(stats, f, indent=2)
```

### Export to Prometheus format
```python
stats = global_limiter.get_statistics()
print(f"api_requests_total {stats['total_requests']}")
print(f"api_requests_successful {stats['successful_requests']}")
print(f"api_requests_failed {stats['failed_requests']}")
print(f"api_success_rate {stats['success_rate']}")
print(f"api_consecutive_errors {stats['consecutive_errors']}")
```

### Log to file periodically
```python
import logging
import time

logger = logging.getLogger('rate_limiter_monitor')
handler = logging.FileHandler('rate_limiter.log')
logger.addHandler(handler)

while True:
    stats = global_limiter.get_statistics()
    logger.info(f"Stats: {stats['total_requests']} req, {stats['success_rate']:.1%} success")
    time.sleep(60)  # Log every minute
```

## Dashboard Integration

The global rate limiter statistics can be displayed in the web dashboard by adding:

```python
# In webdashboard/app.py
from literature_review.utils.global_rate_limiter import global_limiter

@app.route('/api/rate_limiter_stats')
def get_rate_limiter_stats():
    return jsonify(global_limiter.get_statistics())
```

Then display in the UI with real-time updates via WebSocket.

## Related Documentation

- `GLOBAL_RATE_LIMITER_INTEGRATION.md` - Integration details
- `literature_review/utils/global_rate_limiter.py` - Source code with inline docs
- `MODEL_AND_RATE_LIMIT_UPDATE.md` - Model configuration changes

---

**Last Updated:** November 15, 2025  
**Version:** 1.0
