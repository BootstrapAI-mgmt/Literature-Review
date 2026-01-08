"""
E2E Orchestrator
Manages end-to-end test execution including state capture, workflow triggering,
and result verification.
"""

import os
import time
import json
from pathlib import Path
from typing import Dict, Optional, List, Any
from datetime import datetime

# Import from tier2 payloader
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from tier2.payloader import Payloader, PayloaderError, REQUESTS_AVAILABLE


class E2ETestContext:
    """Context for an E2E test execution"""
    
    def __init__(self, test_name: str, repo_path: Path = None):
        self.test_name = test_name
        self.repo_path = repo_path or Path.cwd()
        self.start_time = datetime.now()
        self.end_time = None
        self.baseline_state: Dict[str, Any] = {}
        self.final_state: Dict[str, Any] = {}
        self.events: List[Dict] = []
        self.status = "pending"
        self.error = None
    
    def log_event(self, event_type: str, details: dict = None):
        """Log an event during test execution"""
        self.events.append({
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "details": details or {}
        })
    
    def complete(self, status: str, error: str = None):
        """Mark test as complete"""
        self.end_time = datetime.now()
        self.status = status
        self.error = error
    
    def duration_seconds(self) -> float:
        """Get test duration in seconds"""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for reporting"""
        return {
            "test_name": self.test_name,
            "status": self.status,
            "duration_seconds": self.duration_seconds(),
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "events": self.events,
            "error": self.error
        }


class StateCapture:
    """Captures document state for before/after comparison"""
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
    
    def capture_document(self, doc_path: str) -> Dict:
        """Capture current state of a document"""
        full_path = self.repo_path / doc_path
        if not full_path.exists():
            return {"exists": False, "path": doc_path}
        
        content = full_path.read_text(encoding='utf-8')
        stat = full_path.stat()
        
        return {
            "exists": True,
            "path": doc_path,
            "content_hash": hash(content),
            "content_length": len(content),
            "mtime": stat.st_mtime,
            "mtime_iso": datetime.fromtimestamp(stat.st_mtime).isoformat()
        }
    
    def capture_multiple(self, doc_paths: List[str]) -> Dict[str, Dict]:
        """Capture state of multiple documents"""
        return {path: self.capture_document(path) for path in doc_paths}
    
    def compare_states(self, before: Dict, after: Dict) -> Dict:
        """Compare two captured states"""
        changes = {
            "modified": [],
            "unchanged": [],
            "created": [],
            "deleted": []
        }
        
        all_paths = set(before.keys()) | set(after.keys())
        
        for path in all_paths:
            before_state = before.get(path, {"exists": False})
            after_state = after.get(path, {"exists": False})
            
            if not before_state["exists"] and after_state["exists"]:
                changes["created"].append(path)
            elif before_state["exists"] and not after_state["exists"]:
                changes["deleted"].append(path)
            elif before_state.get("content_hash") != after_state.get("content_hash"):
                changes["modified"].append(path)
            else:
                changes["unchanged"].append(path)
        
        return changes


class E2EOrchestrator:
    """Orchestrates end-to-end test execution"""
    
    # Key documents to monitor
    MONITORED_DOCS = [
        "docs/MASTER_ARCHITECTURE_BLUEPRINT.md",
        "docs/MASTER_REPOSITORY_ROADMAP.md",
        "task-cards/OPERATIONALIZATION_WAVE_INDEX.md",
    ]
    
    def __init__(self, repo_path: Path = None, n8n_timeout: int = 60):
        self.repo_path = repo_path or Path.cwd()
        self.payloader = Payloader(timeout=30)
        self.state_capture = StateCapture(self.repo_path)
        self.n8n_timeout = n8n_timeout
        self.contexts: List[E2ETestContext] = []
    
    def create_context(self, test_name: str) -> E2ETestContext:
        """Create a new test context"""
        ctx = E2ETestContext(test_name, self.repo_path)
        self.contexts.append(ctx)
        return ctx
    
    def capture_baseline(self, ctx: E2ETestContext, doc_paths: List[str] = None):
        """Capture baseline state before test"""
        paths = doc_paths or self.MONITORED_DOCS
        ctx.baseline_state = self.state_capture.capture_multiple(paths)
        ctx.log_event("baseline_captured", {"documents": len(paths)})
    
    def capture_final(self, ctx: E2ETestContext, doc_paths: List[str] = None):
        """Capture final state after test"""
        paths = doc_paths or self.MONITORED_DOCS
        ctx.final_state = self.state_capture.capture_multiple(paths)
        ctx.log_event("final_captured", {"documents": len(paths)})
    
    def trigger_github_push(self, ctx: E2ETestContext, modified_files: List[str]) -> Dict:
        """Trigger a GitHub push event via n8n"""
        ctx.log_event("trigger_push", {"files": modified_files})
        
        try:
            response = self.payloader.trigger_github_push(modified_files)
            ctx.log_event("trigger_response", response)
            return response
        except PayloaderError as e:
            ctx.log_event("trigger_error", {"error": str(e)})
            raise
    
    def wait_for_processing(self, ctx: E2ETestContext, timeout: int = None) -> bool:
        """Wait for n8n workflow to complete processing"""
        timeout = timeout or self.n8n_timeout
        ctx.log_event("waiting_start", {"timeout": timeout})
        
        result = self.payloader.wait_for_execution(timeout=timeout)
        
        if result:
            ctx.log_event("waiting_complete", result)
            return True
        else:
            ctx.log_event("waiting_timeout", {"timeout": timeout})
            return False
    
    def verify_changes(self, ctx: E2ETestContext) -> Dict:
        """Verify document changes after test"""
        changes = self.state_capture.compare_states(
            ctx.baseline_state, 
            ctx.final_state
        )
        ctx.log_event("changes_verified", changes)
        return changes
    
    def run_e2e_test(
        self, 
        test_name: str, 
        trigger_files: List[str],
        expected_changes: List[str] = None,
        timeout: int = None
    ) -> E2ETestContext:
        """
        Run a complete E2E test scenario.
        
        Args:
            test_name: Name of the test
            trigger_files: Files to include in mock push event
            expected_changes: Documents expected to change (optional)
            timeout: Max wait time for processing
        
        Returns:
            Test context with results
        """
        ctx = self.create_context(test_name)
        
        try:
            # 1. Capture baseline
            self.capture_baseline(ctx)
            
            # 2. Trigger workflow
            self.trigger_github_push(ctx, trigger_files)
            
            # 3. Wait for processing
            self.wait_for_processing(ctx, timeout)
            
            # 4. Capture final state
            self.capture_final(ctx)
            
            # 5. Verify changes
            changes = self.verify_changes(ctx)
            
            # 6. Evaluate results
            if expected_changes:
                actual_changed = set(changes["modified"] + changes["created"])
                expected_set = set(expected_changes)
                if expected_set.issubset(actual_changed):
                    ctx.complete("passed")
                else:
                    missing = expected_set - actual_changed
                    ctx.complete("failed", f"Expected changes not found: {missing}")
            else:
                ctx.complete("passed")
            
        except PayloaderError as e:
            ctx.complete("skipped", f"n8n not available: {e}")
        except Exception as e:
            ctx.complete("error", str(e))
        
        return ctx
    
    def generate_report(self) -> Dict:
        """Generate summary report of all tests"""
        return {
            "total": len(self.contexts),
            "passed": sum(1 for c in self.contexts if c.status == "passed"),
            "failed": sum(1 for c in self.contexts if c.status == "failed"),
            "skipped": sum(1 for c in self.contexts if c.status == "skipped"),
            "error": sum(1 for c in self.contexts if c.status == "error"),
            "tests": [c.to_dict() for c in self.contexts]
        }


def check_n8n_available() -> bool:
    """Quick check if n8n Cloud is accessible"""
    if not REQUESTS_AVAILABLE:
        return False
    
    payloader = Payloader(timeout=10)
    try:
        # Try the github-doc-trigger endpoint with a test payload
        payloader.send_to_webhook("/github-doc-trigger", {"test": True})
        return True
    except PayloaderError as e:
        # Webhook errors (404, 500, etc.) mean n8n IS available
        # Only connection errors mean n8n is unavailable
        if "Webhook error" in str(e):
            return True
        return False

