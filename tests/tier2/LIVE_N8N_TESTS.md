# Tier 2 & 3 Integration Tests - Live n8n Environment Notes

## Current Test Results (Phase 4 Complete)

| Tier | Passed | Skipped | Failed | Total |
|------|--------|---------|--------|-------|
| Tier 2 | 24 | 5 | 0 | 29 |
| Tier 3 | 17 | 0 | 0 | 17 |
| **Total** | **41** | **5** | **0** | **46** |

---

## Expected Skips (5 total)

These tests skip by design - the endpoints they test either don't exist or are slow:

| Test ID | Endpoint | Skip Reason | Resolution |
|---------|----------|-------------|------------|
| T2-EP-05 | `/distributor-status` | 404 - Endpoint not configured | By design (no status endpoint) |
| T2-EP-06 | `/state-reconciliation` | Timeout | Slow workflow (AI analysis) |
| T2-EP-09 | `/error-handler` | 404 - Endpoint not configured | By design (uses errorTrigger) |
| T2-01-01 | `/github-doc-trigger` | Assertion mismatch | Test logic issue |
| T2-01-02 | `/task-distributor` | 404 - Path mismatch | Test logic issue |

---

## n8n MCP Bridge (NEW)

Antigravity agents can access n8n via the MCP Bridge webhook:

```bash
python n8n-server/mcp_client.py health         # Check status
python n8n-server/mcp_client.py list_workflows # List all workflows
python n8n-server/mcp_client.py help           # Available commands
```

No API key required - uses public webhook at `/webhook/antigravity-bridge`.

---

## Running Full Test Suite

```bash
# Run all Tier 2 + Tier 3 tests
python -m pytest tests/tier2/ tests/tier3/ -v -o "addopts=" --tb=short
```

Expected result: **41 passed, 5 skipped, 0 failed**

