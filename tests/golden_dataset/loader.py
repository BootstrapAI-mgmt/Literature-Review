"""
Golden Dataset Loading Utilities

Provides utilities for loading and managing golden dataset test fixtures.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

from tests.golden_dataset.schema import (
    GoldenClaim,
    GoldenVerdict,
    GoldenGap,
    GoldenDataset
)

logger = logging.getLogger(__name__)


class GoldenDatasetLoader:
    """Load and manage golden dataset files."""
    
    DEFAULT_DATA_DIR = Path(__file__).parent / "data"
    
    def __init__(self, data_dir: Optional[Path] = None, warn_on_missing: bool = True):
        """
        Initialize the loader.
        
        Args:
            data_dir: Directory containing golden dataset files.
                     Defaults to tests/golden_dataset/data/
            warn_on_missing: Whether to log a warning when files are not found.
                            Defaults to True.
        """
        self.data_dir = Path(data_dir) if data_dir else self.DEFAULT_DATA_DIR
        self.warn_on_missing = warn_on_missing
    
    def load_claims(self, filename: str = "claims.json") -> List[GoldenClaim]:
        """
        Load golden claims from JSON file.
        
        Args:
            filename: Name of claims file
            
        Returns:
            List of GoldenClaim objects (empty list if file not found)
        """
        filepath = self.data_dir / filename
        if not filepath.exists():
            if self.warn_on_missing:
                logger.warning(f"Golden dataset file not found: {filepath}")
            return []
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        claims = []
        for item in data:
            claims.append(GoldenClaim(
                claim_id=item["claim_id"],
                pillar=item["pillar"],
                sub_requirement=item["sub_requirement"],
                claim_text=item["claim_text"],
                evidence_text=item["evidence_text"],
                expected_verdict=item["expected_verdict"],
                expected_reasoning=item.get("expected_reasoning"),
                evidence_quality_scores=item.get("evidence_quality_scores", {}),
                source_paper=item.get("source_paper"),
                metadata=item.get("metadata", {})
            ))
        
        return claims
    
    def load_verdicts(self, filename: str = "verdicts.json") -> List[GoldenVerdict]:
        """
        Load golden verdicts from JSON file.
        
        Args:
            filename: Name of verdicts file
            
        Returns:
            List of GoldenVerdict objects (empty list if file not found)
        """
        filepath = self.data_dir / filename
        if not filepath.exists():
            if self.warn_on_missing:
                logger.warning(f"Golden dataset file not found: {filepath}")
            return []
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        verdicts = []
        for item in data:
            verdicts.append(GoldenVerdict(
                verdict_id=item["verdict_id"],
                claim_id=item["claim_id"],
                verdict=item["verdict"],
                reasoning=item["reasoning"],
                confidence=item["confidence"],
                judge_model=item.get("judge_model"),
                timestamp=item.get("timestamp", ""),
                metadata=item.get("metadata", {})
            ))
        
        return verdicts
    
    def load_gaps(self, filename: str = "gaps.json") -> List[GoldenGap]:
        """
        Load golden gaps from JSON file.
        
        Args:
            filename: Name of gaps file
            
        Returns:
            List of GoldenGap objects (empty list if file not found)
        """
        filepath = self.data_dir / filename
        if not filepath.exists():
            if self.warn_on_missing:
                logger.warning(f"Golden dataset file not found: {filepath}")
            return []
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        gaps = []
        for item in data:
            gaps.append(GoldenGap(
                gap_id=item["gap_id"],
                pillar=item["pillar"],
                sub_requirement=item["sub_requirement"],
                gap_description=item["gap_description"],
                severity=item["severity"],
                suggested_searches=item.get("suggested_searches", []),
                metadata=item.get("metadata", {})
            ))
        
        return gaps
    
    def load_dataset(self, name: str = "default") -> Optional[GoldenDataset]:
        """
        Load a complete golden dataset.
        
        Args:
            name: Name of the dataset (looks for {name}_dataset.json)
            
        Returns:
            GoldenDataset object or None if not found
        """
        filepath = self.data_dir / f"{name}_dataset.json"
        if not filepath.exists():
            if self.warn_on_missing:
                logger.warning(f"Golden dataset not found: {filepath}")
            return None
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        claims = [
            GoldenClaim(
                claim_id=c["claim_id"],
                pillar=c["pillar"],
                sub_requirement=c["sub_requirement"],
                claim_text=c["claim_text"],
                evidence_text=c["evidence_text"],
                expected_verdict=c["expected_verdict"],
                expected_reasoning=c.get("expected_reasoning"),
                evidence_quality_scores=c.get("evidence_quality_scores", {}),
                source_paper=c.get("source_paper"),
                metadata=c.get("metadata", {})
            )
            for c in data.get("claims", [])
        ]
        
        verdicts = [
            GoldenVerdict(
                verdict_id=v["verdict_id"],
                claim_id=v["claim_id"],
                verdict=v["verdict"],
                reasoning=v["reasoning"],
                confidence=v["confidence"],
                judge_model=v.get("judge_model"),
                timestamp=v.get("timestamp", ""),
                metadata=v.get("metadata", {})
            )
            for v in data.get("verdicts", [])
        ]
        
        gaps = [
            GoldenGap(
                gap_id=g["gap_id"],
                pillar=g["pillar"],
                sub_requirement=g["sub_requirement"],
                gap_description=g["gap_description"],
                severity=g["severity"],
                suggested_searches=g.get("suggested_searches", []),
                metadata=g.get("metadata", {})
            )
            for g in data.get("gaps", [])
        ]
        
        return GoldenDataset(
            name=data["name"],
            version=data["version"],
            description=data["description"],
            claims=claims,
            verdicts=verdicts,
            gaps=gaps,
            created_at=data.get("created_at", ""),
            metadata=data.get("metadata", {})
        )
    
    def save_dataset(self, dataset: GoldenDataset, filename: Optional[str] = None) -> Path:
        """
        Save a golden dataset to JSON file.
        
        Args:
            dataset: GoldenDataset to save
            filename: Optional filename (defaults to {name}_dataset.json)
            
        Returns:
            Path to saved file
        """
        if filename is None:
            filename = f"{dataset.name}_dataset.json"
        
        filepath = self.data_dir / filename
        
        # Ensure directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(dataset.to_dict(), f, indent=2)
        
        return filepath
    
    def list_datasets(self) -> List[str]:
        """
        List available golden datasets.
        
        Returns:
            List of dataset names
        """
        if not self.data_dir.exists():
            return []
        
        datasets = []
        for filepath in self.data_dir.glob("*_dataset.json"):
            name = filepath.stem.replace("_dataset", "")
            datasets.append(name)
        
        return datasets
