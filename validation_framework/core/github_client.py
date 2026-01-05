"""
GitHub Client
Provides GitHub API integration for PR/Issue validation.
"""

from typing import Dict, List, Optional
import os
import json
from pathlib import Path

# Note: requests is optional, will gracefully degrade if not available
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class GitHubClient:
    """Client for GitHub API interactions"""
    
    def __init__(self, owner: str = "BootstrapAI-mgmt", repo: str = "Literature-Review"):
        self.owner = owner
        self.repo = repo
        self.base_url = f"https://api.github.com/repos/{owner}/{repo}"
        self._token: Optional[str] = None
    
    @property
    def token(self) -> Optional[str]:
        """Get GitHub token from environment (never log or expose)"""
        if self._token is None:
            self._token = os.environ.get('GITHUB_TOKEN')
        return self._token
    
    @property
    def headers(self) -> Dict[str, str]:
        """Get request headers with auth if available"""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ValidationFramework/2.0",
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers
    
    def _request(self, endpoint: str, method: str = "GET") -> Optional[Dict]:
        """Make an API request"""
        if not REQUESTS_AVAILABLE:
            return None
        
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.request(method, url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None
    
    def get_pr_status(self, pr_number: int) -> Dict:
        """Get the status of a PR"""
        result = self._request(f"pulls/{pr_number}")
        if result:
            return {
                "number": result.get("number"),
                "state": result.get("state"),
                "merged": result.get("merged", False),
                "title": result.get("title"),
                "merged_at": result.get("merged_at"),
            }
        return {"number": pr_number, "error": "Failed to fetch PR"}
    
    def get_merged_prs(self, limit: int = 100) -> List[Dict]:
        """Get list of recently merged PRs"""
        result = self._request(f"pulls?state=closed&per_page={limit}")
        if result:
            return [
                {
                    "number": pr.get("number"),
                    "title": pr.get("title"),
                    "merged": pr.get("merged_at") is not None,
                    "merged_at": pr.get("merged_at"),
                }
                for pr in result
                if pr.get("merged_at")
            ]
        return []
    
    def is_pr_merged(self, pr_number: int) -> bool:
        """Check if a specific PR is merged"""
        status = self.get_pr_status(pr_number)
        return status.get("merged", False)
    
    def get_recent_commits(self, branch: str = "main", limit: int = 10) -> List[Dict]:
        """Get recent commits on a branch"""
        result = self._request(f"commits?sha={branch}&per_page={limit}")
        if result:
            return [
                {
                    "sha": c.get("sha", "")[:7],
                    "message": c.get("commit", {}).get("message", "").split('\n')[0],
                    "author": c.get("commit", {}).get("author", {}).get("name"),
                    "date": c.get("commit", {}).get("author", {}).get("date"),
                }
                for c in result
            ]
        return []
    
    def get_open_issues(self, labels: Optional[List[str]] = None) -> List[Dict]:
        """Get open issues, optionally filtered by labels"""
        endpoint = "issues?state=open"
        if labels:
            endpoint += f"&labels={','.join(labels)}"
        result = self._request(endpoint)
        if result:
            return [
                {
                    "number": issue.get("number"),
                    "title": issue.get("title"),
                    "labels": [l.get("name") for l in issue.get("labels", [])],
                }
                for issue in result
                if "pull_request" not in issue  # Exclude PRs
            ]
        return []
