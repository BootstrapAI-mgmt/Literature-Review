# INCR-W2-4: Incremental Analysis Integration Tests

**Wave:** 2 (Integration)  
**Priority:** 🔴 Critical  
**Effort:** 6-8 hours  
**Status:** 🟡 Blocked (requires INCR-W2-1, W2-2)  
**Assignable:** QA/Test Engineer

---

## Overview

Comprehensive integration test suite for incremental review mode across CLI and Dashboard. Validates end-to-end workflows, edge cases, and cross-system compatibility.

---

## Dependencies

**Prerequisites:**
- ✅ INCR-W2-1 (CLI Incremental Mode)
- ✅ INCR-W2-2 (Dashboard Job Continuation API)

---

## Scope

### Included
- [x] CLI incremental mode E2E tests
- [x] Dashboard continuation E2E tests
- [x] Cross-system compatibility tests
- [x] Edge case coverage (corrupt state, no gaps, all papers relevant)
- [x] Performance benchmarks
- [x] Rollback/recovery tests

### Excluded
- ❌ Load testing (separate task)
- ❌ Security testing (separate task)
- ❌ Browser compatibility matrix (basic coverage only)

---

## Test Categories

### 1. CLI Incremental Mode Tests

#### Test 1.1: Basic Incremental Workflow
```python
def test_cli_incremental_basic_workflow(tmp_path):
    """
    Test complete CLI incremental workflow:
    1. Run baseline analysis
    2. Add new papers
    3. Run incremental update
    4. Verify results merged
    """
    output_dir = tmp_path / "review"
    
    # Step 1: Baseline
    run_cli(['--output-dir', str(output_dir)])
    assert (output_dir / 'gap_analysis_report.json').exists()
    
    baseline_state = load_json(output_dir / 'orchestrator_state.json')
    baseline_gaps = baseline_state['gap_metrics']['total_gaps']
    
    # Step 2: Add new papers
    add_papers_to_database(['paper_new1.csv', 'paper_new2.csv'])
    
    # Step 3: Incremental
    run_cli(['--incremental', '--output-dir', str(output_dir)])
    
    # Step 4: Verify
    incremental_state = load_json(output_dir / 'orchestrator_state.json')
    
    assert incremental_state['job_type'] == 'incremental'
    assert incremental_state['parent_job_id'] == baseline_state['job_id']
    assert incremental_state['papers_analyzed'] < incremental_state['total_papers']
    assert incremental_state['gap_metrics']['total_gaps'] <= baseline_gaps
```

#### Test 1.2: No New Papers Detection
```python
def test_cli_no_new_papers(tmp_path):
    """Test CLI exits gracefully when no new papers."""
    output_dir = tmp_path / "review"
    
    # Baseline
    run_cli(['--output-dir', str(output_dir)])
    
    # Incremental without adding papers
    result = run_cli(['--incremental', '--output-dir', str(output_dir)])
    
    assert "No new papers detected" in result.stdout
    assert result.returncode == 0
```

#### Test 1.3: Force Full Re-analysis
```python
def test_cli_force_overrides_incremental(tmp_path):
    """Test --force disables incremental mode."""
    output_dir = tmp_path / "review"
    
    run_cli(['--output-dir', str(output_dir)])
    add_papers_to_database(['paper_new1.csv'])
    
    result = run_cli(['--incremental', '--force', '--output-dir', str(output_dir)])
    
    # Should run full analysis
    state = load_json(output_dir / 'orchestrator_state.json')
    assert state['job_type'] == 'full'
    assert state['papers_analyzed'] == state['total_papers']
```

### 2. Dashboard Continuation Tests

#### Test 2.1: Job Continuation API
```python
def test_dashboard_job_continuation(client, sample_job):
    """Test POST /api/jobs/{job_id}/continue."""
    base_job_id = sample_job['job_id']
    
    # Upload new papers
    papers = [
        {'DOI': '10.1000/new1', 'Title': 'New Paper 1', 'Abstract': '...'},
        {'DOI': '10.1000/new2', 'Title': 'New Paper 2', 'Abstract': '...'}
    ]
    
    response = client.post(
        f'/api/jobs/{base_job_id}/continue',
        json={
            'papers': papers,
            'relevance_threshold': 0.50,
            'prefilter_enabled': True
        }
    )
    
    assert response.status_code == 202
    data = response.json()
    
    assert 'job_id' in data
    assert data['parent_job_id'] == base_job_id
    assert data['papers_to_analyze'] <= len(papers)
```

