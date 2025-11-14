# Task Card #14 - Advanced Pipeline Features (v2.0)

**Priority:** 🟡 HIGH
**Estimated Effort:** 12-16 hours
**Risk Level:** MEDIUM
**Dependencies:** Task Cards #6, #7, #8, #13
**Wave:** Wave 3

---

## Problem Statement

The basic orchestrator (v1.0) provides sequential execution for the pipeline but lacks production capabilities required for scale and robustness: checkpoint/resume, parallel processing, smart retry with error classification, API quota management, dry-run mode and observability. Implementing these features in a controlled, test-driven manner reduces risk and enables safe performance improvements.

## Acceptance Criteria

Functional:
- [ ] Checkpoint and resume from any stage for in-progress runs
- [ ] Parallel processing of multiple papers (configurable concurrency)
- [ ] Intelligent retry distinguishing transient vs permanent errors
- [ ] API quota monitoring and throttling
- [ ] Dry-run mode that performs validation without side effects
- [ ] Backward compatible with `pipeline_orchestrator.py` v1 invocation

Non-Functional:
- [ ] Unit and integration tests for checkpointing and retry logic
- [ ] Logging and metrics for concurrency, retries, and stage durations
- [ ] Configurable via `pipeline_config.json` or CLI flags
- [ ] Feature flags to enable/disable experimental features

Security & Safety:
- [ ] Parallel processing is only enabled after INT-001/INT-003 pass (safety gate)
- [ ] Rate limits are respected to avoid API throttling and quotas

---

## Design Contract (2-4 bullets)

- Inputs: pipeline configuration (JSON), workspace with paper inputs, optional resume checkpoint file
- Outputs: logs, checkpoint/state file, result artifacts (reports), exit code
- Error modes: transient API errors (retryable), permanent data errors (fail and record), timeouts
- Success: pipeline processes N papers under concurrency C, checkpoint/resume completes, retry prevents transient failures from causing permanent failure

---

## Edge Cases

- Interrupted runs (process killed, machine reboot)
- Partial outputs left behind (files, partial DB writes)
- Non-idempotent stages (stages that append state instead of overwriting)
- API rate limit changes mid-run
- Large batches causing memory pressure

---

## Implementation Overview

Break into sub-tasks:

- 14.1 Checkpoint/Resume (4-6h)
  - Create a lightweight JSON-based checkpoint file that records processed item ids, current stage, timestamps and retry counts.
  - Add `--resume-from` CLI option and `--checkpoint-file` config.
  - Implement atomic checkpoint writes (write to tmp then rename) to avoid corruption.
  - Add `dry-run` behavior that only writes simulated checkpoint entries.

- 14.2 Parallel Processing (6-8h) — BLOCKED until safety validation
  - Implement concurrency via `concurrent.futures.ThreadPoolExecutor` (IO-bound operations) or `ProcessPoolExecutor` when CPU-bound.
  - Provide configurable `max_workers` in `pipeline_config.json`.
  - Use a per-paper processing function that executes the pipeline stages for a single paper and reports status to coordinator.
  - Maintain a coordinator event loop that manages the worker pool, aggregates results, and updates checkpoint.

- 14.3 Smart Retry & Quota Mgmt (4-6h)
  - Implement retry policies with exponential backoff and jitter for transient failures.
  - Add an error classification module that maps exception types and HTTP status codes to retryable/non-retryable.
  - Add a token-bucket style quota manager (simple) to throttle API calls across threads.
  - Provide observability through counters for retry attempts and throttle events.

- 14.4 Dry-run & Feature Flags (1-2h)
  - `--dry-run` option: walk the job queue, validate inputs, but do not call external APIs or write DB.
  - Feature flag in config to enable parallel processing.

---

## Proposed Data Structures

Checkpoint file (`checkpoint.json`) example:

```json
{
  "run_id": "2025-11-11T10:00:00",
  "last_updated": "2025-11-11T10:23:12",
  "papers": {
    "paper_0001.pdf": { "stage": "completed", "stages": {"journal": "2025-11-11T10:01:00", "judge": "2025-11-11T10:05:00"} },
    "paper_0002.pdf": { "stage": "in_progress", "stages": {"journal": "2025-11-11T10:02:00"}, "retries": 1 }
  },
  "config": { "max_workers": 4 }
}
```

