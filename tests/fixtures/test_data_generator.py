#!/usr/bin/env python3
"""
Test Data Generation Utilities

Provides utilities for creating synthetic test data for integration and E2E tests.
Includes generators for:
- Version history entries
- CSV database records
- Paper metadata
- Review claims
"""

import json
import os
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import random


class TestDataGenerator:
    """Generate synthetic test data for integration tests."""
    
    def __init__(self, fixtures_dir: str = "tests/fixtures"):
        """
        Initialize the test data generator.
        
        Args:
            fixtures_dir: Directory where fixture files will be stored
        """
        self.fixtures_dir = fixtures_dir
        os.makedirs(fixtures_dir, exist_ok=True)
        
        # Sample data for realistic generation
        self.sample_titles = [
            "Neuromorphic Computing with Spiking Neural Networks",
            "Event-Based Vision for Autonomous Systems",
            "Memristive Devices for Brain-Inspired Computing",
            "Reconfigurable Hardware Accelerators for ML",
            "Photonic Neural Networks for Edge Computing"
        ]
        
        self.sample_pillars = [
            "Pillar 1: Bio-Inspired Algorithms",
            "Pillar 2: Neuromorphic Hardware",
            "Pillar 3: Event-Based Sensing",
            "Pillar 4: Energy Efficiency"
        ]
        
        self.sample_domains = [
            "Neuromorphic Computing",
            "Event-Based Vision",
            "Spiking Neural Networks",
            "Hardware Accelerators",
            "Edge AI"
        ]
    
    def create_version_history_entry(
        self,
        filename: str,
        title: Optional[str] = None,
        num_claims: int = 5,
        approved_ratio: float = 0.8,
        version_num: int = 1,
        claim_statuses: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a single version history entry.
        
        Args:
            filename: PDF filename
            title: Paper title (random if None)
            num_claims: Number of claims to generate
            approved_ratio: Ratio of approved to total claims
            version_num: Version number for this entry
            claim_statuses: Optional list of explicit statuses for each claim
            
        Returns:
            Version history entry dict
        """
        title = title or random.choice(self.sample_titles)
        
        # Generate claims
        claims = []
        
        # If explicit statuses provided, use them
        if claim_statuses:
            num_claims = len(claim_statuses)
        
        num_approved = int(num_claims * approved_ratio)
        
        for i in range(num_claims):
            pillar = random.choice(self.sample_pillars)
            
            # Use explicit status if provided, otherwise use approved_ratio
            if claim_statuses and i < len(claim_statuses):
                status = claim_statuses[i]
            else:
                status = "approved" if i < num_approved else "rejected"
            
            claim = {
                "claim_id": f"claim_{filename}_{i+1}",
                "pillar": pillar,
                "sub_requirement": f"SR {random.randint(1, 4)}.{random.randint(1, 5)}",
                "claim": f"Sample claim {i+1} for {pillar}",
                "evidence": f"Page {random.randint(1, 20)}: Sample evidence text...",
                "page_number": random.randint(1, 20),
                "status": status,
                "reasoning": f"Sample {'approval' if status == 'approved' else 'rejection'} reasoning"
            }
            
            if status == "rejected":
                claim["rejection_reason"] = f"Insufficient evidence for claim {i+1}"
            
            claims.append(claim)
        
        # Create version entry
        timestamp = (datetime.now() - timedelta(days=version_num)).isoformat()
        
        return {
            "version": version_num,
            "timestamp": timestamp,
            "review": {
                "FILENAME": filename,
                "TITLE": title,
                "CORE_DOMAIN": random.choice(self.sample_domains),
                "PUBLICATION_YEAR": random.randint(2018, 2024),
                "Requirement(s)": claims
            }
        }
    
    def create_version_history(
        self,
        filename: Optional[str] = None,
        filenames: Optional[List[str]] = None,
        num_versions: int = 1,
        num_versions_per_file: int = 1,
        approved_ratio: float = 0.8,
        claim_statuses: Optional[List[str]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Create a complete version history structure.
        
        Args:
            filename: Single PDF filename (alternative to filenames list)
            filenames: List of PDF filenames (alternative to filename)
            num_versions: Number of versions for single file mode
            num_versions_per_file: Number of versions for each file in multi-file mode
            approved_ratio: Ratio of approved claims
            claim_statuses: Optional list of explicit statuses for claims (single file mode)
            
        Returns:
            Complete version history dict
        """
        history = {}
        
        # Support both single filename and list of filenames
        if filename:
            # Single file mode
            versions = []
            num_versions_to_create = num_versions
            for v in range(1, num_versions_to_create + 1):
                entry = self.create_version_history_entry(
                    filename=filename,
                    num_claims=len(claim_statuses) if claim_statuses else random.randint(3, 8),
                    approved_ratio=approved_ratio,
                    version_num=v,
                    claim_statuses=claim_statuses
                )
                versions.append(entry)
            history[filename] = versions
        elif filenames:
            # Multi-file mode
            for fname in filenames:
                versions = []
                for v in range(1, num_versions_per_file + 1):
                    entry = self.create_version_history_entry(
                        filename=fname,
                        num_claims=random.randint(3, 8),
                        approved_ratio=approved_ratio,
                        version_num=v
                    )
                    versions.append(entry)
                history[fname] = versions
        
        return history
    
    def save_version_history(
        self,
        filepath: str,
        filenames: List[str],
        num_versions_per_file: int = 1,
        approved_ratio: float = 0.8
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Create and save a version history file.
        
        Args:
            filepath: Path where to save the file
            filenames: List of PDF filenames
            num_versions_per_file: Number of versions per file
            approved_ratio: Ratio of approved claims
            
        Returns:
            The created version history dict
        """
        history = self.create_version_history(
            filenames=filenames,
            num_versions_per_file=num_versions_per_file,
            approved_ratio=approved_ratio
        )
        
        with open(filepath, 'w') as f:
            json.dump(history, f, indent=2)
        
        return history
    
    def create_csv_row(
        self,
        filename: str,
        title: Optional[str] = None,
        num_claims: int = 5,
        approved_ratio: float = 0.8
    ) -> Dict[str, Any]:
        """
        Create a single CSV database row.
        
        Args:
            filename: PDF filename
            title: Paper title
            num_claims: Number of claims
            approved_ratio: Ratio of approved claims
            
        Returns:
            CSV row as dict
        """
        title = title or random.choice(self.sample_titles)
        
        # Generate claims for CSV format
        claims = []
        num_approved = int(num_claims * approved_ratio)
        
        for i in range(num_claims):
            pillar = random.choice(self.sample_pillars)
            status = "approved" if i < num_approved else "rejected"
            
            claim = {
                "pillar": pillar,
                "claim": f"Sample claim {i+1}",
                "evidence": f"Page {random.randint(1, 20)}",
                "status": status
            }
            claims.append(claim)
        
        return {
            "FILENAME": filename,
            "TITLE": title,
            "CORE_DOMAIN": random.choice(self.sample_domains),
            "PUBLICATION_YEAR": random.randint(2018, 2024),
            "Requirement(s)": json.dumps(claims),
            "REVIEW_TIMESTAMP": datetime.now().isoformat()
        }
    
    def create_mock_paper_metadata(
        self,
        filename: str,
        num_pages: int = 10
    ) -> Dict[str, Any]:
        """
        Create mock paper metadata.
        
        Args:
            filename: PDF filename
            num_pages: Number of pages in the paper
            
        Returns:
            Paper metadata dict
        """
        return {
            "filename": filename,
            "title": random.choice(self.sample_titles),
            "num_pages": num_pages,
            "file_size": random.randint(100000, 5000000),
            "md5": hashlib.md5(filename.encode()).hexdigest()
        }
    
    def create_mock_pillar_definitions(self) -> Dict[str, Any]:
        """
        Create mock pillar definitions.
        
        Returns:
            Pillar definitions dict
        """
        definitions = {}
        
        for pillar in self.sample_pillars:
            pillar_key = pillar.split(":")[0].replace(" ", "_")
            
            definitions[pillar_key] = {
                "name": pillar,
                "description": f"Sample description for {pillar}",
                "requirements": {
                    "REQ-001": [
                        "Sub-requirement 1",
                        "Sub-requirement 2"
                    ],
                    "REQ-002": [
                        "Sub-requirement 3",
                        "Sub-requirement 4"
                    ]
                }
            }
        
        return definitions
    
    def create_rejected_claims_scenario(
        self,
        filename: str,
        num_rejected: int = 3
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Create a version history with rejected claims for DRA testing.
        
        Args:
            filename: PDF filename
            num_rejected: Number of rejected claims
            
        Returns:
            Version history with rejected claims
        """
        # Create initial version with rejections
        entry = self.create_version_history_entry(
            filename=filename,
            num_claims=num_rejected + 2,  # Some approved, some rejected
            approved_ratio=0.4,  # 40% approval rate to trigger DRA
            version_num=1
        )
        
        return {filename: [entry]}
    
    def cleanup_fixtures(self):
        """Remove all generated fixture files."""
        import shutil
        if os.path.exists(self.fixtures_dir):
            for item in os.listdir(self.fixtures_dir):
                item_path = os.path.join(self.fixtures_dir, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path) and item in ['sample_papers', 'version_history_fixtures', 'csv_fixtures']:
                    shutil.rmtree(item_path)


# Helper functions for quick fixture creation

def create_minimal_version_history() -> Dict[str, List[Dict[str, Any]]]:
    """Create a minimal version history for quick tests."""
    generator = TestDataGenerator()
    return generator.create_version_history(
        filenames=["test_paper_1.pdf"],
        num_versions_per_file=1,
        approved_ratio=1.0  # All approved
    )


def create_rejected_scenario() -> Dict[str, List[Dict[str, Any]]]:
    """Create a scenario with rejected claims for DRA tests."""
    generator = TestDataGenerator()
    return generator.create_rejected_claims_scenario(
        filename="test_paper_rejected.pdf",
        num_rejected=3
    )


def create_multi_version_history() -> Dict[str, List[Dict[str, Any]]]:
    """Create a version history with multiple versions."""
    generator = TestDataGenerator()
    return generator.create_version_history(
        filenames=["test_paper_multi.pdf"],
        num_versions_per_file=3,
        approved_ratio=0.7
    )
