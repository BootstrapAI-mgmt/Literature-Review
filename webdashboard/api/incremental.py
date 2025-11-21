"""
Incremental Review API Endpoints for Web Dashboard

Provides REST API endpoints for incremental literature review mode:
- Create continuation jobs from previous analyses
- Extract and query gaps from completed jobs
- Score paper relevance to gaps
- Merge incremental analysis results
- Track job lineage (parent-child relationships)

Part of INCR-W2-2: Dashboard Job Continuation API
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Header, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from literature_review.utils.gap_extractor import GapExtractor
from literature_review.utils.relevance_scorer import RelevanceScorer
from literature_review.analysis.result_merger import ResultMerger

# Setup logger
logger = logging.getLogger(__name__)

# Import state manager components with error handling
try:
    from literature_review.utils.state_manager import StateManager, JobType
except (SyntaxError, ImportError) as e:
    # Fallback if state_manager has issues
    logger.warning(f"Could not import StateManager: {e}")
    StateManager = None
    JobType = None

# Create router
router = APIRouter(prefix="/api/jobs", tags=["Incremental Review"])

# Base directories - will be overridden by app configuration
BASE_DIR = Path(__file__).parent.parent.parent
WORKSPACE_DIR = BASE_DIR / "workspace"
JOBS_DIR = WORKSPACE_DIR / "jobs"


def set_workspace_dir(workspace_dir: Path):
    """Set workspace directory for testing or configuration."""
    global WORKSPACE_DIR, JOBS_DIR
    WORKSPACE_DIR = workspace_dir
    JOBS_DIR = workspace_dir / "jobs"


# Request/Response Models
class Paper(BaseModel):
    """Paper metadata for continuation job."""
    DOI: Optional[str] = None
    Title: str
    Abstract: Optional[str] = None
    Authors: Optional[str] = None
    Year: Optional[int] = None


class ContinuationRequest(BaseModel):
    """Request to create a continuation job."""
    papers: List[Paper]
    relevance_threshold: float = 0.50
    prefilter_enabled: bool = True
    job_name: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "papers": [
                    {
                        "DOI": "10.1000/paper1",
                        "Title": "New Neuromorphic Paper",
                        "Abstract": "This paper explores...",
                        "Authors": "Smith et al.",
                        "Year": 2025
                    }
                ],
                "relevance_threshold": 0.50,
                "prefilter_enabled": True,
                "job_name": "Review Update Jan 2025"
            }
        }


class RelevanceRequest(BaseModel):
    """Request to score paper relevance."""
    papers: List[Paper]
    threshold: float = 0.50
    
    class Config:
        json_schema_extra = {
            "example": {
                "papers": [
                    {
                        "DOI": "10.1000/paper1",
                        "Title": "New Paper",
                        "Abstract": "Abstract text..."
                    }
                ],
                "threshold": 0.50
            }
        }


class MergeRequest(BaseModel):
    """Request to merge incremental results."""
    incremental_job_id: str
    conflict_resolution: str = "highest_score"
    validation_mode: str = "strict"
    
    class Config:
        json_schema_extra = {
            "example": {
                "incremental_job_id": "job_20250120_143000",
                "conflict_resolution": "highest_score",
                "validation_mode": "strict"
            }
        }


# Helper functions
def get_job_dir(job_id: str) -> Path:
    """Get job directory path."""
    return JOBS_DIR / job_id


def verify_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-KEY")):
    """Verify API key - placeholder for actual auth."""
    # In production, verify against environment variable
    # For now, we'll allow requests without strict validation
    pass


# Endpoints
@router.post(
    "/{job_id}/continue",
    summary="Create continuation job",
    description="Create a new incremental analysis job from a previous completed job",
    responses={
        202: {
            "description": "Continuation job created and queued",
            "content": {
                "application/json": {
                    "example": {
                        "job_id": "job_20250120_143000",
                        "parent_job_id": "job_20250115_103000",
                        "status": "queued",
                        "papers_to_analyze": 12,
                        "papers_skipped": 18,
                        "gaps_targeted": 28,
                        "estimated_cost_usd": 3.50,
                        "estimated_duration_minutes": 15
                    }
                }
            }
        },
        404: {"description": "Parent job not found"},
        400: {"description": "Parent job incomplete or no gaps"},
        409: {"description": "Continuation already in progress"}
    }
)
async def create_continuation_job(
    job_id: str,
    request: ContinuationRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-KEY")
):
    """
    Create continuation job from previous analysis.
    
    This endpoint:
    1. Validates parent job exists and is complete
    2. Extracts gaps from parent job
    3. Filters papers by relevance (if prefilter enabled)
    4. Creates new job with parent tracking
    5. Queues job for processing
    """
    verify_api_key(x_api_key)
    
    try:
        # Validate parent job exists
        job_dir = get_job_dir(job_id)
        if not job_dir.exists():
            raise HTTPException(status_code=404, detail="Parent job not found")
        
        # Look for gap analysis report in outputs directory
        gap_report_path = job_dir / "outputs" / "gap_analysis_output" / "gap_analysis_report.json"
        if not gap_report_path.exists():
            # Try alternate location (old structure)
            gap_report_path = job_dir / "gap_analysis_report.json"
            if not gap_report_path.exists():
                raise HTTPException(
                    status_code=400,
                    detail="Parent job incomplete (no gap analysis)"
                )
        
        # Extract gaps from parent job
        extractor = GapExtractor(gap_report_path=str(gap_report_path), threshold=0.7)
        gaps = extractor.extract_gaps()
        
        if not gaps:
            raise HTTPException(
                status_code=400,
                detail="No gaps in parent job (all requirements met)"
            )
        
        # Score paper relevance
        scorer = RelevanceScorer()
        
        papers_to_analyze = []
        papers_skipped = []
        
        if request.prefilter_enabled:
            for paper in request.papers:
                paper_dict = paper.dict()
                # Use 'Title' key to match Gap structure expectations
                paper_dict['title'] = paper_dict.get('Title', '')
                paper_dict['abstract'] = paper_dict.get('Abstract', '')
                
                scores = [scorer.score_relevance(paper_dict, gap) for gap in gaps]
                max_score = max(scores) if scores else 0.0
                
                if max_score >= request.relevance_threshold:
                    papers_to_analyze.append(paper.dict())
                else:
                    papers_skipped.append(paper.dict())
        else:
            papers_to_analyze = [p.dict() for p in request.papers]
        
        # Create new job ID
        new_job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        new_job_dir = get_job_dir(new_job_id)
        new_job_dir.mkdir(parents=True, exist_ok=True)
        
        # Save papers to analyze
        papers_file = new_job_dir / "papers_to_analyze.json"
        with open(papers_file, 'w') as f:
            json.dump(papers_to_analyze, f, indent=2)
        
        # Create state
        state_file = new_job_dir / "orchestrator_state.json"
        if StateManager and JobType:
            state_manager = StateManager(str(state_file))
            state = state_manager.create_new_state(
                database_path="incremental_papers.csv",
                database_hash="",
                database_size=len(papers_to_analyze),
                job_type=JobType.INCREMENTAL,
                parent_job_id=job_id
            )
            state_manager.save_state(state)
        else:
            # Fallback: create simple state dict
            state_dict = {
                "schema_version": "2.0",
                "job_id": new_job_id,
                "parent_job_id": job_id,
                "job_type": "incremental",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "completed_at": None,
                "database_path": "incremental_papers.csv",
                "database_hash": "",
                "database_size": len(papers_to_analyze),
                "pillar_selections": ["ALL"],
                "run_mode": "ONCE"
            }
            with open(state_file, 'w') as f:
                json.dump(state_dict, f, indent=2)
        
        # Estimate cost and duration
        estimated_cost_usd = len(papers_to_analyze) * 0.25  # $0.25 per paper
        estimated_duration_minutes = len(papers_to_analyze) * 1.5  # 90 sec per paper
        
        logger.info(
            f"Created continuation job {new_job_id} from parent {job_id}: "
            f"{len(papers_to_analyze)} papers to analyze, "
            f"{len(papers_skipped)} skipped"
        )
        
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "job_id": new_job_id,
                "parent_job_id": job_id,
                "status": "queued",
                "papers_to_analyze": len(papers_to_analyze),
                "papers_skipped": len(papers_skipped),
                "gaps_targeted": len(gaps),
                "estimated_cost_usd": round(estimated_cost_usd, 2),
                "estimated_duration_minutes": int(estimated_duration_minutes)
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating continuation job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{job_id}/gaps",
    summary="Get job gaps",
    description="Extract open gaps from a completed job for targeted analysis",
    responses={
        200: {
            "description": "List of gaps with details",
            "content": {
                "application/json": {
                    "example": {
                        "job_id": "job_20250115_103000",
                        "total_gaps": 28,
                        "gap_threshold": 0.7,
                        "gaps": [],
                        "gaps_by_pillar": {
                            "pillar_1": 5,
                            "pillar_2": 8
                        }
                    }
                }
            }
        },
        404: {"description": "Job not found"},
        400: {"description": "Job incomplete (no gap analysis)"}
    }
)
async def get_job_gaps(
    job_id: str,
    threshold: float = 0.7,
    pillar_id: Optional[str] = None,
    x_api_key: Optional[str] = Header(None, alias="X-API-KEY")
):
    """
    Extract gaps from completed job.
    
    Query parameters:
    - threshold: Coverage threshold for gap identification (default: 0.7)
    - pillar_id: Filter gaps by pillar (optional)
    """
    verify_api_key(x_api_key)
    
    try:
        # Validate job exists
        job_dir = get_job_dir(job_id)
        
        # Look for gap analysis report in outputs directory
        gap_report_path = job_dir / "outputs" / "gap_analysis_output" / "gap_analysis_report.json"
        if not gap_report_path.exists():
            # Try alternate location (old structure)
            gap_report_path = job_dir / "gap_analysis_report.json"
            if not gap_report_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail="Job not found or incomplete"
                )
        
        # Extract gaps
        extractor = GapExtractor(gap_report_path=str(gap_report_path), threshold=threshold)
        gaps = extractor.extract_gaps()
        
        # Filter by pillar if requested
        if pillar_id:
            gaps = [gap for gap in gaps if gap.get('pillar_id') == pillar_id]
        
        # Aggregate by pillar
        gaps_by_pillar = {}
        for gap in gaps:
            pillar = gap.get('pillar_id', 'unknown')
            gaps_by_pillar[pillar] = gaps_by_pillar.get(pillar, 0) + 1
        
        return {
            "job_id": job_id,
            "total_gaps": len(gaps),
            "gap_threshold": threshold,
            "gaps": gaps,
            "gaps_by_pillar": gaps_by_pillar
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting gaps: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{job_id}/relevance",
    summary="Score paper relevance",
    description="Score papers' relevance to job's open gaps",
    responses={
        200: {
            "description": "Relevance scores for papers",
            "content": {
                "application/json": {
                    "example": {
                        "job_id": "job_20250115_103000",
                        "total_papers_scored": 30,
                        "papers_above_threshold": 12,
                        "papers_below_threshold": 18,
                        "threshold": 0.50,
                        "scores": [],
                        "avg_score": 0.38
                    }
                }
            }
        },
        404: {"description": "Job not found"},
        400: {"description": "No gaps in job"}
    }
)
async def score_paper_relevance(
    job_id: str,
    request: RelevanceRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-KEY")
):
    """
    Score papers' relevance to job's gaps.
    
    Analyzes each paper against all gaps and returns:
    - Overall relevance score (max across all gaps)
    - Top matched gaps
    - Statistics and recommendations
    """
    verify_api_key(x_api_key)
    
    try:
        # Load gaps
        job_dir = get_job_dir(job_id)
        
        # Look for gap analysis report in outputs directory
        gap_report_path = job_dir / "outputs" / "gap_analysis_output" / "gap_analysis_report.json"
        if not gap_report_path.exists():
            # Try alternate location (old structure)
            gap_report_path = job_dir / "gap_analysis_report.json"
            if not gap_report_path.exists():
                raise HTTPException(status_code=404, detail="Job not found")
        
        extractor = GapExtractor(gap_report_path=str(gap_report_path))
        gaps = extractor.extract_gaps()
        
        if not gaps:
            raise HTTPException(status_code=400, detail="No gaps in job")
        
        # Score papers
        scorer = RelevanceScorer()
        
        scores = []
        for paper in request.papers:
            paper_dict = paper.dict()
            paper_dict['title'] = paper_dict.get('Title', '')
            paper_dict['abstract'] = paper_dict.get('Abstract', '')
            paper_id = paper.DOI or paper.Title
            
            # Score against all gaps
            gap_scores = []
            for gap in gaps:
                score = scorer.score_relevance(paper_dict, gap)
                gap_scores.append({
                    'gap_id': gap.get('sub_requirement_id', gap.get('requirement_id', 'unknown')),
                    'score': round(score, 2),
                    'keywords_matched': gap.get('keywords', [])[:3]  # Top 3
                })
            
            # Get max score and top gaps
            max_score = max([gs['score'] for gs in gap_scores]) if gap_scores else 0.0
            top_gaps = sorted(gap_scores, key=lambda x: x['score'], reverse=True)[:3]
            
            scores.append({
                'paper_id': paper_id,
                'title': paper.Title,
                'relevance_score': round(max_score, 2),
                'top_matched_gaps': top_gaps
            })
        
        # Statistics
        above_threshold = sum(1 for s in scores if s['relevance_score'] >= request.threshold)
        below_threshold = len(scores) - above_threshold
        avg_score = sum(s['relevance_score'] for s in scores) / len(scores) if scores else 0.0
        
        return {
            "job_id": job_id,
            "total_papers_scored": len(scores),
            "papers_above_threshold": above_threshold,
            "papers_below_threshold": below_threshold,
            "threshold": request.threshold,
            "scores": scores,
            "avg_score": round(avg_score, 2),
            "recommendations": {
                "suggested_threshold": round(avg_score + 0.1, 2),
                "estimated_cost_savings": round(below_threshold / len(scores), 2) if scores else 0.0
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scoring paper relevance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{job_id}/merge",
    summary="Merge incremental results",
    description="Merge incremental analysis results into base job",
    responses={
        200: {
            "description": "Merge completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "merge_id": "merge_20250120_150000",
                        "base_job_id": "job_20250115_103000",
                        "incremental_job_id": "job_20250120_143000",
                        "status": "completed",
                        "statistics": {},
                        "conflicts": [],
                        "output_path": "/workspaces/jobs/job_20250115_103000/gap_analysis_report.json"
                    }
                }
            }
        },
        404: {"description": "Base or incremental job not found"},
        400: {"description": "Jobs incompatible"},
        409: {"description": "Merge already in progress"}
    }
)
async def merge_incremental_results(
    job_id: str,
    request: MergeRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-KEY")
):
    """
    Merge incremental job into base job.
    
    Combines results from an incremental analysis with the base job,
    handling conflicts and updating gap metrics.
    """
    verify_api_key(x_api_key)
    
    try:
        # Validate jobs exist
        base_job_dir = get_job_dir(job_id)
        incr_job_dir = get_job_dir(request.incremental_job_id)
        
        base_report_path = base_job_dir / "gap_analysis_report.json"
        incr_report_path = incr_job_dir / "gap_analysis_report.json"
        
        if not base_report_path.exists() or not incr_report_path.exists():
            raise HTTPException(
                status_code=404,
                detail="One or both jobs not found"
            )
        
        # Load reports
        with open(base_report_path, 'r') as f:
            base_report = json.load(f)
        with open(incr_report_path, 'r') as f:
            incr_report = json.load(f)
        
        # Merge reports
        merger = ResultMerger(conflict_resolution=request.conflict_resolution)
        merge_result = merger.merge_gap_analysis_results(base_report, incr_report)
        
        # Save merged report
        with open(base_report_path, 'w') as f:
            json.dump(merge_result.merged_report, f, indent=2)
        
        # Generate merge ID
        merge_id = f"merge_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Extract statistics from merge result
        statistics = merge_result.statistics
        conflicts = merge_result.conflicts
        
        logger.info(
            f"Merged incremental job {request.incremental_job_id} into {job_id}: "
            f"{statistics.get('papers_added', 0)} papers added, "
            f"{len(conflicts)} conflicts"
        )
        
        return {
            "merge_id": merge_id,
            "base_job_id": job_id,
            "incremental_job_id": request.incremental_job_id,
            "status": "completed",
            "statistics": statistics,
            "conflicts": [
                {
                    "location": c.get("location", "unknown"),
                    "type": c.get("type", "unknown"),
                    "base_value": c.get("base_value"),
                    "incremental_value": c.get("incremental_value"),
                    "resolved_value": c.get("resolved_value"),
                    "resolution_strategy": request.conflict_resolution
                }
                for c in conflicts
            ],
            "output_path": str(base_report_path)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error merging results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _extract_gap_metrics(job_dir: Path) -> Dict[str, Any]:
    """Extract gap metrics from a job's gap analysis report."""
    # Look for gap analysis report
    gap_report_path = job_dir / "outputs" / "gap_analysis_output" / "gap_analysis_report.json"
    if not gap_report_path.exists():
        # Try alternate location (old structure)
        gap_report_path = job_dir / "gap_analysis_report.json"
        if not gap_report_path.exists():
            return {
                'total_gaps': 0,
                'gaps_by_pillar': {},
                'overall_coverage': 0.0,
                'papers_analyzed': 0
            }
    
    try:
        with open(gap_report_path, 'r') as f:
            gap_report = json.load(f)
        
        # Extract gap count
        total_gaps = 0
        gaps_by_pillar = {}
        
        # Parse pillar results
        pillar_results = gap_report.get('pillar_results', {})
        for pillar_id, pillar_data in pillar_results.items():
            requirements = pillar_data.get('requirements', [])
            pillar_gaps = 0
            
            for req in requirements:
                coverage = req.get('coverage_percentage', 100.0)
                if coverage < 70.0:  # Gap threshold
                    pillar_gaps += 1
                    
                # Check sub-requirements
                for sub_req in req.get('sub_requirements', []):
                    sub_coverage = sub_req.get('coverage_percentage', 100.0)
                    if sub_coverage < 70.0:
                        pillar_gaps += 1
            
            if pillar_gaps > 0:
                gaps_by_pillar[pillar_id] = pillar_gaps
                total_gaps += pillar_gaps
        
        # Calculate overall coverage
        overall_coverage = gap_report.get('overall_summary', {}).get('overall_coverage_percentage', 0.0)
        
        # Get paper count
        papers_analyzed = gap_report.get('overall_summary', {}).get('total_papers_analyzed', 0)
        
        return {
            'total_gaps': total_gaps,
            'gaps_by_pillar': gaps_by_pillar,
            'overall_coverage': overall_coverage,
            'papers_analyzed': papers_analyzed
        }
    except Exception as e:
        logger.error(f"Error extracting gap metrics: {e}")
        return {
            'total_gaps': 0,
            'gaps_by_pillar': {},
            'overall_coverage': 0.0,
            'papers_analyzed': 0
        }