Quota manager state (in-memory): counters per API with timestamp windows.

---

## Suggested Code Patterns & Snippets

Checkpoint atomic write:

```python
import json
from pathlib import Path

def atomic_write(path: Path, data: dict):
    tmp = path.with_suffix('.tmp')
    with tmp.open('w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(path)
```

Parallel worker sketch (coordinator):

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def process_paper(paper_path, config):
    # run stages for a single paper
    # return (paper, status, details)
    pass

with ThreadPoolExecutor(max_workers=config.get('max_workers', 4)) as exe:
    futures = {exe.submit(process_paper, p, config): p for p in papers}
    for fut in as_completed(futures):
        paper = futures[fut]
        try:
            result = fut.result()
            update_checkpoint(paper, result)
        except Exception as e:
            handle_failure(paper, e)
```

Retry helper (exponential backoff):

```python
import time
import random

def retry(func, attempts=3, base=0.5, factor=2.0):
    for i in range(attempts):
        try:
            return func()
        except TransientError as e:
            sleep = base * (factor ** i) + random.uniform(0, 0.1)
            time.sleep(sleep)
    raise
```

Quota manager sketch:

```python
import time
from threading import Lock

class SimpleQuota:
    def __init__(self, rate, per_seconds=60):
        self.rate = rate
        self.per = per_seconds
        self.allowance = rate
        self.last_check = time.time()
        self.lock = Lock()

    def consume(self, tokens=1):
        with self.lock:
            now = time.time()
            elapsed = now - self.last_check
            self.last_check = now
            self.allowance += elapsed * (self.rate / self.per)
            if self.allowance > self.rate:
                self.allowance = self.rate
            if self.allowance >= tokens:
                self.allowance -= tokens
                return True
            return False
```

---

## Tests to Add (integration/unit mapping)

- Unit:
  - Checkpoint read/write atomicity
  - Retry helper behavior (mock transient error)
  - Quota manager correctness under burst

- Integration:
  - End-to-end single-paper with checkpoint file written
  - Resume from checkpoint: run until stage 2, kill, resume and complete
  - Parallel worker run: process 4 small artificial papers concurrently and assert outputs
  - Retry behavior with mocked API returning transient errors first

Add tests under `tests/automation/test_orchestrator_v2.py` (marker `integration` where appropriate).

---

## Configuration

Add keys to `pipeline_config.json`:

```json
{
  "max_workers": 4,
  "enable_parallel": false,
  "checkpoint_file": "pipeline_checkpoint.json",
  "retry": { "attempts": 3, "base": 0.5, "factor": 2.0 },
  "quota": { "api_x": { "rate": 60, "per_seconds": 60 } }
}
```

---

## Acceptance Test Plan

1. Basic smoke run with `enable_parallel`=false: pipeline behaves like v1.0 and writes checkpoint file after each stage.
2. Checkpoint/resume: run, interrupt after stage 2, re-run with `--resume` and confirm completion.
3. Dry-run: `--dry-run` verifies steps without hitting external APIs or writing DB rows.
4. Parallel run (manual enable after INT-001 passes): run with `max_workers`=4 on demo papers and compare total time and correctness against sequential run.
5. Retry: instrument a mocked endpoint to return HTTP 503 twice then 200 and assert the retry logic causes the stage to succeed.

---

## Rollout Plan & Feature Flags

- Merge to `feature/orchestrator-v2` branch.
- Keep `pipeline_orchestrator.py` v1.0 as stable default in `main`.
- Default `enable_parallel` to `false` in config. Enable in controlled environment only after INT-001 + INT-003 pass.
- Add a toggle `--enable-experimental` CLI flag to allow feature testing without changing config.

---

## Implementation Checklist

- [ ] Implement checkpoint read/write & CLI
- [ ] Implement retry helper and error classification
- [ ] Implement quota manager
- [ ] Implement per-paper worker and coordinator
- [ ] Add unit and integration tests
- [ ] Add logging and metrics
- [ ] Document usage and examples

---

## Estimated Lines: ~400-500 additional

**Notes:** Concurrency introduces complexity. Keep design conservative and test-driven. Parallelism should only be enabled after safety validation (integration tests). Feature flags and dry-run mode reduce risk.
