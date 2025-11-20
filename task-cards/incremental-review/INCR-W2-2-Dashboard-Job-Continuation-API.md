# INCR-W2-2: Dashboard Job Continuation API

**Wave:** 2 (Integration)  
**Priority:** 🔴 Critical  
**Effort:** 8-10 hours  
**Status:** 🟡 Blocked (requires Wave 1)  
**Assignable:** Full-Stack Developer

---

## Overview

Implement REST API endpoints in the web dashboard to support incremental review mode, including job continuation, gap-targeted paper import, and parent-child job tracking. This is the backend counterpart to INCR-W2-1 (CLI mode) and enables the Dashboard UI (INCR-W2-3) to offer incremental analysis.

---

## Dependencies

**Prerequisites:**
- ✅ INCR-W1-1 (Gap Extraction Engine)
- ✅ INCR-W1-2 (Paper Relevance Assessor)
- ✅ INCR-W1-3 (Result Merger Utility)
- ✅ INCR-W1-5 (Orchestrator State Manager)

**Blocks:**
- INCR-W2-3 (Dashboard Continuation UI)
- INCR-W3-1 (Dashboard Job Genealogy Visualization)

---

## Scope

### Included
- [x] `/api/jobs/<job_id>/continue` - Create continuation job
- [x] `/api/jobs/<job_id>/gaps` - Get open gaps from previous job
- [x] `/api/jobs/<job_id>/relevance` - Score papers against gaps
- [x] `/api/jobs/<job_id>/merge` - Merge incremental results
- [x] `/api/jobs/<job_id>/lineage` - Get parent-child job relationships
- [x] Job state persistence with parent tracking
- [x] OpenAPI/Swagger documentation
- [x] Unit and integration tests

### Excluded
- ❌ Real-time job progress (use existing polling)
- ❌ Concurrent job merging (single merge at a time)
- ❌ Rollback endpoints (manual rollback via file restore)

---

## Technical Specification

### API Endpoints

#### 1. POST /api/jobs/<job_id>/continue

**Description:** Create a continuation job from a previous analysis.

**Request:**
```json
{
  "papers": [
    {
      "DOI": "10.1000/paper1",
      "Title": "New Neuromorphic Paper",
      "Abstract": "...",
      "Authors": "Smith et al.",
      "Year": 2025
    }
  ],
  "relevance_threshold": 0.50,
  "prefilter_enabled": true,
  "job_name": "Review Update Jan 2025"
}
```

**Response (202 Accepted):**
```json
{
  "job_id": "job_20250120_143000",
  "parent_job_id": "job_20250115_103000",
  "status": "queued",
  "papers_to_analyze": 12,
  "papers_skipped": 18,
  "gaps_targeted": 28,
  "estimated_cost_usd": 3.50,
  "estimated_duration_minutes": 15
}
```

**Errors:**
- `404` - Parent job not found
- `400` - Parent job incomplete or no gaps
- `409` - Continuation already in progress

---

#### 2. GET /api/jobs/<job_id>/gaps

**Description:** Extract open gaps from a completed job.

**Query Parameters:**
- `threshold` (float, default: 0.7) - Coverage threshold for gap identification
- `pillar_id` (str, optional) - Filter gaps by pillar

**Response (200 OK):**
```json
{
  "job_id": "job_20250115_103000",
  "total_gaps": 28,
  "gap_threshold": 0.7,
  "gaps": [
    {
      "pillar_id": "pillar_1",
      "pillar_name": "Neuromorphic Hardware",
      "requirement_id": "req_1_2",
      "sub_requirement_id": "sub_1_2_3",
      "current_coverage": 0.45,
      "target_coverage": 0.70,
      "gap_size": 0.25,
      "keywords": ["spike timing", "STDP"],
      "evidence_count": 3,
      "relevant_papers": [
        {
          "DOI": "10.1000/paper1",
          "Title": "...",
          "relevance_score": 0.65
        }
      ]
    }
  ],
  "gaps_by_pillar": {
    "pillar_1": 5,
    "pillar_2": 8,
    "pillar_3": 15
  }
}
```

**Errors:**
- `404` - Job not found
- `400` - Job incomplete (no gap analysis)

---

#### 3. POST /api/jobs/<job_id>/relevance