@router.get(
    "/{job_id}/lineage",
    summary="Get job lineage with metrics",
    description="Get parent-child job relationships, ancestry tree, and gap/coverage metrics over time",
    responses={
        200: {
            "description": "Job lineage information with metrics",
            "content": {
                "application/json": {
                    "example": {
                        "job_id": "job_20250120_143000",
                        "job_type": "incremental",
                        "parent_job_id": "job_20250115_103000",
                        "child_job_ids": [],
                        "ancestors": [],
                        "descendants": [],
                        "lineage_depth": 2,
                        "root_job_id": "job_20250101_100000",
                        "metrics_timeline": []
                    }
                }
            }
        },
        404: {"description": "Job not found"}
    }
)
async def get_job_lineage(
    job_id: str,
    x_api_key: Optional[str] = Header(None, alias="X-API-KEY")
):
    """
    Get parent-child job relationships with gap metrics.
    
    Returns the complete ancestry tree for a job, including:
    - Immediate parent
    - All ancestors (recursive) with gap metrics
    - Child jobs (if any)
    - Root job in the lineage
    - Metrics timeline for visualization
    """
    verify_api_key(x_api_key)
    
    try:
        # Load job state
        job_dir = get_job_dir(job_id)
        state_file = job_dir / "orchestrator_state.json"
        
        if not state_file.exists():
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Load state from JSON
        with open(state_file, 'r') as f:
            state_data = json.load(f)
        
        # Build lineage - walk up to find ancestors with metrics
        ancestors = []
        current_parent = state_data.get('parent_job_id')
        
        while current_parent:
            parent_state_file = get_job_dir(current_parent) / "orchestrator_state.json"
            if not parent_state_file.exists():
                logger.warning(f"Parent job {current_parent} state not found")
                break
            
            parent_job_dir = get_job_dir(current_parent)
            with open(parent_state_file, 'r') as f:
                parent_state = json.load(f)
            
            # Extract gap metrics for this ancestor
            gap_metrics = _extract_gap_metrics(parent_job_dir)
            
            ancestors.append({
                'job_id': parent_state.get('job_id'),
                'created_at': parent_state.get('created_at'),
                'job_type': parent_state.get('job_type', 'unknown'),
                'gap_metrics': {
                    'total_gaps': gap_metrics['total_gaps'],
                    'gaps_by_pillar': gap_metrics['gaps_by_pillar']
                },
                'overall_coverage': gap_metrics['overall_coverage'],
                'papers_analyzed': gap_metrics['papers_analyzed']
            })
            
            current_parent = parent_state.get('parent_job_id')
        
        # Reverse to get chronological order (oldest first)
        ancestors.reverse()
        
        # Add current job metrics
        current_gap_metrics = _extract_gap_metrics(job_dir)
        current_job_data = {
            'job_id': job_id,
            'created_at': state_data.get('created_at'),
            'job_type': state_data.get('job_type', 'unknown'),
            'gap_metrics': {
                'total_gaps': current_gap_metrics['total_gaps'],
                'gaps_by_pillar': current_gap_metrics['gaps_by_pillar']
            },
            'overall_coverage': current_gap_metrics['overall_coverage'],
            'papers_analyzed': current_gap_metrics['papers_analyzed']
        }
        
        # Find root job
        root_job_id = ancestors[0]['job_id'] if ancestors else job_id
        
        # Build metrics timeline (all jobs in chronological order)
        metrics_timeline = ancestors + [current_job_data]
        
        # Find child jobs by scanning all jobs
        child_job_ids = []
        if JOBS_DIR.exists():
            for child_dir in JOBS_DIR.iterdir():
                if child_dir.is_dir():
                    child_state_file = child_dir / "orchestrator_state.json"
                    if child_state_file.exists():
                        try:
                            with open(child_state_file, 'r') as f:
                                child_state = json.load(f)
                            if child_state.get('parent_job_id') == job_id:
                                child_job_ids.append(child_state.get('job_id'))
                        except:
                            pass
        
        return {
            "job_id": job_id,
            "job_type": state_data.get('job_type', 'unknown'),
            "parent_job_id": state_data.get('parent_job_id'),
            "child_job_ids": child_job_ids,
            "ancestors": ancestors,
            "descendants": [],  # Could be implemented if needed
            "lineage_depth": len(ancestors),
            "root_job_id": root_job_id,
            "metrics_timeline": metrics_timeline,
            "current_metrics": current_job_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job lineage: {e}")
        raise HTTPException(status_code=500, detail=str(e))