#### Test 2.2: Gap Extraction Endpoint
```python
def test_gap_extraction_endpoint(client, completed_job):
    """Test GET /api/jobs/{job_id}/gaps."""
    job_id = completed_job['job_id']
    
    response = client.get(f'/api/jobs/{job_id}/gaps?threshold=0.7')
    
    assert response.status_code == 200
    data = response.json()
    
    assert 'total_gaps' in data
    assert 'gaps' in data
    assert 'gaps_by_pillar' in data
    assert data['gap_threshold'] == 0.7
```

#### Test 2.3: Relevance Scoring Endpoint
```python
def test_relevance_scoring_endpoint(client, completed_job):
    """Test POST /api/jobs/{job_id}/relevance."""
    job_id = completed_job['job_id']
    
    papers = [
        {'DOI': '10.1000/test1', 'Title': 'Neuromorphic Computing', 'Abstract': 'Spike timing dependent plasticity...'},
        {'DOI': '10.1000/test2', 'Title': 'Unrelated Topic', 'Abstract': 'Quantum mechanics...'}
    ]
    
    response = client.post(
        f'/api/jobs/{job_id}/relevance',
        json={'papers': papers, 'threshold': 0.50}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data['total_papers_scored'] == 2
    assert data['papers_above_threshold'] >= 0
    assert len(data['scores']) == 2
```

### 3. Edge Case Tests

#### Test 3.1: Corrupt State File
```python
def test_corrupt_state_fallback(tmp_path):
    """Test fallback to full analysis when state corrupted."""
    output_dir = tmp_path / "review"
    
    # Create corrupt state
    output_dir.mkdir()
    (output_dir / 'orchestrator_state.json').write_text('{ corrupt json')
    
    # Should fallback gracefully
    result = run_cli(['--incremental', '--output-dir', str(output_dir)])
    
    assert "Incremental prerequisites not met" in result.stdout
    assert "falling back to full analysis" in result.stdout.lower()
```

#### Test 3.2: No Gaps in Base Review
```python
def test_no_gaps_all_requirements_met(tmp_path):
    """Test incremental mode when all requirements already met."""
    output_dir = tmp_path / "review"
    
    # Create perfect baseline (no gaps)
    create_perfect_baseline(output_dir)
    
    add_papers_to_database(['paper_new1.csv'])
    
    result = run_cli(['--incremental', '--output-dir', str(output_dir)])
    
    # Should handle gracefully
    assert "No gaps found" in result.stdout or "all requirements met" in result.stdout.lower()
```

#### Test 3.3: All Papers Filtered Out
```python
def test_all_papers_irrelevant(tmp_path):
    """Test when all new papers filtered as irrelevant."""
    output_dir = tmp_path / "review"
    
    run_cli(['--output-dir', str(output_dir)])
    
    # Add irrelevant papers
    add_papers_to_database(['quantum_paper.csv', 'unrelated_paper.csv'])
    
    result = run_cli(['--incremental', '--output-dir', str(output_dir), '--relevance-threshold', '0.80'])
    
    assert "No relevant papers found" in result.stdout
    assert result.returncode == 0
```

### 4. Performance Tests

#### Test 4.1: Incremental Faster Than Full
```python
def test_incremental_performance_improvement():
    """Verify incremental mode is faster than full analysis."""
    import time
    
    output_dir = Path("test_review")
    
    # Baseline (100 papers)
    start = time.time()
    run_cli(['--output-dir', str(output_dir)])
    baseline_time = time.time() - start
    
    # Add 10 new papers
    add_papers_to_database(['new_papers_10.csv'])
    
    # Incremental (10 papers, but with pre-filtering)
    start = time.time()
    run_cli(['--incremental', '--output-dir', str(output_dir)])
    incremental_time = time.time() - start
    
    # Should be significantly faster
    assert incremental_time < baseline_time * 0.5
```