**Description:** Score papers' relevance to open gaps.

**Request:**
```json
{
  "papers": [
    {
      "DOI": "10.1000/paper1",
      "Title": "New Paper",
      "Abstract": "..."
    }
  ],
  "threshold": 0.50
}
```

**Response (200 OK):**
```json
{
  "job_id": "job_20250115_103000",
  "total_papers_scored": 30,
  "papers_above_threshold": 12,
  "papers_below_threshold": 18,
  "threshold": 0.50,
  "scores": [
    {
      "paper_id": "10.1000/paper1",
      "title": "New Paper",
      "relevance_score": 0.72,
      "top_matched_gaps": [
        {
          "gap_id": "sub_1_2_3",
          "score": 0.72,
          "keywords_matched": ["spike timing"]
        }
      ]
    }
  ],
  "avg_score": 0.38,
  "recommendations": {
    "suggested_threshold": 0.55,
    "estimated_cost_savings": 0.60
  }
}
```

**Errors:**
- `404` - Job not found
- `400` - No gaps in job

---

#### 4. POST /api/jobs/<job_id>/merge

**Description:** Merge incremental analysis results into base job.

**Request:**
```json
{
  "incremental_job_id": "job_20250120_143000",
  "conflict_resolution": "highest_score",
  "validation_mode": "strict"
}
```

**Response (200 OK):**
```json
{
  "merge_id": "merge_20250120_150000",
  "base_job_id": "job_20250115_103000",
  "incremental_job_id": "job_20250120_143000",
  "status": "completed",
  "statistics": {
    "pillars_updated": 6,
    "requirements_updated": 15,
    "papers_added": 12,
    "evidence_merged": 38,
    "conflicts_resolved": 3,
    "gaps_closed": 5
  },
  "conflicts": [
    {
      "location": "pillar_1.req_1_2.sub_1_2_3",
      "type": "coverage_conflict",
      "base_value": 0.45,
      "incremental_value": 0.52,
      "resolved_value": 0.52,
      "resolution_strategy": "highest_score"
    }
  ],
  "output_path": "/workspaces/job_20250115_103000/gap_analysis_report.json"
}
```

**Errors:**
- `404` - Base or incremental job not found
- `400` - Jobs incompatible (different databases, pillars)
- `409` - Merge already in progress

---

#### 5. GET /api/jobs/<job_id>/lineage

**Description:** Get parent-child job relationships.

**Response (200 OK):**
```json
{
  "job_id": "job_20250120_143000",
  "job_type": "incremental",
  "parent_job_id": "job_20250115_103000",
  "child_job_ids": [],
  "ancestors": [
    {
      "job_id": "job_20250101_100000",
      "created_at": "2025-01-01T10:00:00",
      "job_type": "full"
    },
    {
      "job_id": "job_20250115_103000",
      "created_at": "2025-01-15T10:30:00",
      "job_type": "incremental"
    }
  ],
  "descendants": [],
  "lineage_depth": 2,
  "root_job_id": "job_20250101_100000"
}
```

**Errors:**
- `404` - Job not found

---

### Implementation

Create `webdashboard/api/incremental.py`:

```python
"""
Incremental Review API Endpoints for Web Dashboard
"""

from flask import Blueprint, request, jsonify
from pathlib import Path
import json
import os
from typing import Dict, Any, List, Optional

from literature_review.utils.gap_extractor import GapExtractor
from literature_review.utils.relevance_scorer import RelevanceScorer
from literature_review.utils.result_merger import ResultMerger
from literature_review.utils.state_manager import StateManager, JobType

incremental_bp = Blueprint('incremental', __name__, url_prefix='/api/jobs')


@incremental_bp.route('/<job_id>/continue', methods=['POST'])
def create_continuation_job(job_id: str):
    """
    Create continuation job from previous analysis.
    
    POST /api/jobs/{job_id}/continue
    """
    try:
        # Validate parent job exists
        job_dir = Path(f'/workspaces/jobs/{job_id}')
        if not job_dir.exists():
            return jsonify({'error': 'Parent job not found'}), 404
        
        gap_report_path = job_dir / 'gap_analysis_report.json'
        if not gap_report_path.exists():
            return jsonify({'error': 'Parent job incomplete (no gap analysis)'}), 400
        
        # Load request data
        data = request.get_json()
        papers = data.get('papers', [])
        relevance_threshold = data.get('relevance_threshold', 0.50)
        prefilter_enabled = data.get('prefilter_enabled', True)
        job_name = data.get('job_name', f'Continuation of {job_id}')
        
        if not papers:
            return jsonify({'error': 'No papers provided'}), 400
        
        # Extract gaps from parent job
        extractor = GapExtractor(gap_report_path=str(gap_report_path), threshold=0.7)
        gaps = extractor.extract_gaps()
        
        if not gaps:
            return jsonify({'error': 'No gaps in parent job (all requirements met)'}), 400
        
        # Score paper relevance
        scorer = RelevanceScorer()
        
        papers_to_analyze = []
        papers_skipped = []
        
        if prefilter_enabled:
            for paper in papers:
                scores = [scorer.score_relevance(paper, gap) for gap in gaps]
                max_score = max(scores) if scores else 0.0
                
                if max_score >= relevance_threshold:
                    papers_to_analyze.append(paper)
                else:
                    papers_skipped.append(paper)
        else:
            papers_to_analyze = papers
        
        # Create new job
        from datetime import datetime
        new_job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        new_job_dir = Path(f'/workspaces/jobs/{new_job_id}')
        new_job_dir.mkdir(parents=True, exist_ok=True)
        
        # Save papers to analyze
        with open(new_job_dir / 'papers_to_analyze.json', 'w') as f:
            json.dump(papers_to_analyze, f, indent=2)
        
        # Create state
        state_manager = StateManager(str(new_job_dir / 'orchestrator_state.json'))
        state = state_manager.create_new_state(
            database_path='incremental_papers.csv',
            database_hash='',
            database_size=len(papers_to_analyze),
            job_type=JobType.INCREMENTAL,
            parent_job_id=job_id
        )
        state_manager.save_state(state)
        
        # Estimate cost
        estimated_cost_usd = len(papers_to_analyze) * 0.25  # $0.25 per paper
        estimated_duration_minutes = len(papers_to_analyze) * 1.5  # 90 sec per paper
        
        # Queue job for analysis (background worker would pick this up)
        # For now, just return job info
        
        return jsonify({
            'job_id': new_job_id,
            'parent_job_id': job_id,
            'status': 'queued',
            'papers_to_analyze': len(papers_to_analyze),
            'papers_skipped': len(papers_skipped),
            'gaps_targeted': len(gaps),
            'estimated_cost_usd': round(estimated_cost_usd, 2),
            'estimated_duration_minutes': int(estimated_duration_minutes)
        }), 202
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@incremental_bp.route('/<job_id>/gaps', methods=['GET'])
def get_job_gaps(job_id: str):
    """
    Extract gaps from completed job.
    
    GET /api/jobs/{job_id}/gaps?threshold=0.7&pillar_id=pillar_1
    """
    try:
        # Validate job exists
        job_dir = Path(f'/workspaces/jobs/{job_id}')
        gap_report_path = job_dir / 'gap_analysis_report.json'
        
        if not gap_report_path.exists():
            return jsonify({'error': 'Job not found or incomplete'}), 404
        
        # Get query params
        threshold = float(request.args.get('threshold', 0.7))
        pillar_filter = request.args.get('pillar_id')
        
        # Extract gaps
        extractor = GapExtractor(gap_report_path=str(gap_report_path), threshold=threshold)
        gaps = extractor.extract_gaps()
        
        # Filter by pillar if requested
        if pillar_filter:
            gaps = [gap for gap in gaps if gap['pillar_id'] == pillar_filter]
        
        # Aggregate by pillar
        gaps_by_pillar = {}
        for gap in gaps:
            pillar_id = gap['pillar_id']
            gaps_by_pillar[pillar_id] = gaps_by_pillar.get(pillar_id, 0) + 1
        
        return jsonify({
            'job_id': job_id,
            'total_gaps': len(gaps),
            'gap_threshold': threshold,
            'gaps': gaps,
            'gaps_by_pillar': gaps_by_pillar
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@incremental_bp.route('/<job_id>/relevance', methods=['POST'])
def score_paper_relevance(job_id: str):
    """
    Score papers' relevance to job's gaps.
    
    POST /api/jobs/{job_id}/relevance
    """
    try:
        # Load gaps
        job_dir = Path(f'/workspaces/jobs/{job_id}')
        gap_report_path = job_dir / 'gap_analysis_report.json'
        
        if not gap_report_path.exists():
            return jsonify({'error': 'Job not found'}), 404
        
        extractor = GapExtractor(gap_report_path=str(gap_report_path))
        gaps = extractor.extract_gaps()
        
        if not gaps:
            return jsonify({'error': 'No gaps in job'}), 400
        
        # Get papers from request
        data = request.get_json()
        papers = data.get('papers', [])
        threshold = data.get('threshold', 0.50)
        
        # Score papers
        scorer = RelevanceScorer()
        
        scores = []
        for paper in papers:
            paper_id = paper.get('DOI', paper.get('Title'))
            
            # Score against all gaps
            gap_scores = []
            for gap in gaps:
                score = scorer.score_relevance(paper, gap)
                gap_scores.append({
                    'gap_id': gap['sub_requirement_id'],
                    'score': score,
                    'keywords_matched': gap['keywords'][:3]  # Top 3
                })
            
            # Get max score and top gaps
            max_score = max([gs['score'] for gs in gap_scores]) if gap_scores else 0.0
            top_gaps = sorted(gap_scores, key=lambda x: x['score'], reverse=True)[:3]
            
            scores.append({
                'paper_id': paper_id,
                'title': paper.get('Title', ''),
                'relevance_score': round(max_score, 2),
                'top_matched_gaps': top_gaps
            })
        
        # Statistics
        above_threshold = sum(1 for s in scores if s['relevance_score'] >= threshold)
        below_threshold = len(scores) - above_threshold
        avg_score = sum(s['relevance_score'] for s in scores) / len(scores) if scores else 0.0
        
        return jsonify({
            'job_id': job_id,
            'total_papers_scored': len(scores),
            'papers_above_threshold': above_threshold,
            'papers_below_threshold': below_threshold,
            'threshold': threshold,
            'scores': scores,
            'avg_score': round(avg_score, 2),
            'recommendations': {
                'suggested_threshold': round(avg_score + 0.1, 2),
                'estimated_cost_savings': round(below_threshold / len(scores), 2) if scores else 0.0
            }
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@incremental_bp.route('/<job_id>/merge', methods=['POST'])
def merge_incremental_results(job_id: str):
    """
    Merge incremental job into base job.
    
    POST /api/jobs/{job_id}/merge
    """
    try:
        # Get request data
        data = request.get_json()
        incremental_job_id = data.get('incremental_job_id')
        conflict_resolution = data.get('conflict_resolution', 'highest_score')
        
        # Validate jobs exist
        base_job_dir = Path(f'/workspaces/jobs/{job_id}')
        incr_job_dir = Path(f'/workspaces/jobs/{incremental_job_id}')
        
        base_report_path = base_job_dir / 'gap_analysis_report.json'
        incr_report_path = incr_job_dir / 'gap_analysis_report.json'
        
        if not base_report_path.exists() or not incr_report_path.exists():
            return jsonify({'error': 'One or both jobs not found'}), 404
        
        # Merge reports
        merger = ResultMerger()
        merged_report = merger.merge_reports(
            base_report_path=str(base_report_path),
            incremental_report_path=str(incr_report_path),
            conflict_resolution=conflict_resolution
        )
        
        # Save merged report
        merger.save_report(merged_report, str(base_report_path))
        
        # Get merge statistics
        from datetime import datetime
        merge_id = f"merge_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # TODO: Compute actual statistics from merge
        statistics = {
            'pillars_updated': 6,
            'requirements_updated': 15,
            'papers_added': 12,
            'evidence_merged': 38,
            'conflicts_resolved': 0,
            'gaps_closed': 0
        }
        
        return jsonify({
            'merge_id': merge_id,
            'base_job_id': job_id,
            'incremental_job_id': incremental_job_id,
            'status': 'completed',
            'statistics': statistics,
            'conflicts': [],
            'output_path': str(base_report_path)
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@incremental_bp.route('/<job_id>/lineage', methods=['GET'])
def get_job_lineage(job_id: str):
    """
    Get parent-child job relationships.
    
    GET /api/jobs/{job_id}/lineage
    """
    try:
        # Load job state
        job_dir = Path(f'/workspaces/jobs/{job_id}')
        state_file = job_dir / 'orchestrator_state.json'
        
        if not state_file.exists():
            return jsonify({'error': 'Job not found'}), 404
        
        state_manager = StateManager(str(state_file))
        state = state_manager.load_state()
        
        # Build lineage
        ancestors = []
        current_parent = state.parent_job_id
        
        while current_parent:
            parent_state_file = Path(f'/workspaces/jobs/{current_parent}/orchestrator_state.json')
            if not parent_state_file.exists():
                break
            
            parent_manager = StateManager(str(parent_state_file))
            parent_state = parent_manager.load_state()
            
            ancestors.append({
                'job_id': parent_state.job_id,
                'created_at': parent_state.created_at,
                'job_type': parent_state.job_type.value
            })
            
            current_parent = parent_state.parent_job_id
        
        # Find root
        root_job_id = ancestors[-1]['job_id'] if ancestors else job_id
        
        return jsonify({
            'job_id': job_id,
            'job_type': state.job_type.value,
            'parent_job_id': state.parent_job_id,
            'child_job_ids': [],  # TODO: Implement child tracking
            'ancestors': ancestors,
            'descendants': [],
            'lineage_depth': len(ancestors),
            'root_job_id': root_job_id
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### Register Blueprint

Update `webdashboard/app.py`:

```python
# webdashboard/app.py

from webdashboard.api.incremental import incremental_bp

app.register_blueprint(incremental_bp)
```

---

## Testing Strategy

### Unit Tests

Create `tests/webui/test_incremental_api.py`:

```python
import pytest
import json
from webdashboard import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_get_job_gaps(client, tmp_path):
    """Test GET /api/jobs/<job_id>/gaps."""
    # Create mock job
    job_id = "test_job_001"
    # ... setup mock gap report ...
    
    response = client.get(f'/api/jobs/{job_id}/gaps')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'total_gaps' in data
    assert 'gaps' in data

def test_score_paper_relevance(client):
    """Test POST /api/jobs/<job_id>/relevance."""
    job_id = "test_job_001"
    
    payload = {
        'papers': [
            {'DOI': '10.1000/test1', 'Title': 'Test Paper', 'Abstract': '...'}
        ],
        'threshold': 0.50
    }
    
    response = client.post(
        f'/api/jobs/{job_id}/relevance',
        data=json.dumps(payload),
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'scores' in data

def test_create_continuation_job(client):
    """Test POST /api/jobs/<job_id>/continue."""
    job_id = "test_job_001"
    
    payload = {
        'papers': [{'Title': 'New Paper', 'Abstract': '...'}],
        'relevance_threshold': 0.50,
        'prefilter_enabled': True
    }
    
    response = client.post(
        f'/api/jobs/{job_id}/continue',
        data=json.dumps(payload),
        content_type='application/json'
    )
    
    assert response.status_code == 202
    data = json.loads(response.data)
    assert 'job_id' in data
    assert 'parent_job_id' in data
    assert data['parent_job_id'] == job_id
```

---

## Deliverables

- [ ] `webdashboard/api/incremental.py` with 5 endpoints
- [ ] Blueprint registration in `app.py`
- [ ] OpenAPI/Swagger documentation
- [ ] Unit tests in `tests/webui/test_incremental_api.py`
- [ ] Integration tests
- [ ] API documentation in README

---

## Success Criteria

✅ **Functional:**
- All 5 endpoints work correctly
- Job continuation creates child job
- Gap extraction returns accurate gaps
- Relevance scoring uses ML model
- Merge updates base job atomically

✅ **Quality:**
- Unit tests pass (90% coverage)
- API documented (OpenAPI spec)
- Error handling comprehensive

✅ **Performance:**
- <500ms response time (non-analysis endpoints)
- Handles 100+ papers in relevance scoring

---

**Status:** 🟡 Blocked (requires Wave 1 completion)  
**Assignee:** TBD  
**Estimated Start:** Week 2, Day 1  
**Estimated Completion:** Week 2, Day 3