#### Test 4.2: Gap Extraction Performance
```python
def test_gap_extraction_performance():
    """Verify gap extraction is fast (< 100ms)."""
    import time
    
    # Large report (500 requirements)
    large_report = create_large_gap_report(num_requirements=500)
    
    extractor = GapExtractor(large_report)
    
    start = time.time()
    gaps = extractor.extract_gaps()
    duration = time.time() - start
    
    assert duration < 0.1  # < 100ms
```

### 5. Cross-System Tests

#### Test 5.1: CLI → Dashboard Import
```python
def test_cli_dashboard_compatibility(tmp_path):
    """Test Dashboard can import CLI results."""
    output_dir = tmp_path / "cli_review"
    
    # Run CLI analysis
    run_cli(['--output-dir', str(output_dir)])
    
    # Import to Dashboard
    gap_report = output_dir / 'gap_analysis_report.json'
    
    response = client.post('/api/jobs/import', files={'report': open(gap_report, 'rb')})
    
    assert response.status_code == 200
    job_id = response.json()['job_id']
    
    # Verify Dashboard can continue from CLI job
    response = client.post(f'/api/jobs/{job_id}/continue', json={'papers': [...]})
    assert response.status_code == 202
```

#### Test 5.2: Dashboard → CLI Export
```python
def test_dashboard_cli_compatibility(client, completed_dashboard_job):
    """Test CLI can continue Dashboard jobs."""
    job_id = completed_dashboard_job['job_id']
    
    # Export Dashboard job
    response = client.get(f'/api/jobs/{job_id}/export')
    exported_dir = save_export(response.content)
    
    # Add new papers
    add_papers_to_database(['new_papers.csv'])
    
    # Continue via CLI
    result = run_cli(['--incremental', '--output-dir', str(exported_dir)])
    
    assert result.returncode == 0
```

---

## Test Fixtures

### Fixture: Sample Database
```python
@pytest.fixture
def sample_database(tmp_path):
    """Create sample research database CSV."""
    data = {
        'DOI': ['10.1000/paper1', '10.1000/paper2'],
        'Title': ['Paper 1', 'Paper 2'],
        'Abstract': ['Abstract 1...', 'Abstract 2...'],
        'Year': [2024, 2024]
    }
    
    df = pd.DataFrame(data)
    csv_path = tmp_path / 'neuromorphic-research_database.csv'
    df.to_csv(csv_path, index=False)
    
    return csv_path
```

### Fixture: Completed Job
```python
@pytest.fixture
def completed_job(tmp_path):
    """Create completed job with gap analysis."""
    job_dir = tmp_path / 'job_test001'
    job_dir.mkdir()
    
    # Create gap report
    report = {
        'pillars': {
            'pillar_1': {
                'requirements': {
                    'req_1': {
                        'sub_requirements': {
                            'sub_1': {'current_coverage': 0.4, 'target_coverage': 0.7}
                        }
                    }
                }
            }
        }
    }
    
    with open(job_dir / 'gap_analysis_report.json', 'w') as f:
        json.dump(report, f)
    
    # Create state
    state = {
        'schema_version': '2.0',
        'job_id': 'job_test001',
        'analysis_completed': True,
        'gap_metrics': {'total_gaps': 15}
    }
    
    with open(job_dir / 'orchestrator_state.json', 'w') as f:
        json.dump(state, f)
    
    return {'job_id': 'job_test001', 'path': job_dir}
```

---

## Deliverables

- [ ] Test suite in `tests/integration/test_incremental_mode.py`
- [ ] CLI tests (10+ scenarios)
- [ ] Dashboard API tests (8+ scenarios)
- [ ] Edge case tests (5+ scenarios)
- [ ] Performance benchmarks
- [ ] Cross-system compatibility tests
- [ ] Test documentation
- [ ] CI/CD integration (GitHub Actions)

---

## Success Criteria

✅ **Coverage:**
- 90%+ code coverage for incremental mode
- All edge cases handled gracefully
- No flaky tests

✅ **Performance:**
- Incremental mode 60-80% faster than full
- Gap extraction < 100ms
- All tests complete < 5 minutes

✅ **Quality:**
- Zero data loss scenarios
- Backward compatibility verified
- Cross-system compatibility confirmed

---

**Status:** 🟡 Blocked (requires W2-1, W2-2)  
**Assignee:** TBD  
**Estimated Start:** Week 2, Day 3  
**Estimated Completion:** Week 2, Day 5
