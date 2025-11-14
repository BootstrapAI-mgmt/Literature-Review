"""
Orchestrator Integration Module

Coordinates Journal-Reviewer, Deep-Reviewer, Judge, and CSV sync.
Implements evidence triangulation across multiple reviewers.

Version: 1.0 (Task Card #9: Orchestrator Integration Tests)
"""

import json
import os
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path


class Orchestrator:
    """
    Orchestrates the literature review workflow.
    
    Coordinates:
    - Journal-Reviewer: Initial paper analysis
    - Deep-Reviewer: Detailed evidence extraction
    - Judge: Claim validation
    - CSV Sync: Database updates
    - Evidence Triangulation: Cross-reviewer aggregation
    """
    
    def __init__(self, version_history_path: str, csv_database_path: Optional[str] = None):
        """
        Initialize Orchestrator.
        
        Args:
            version_history_path: Path to review_version_history.json
            csv_database_path: Path to CSV database (optional)
        """
        self.version_history_path = version_history_path
        self.csv_database_path = csv_database_path
        
    def process_paper(self, pdf_path: str) -> bool:
        """
        Process a paper through the full workflow.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # This is a simplified implementation for testing
            # In production, this would call the actual reviewer modules
            
            # For now, just verify the file exists
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF not found: {pdf_path}")
            
            # Load version history
            with open(self.version_history_path, 'r') as f:
                version_history = json.load(f)
            
            # Create a basic entry if processing is successful
            filename = os.path.basename(pdf_path)
            
            if filename not in version_history:
                version_history[filename] = []
            
            # Add a version entry (simulated)
            version_history[filename].append({
                'timestamp': datetime.now().isoformat(),
                'review': {
                    'FILENAME': filename,
                    'TITLE': 'Processed Paper',
                    'source': 'journal',
                    'Requirement(s)': []
                }
            })
            
            # Save updated history
            with open(self.version_history_path, 'w') as f:
                json.dump(version_history, f, indent=2)
                
            return True
            
        except Exception as e:
            print(f"Error processing paper: {e}")
            return False
    
    def run_judge(self) -> bool:
        """
        Run Judge on pending claims in version history.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load version history
            with open(self.version_history_path, 'r') as f:
                version_history = json.load(f)
            
            # Process pending claims
            for filename, versions in version_history.items():
                if not versions:
                    continue
                    
                latest_version = versions[-1]
                claims = latest_version.get('review', {}).get('Requirement(s)', [])
                
                # Find pending claims
                has_pending = any(
                    claim.get('status') == 'pending_judge_review' 
                    for claim in claims
                )
                
                if has_pending:
                    # Create a new version with updated statuses
                    new_version = {
                        'timestamp': datetime.now().isoformat(),
                        'review': latest_version['review'].copy()
                    }
                    
                    # Update claim statuses (simplified - real implementation would call Judge)
                    for claim in new_version['review']['Requirement(s)']:
                        if claim.get('status') == 'pending_judge_review':
                            # Simple logic: approve if has evidence
                            if claim.get('evidence'):
                                claim['status'] = 'approved'
                                claim['judge_notes'] = 'Approved by automated judge'
                            else:
                                claim['status'] = 'rejected'
                                claim['judge_notes'] = 'Rejected - insufficient evidence'
                    
                    versions.append(new_version)
            
            # Save updated history
            with open(self.version_history_path, 'w') as f:
                json.dump(version_history, f, indent=2)
                
            return True
            
        except (json.JSONDecodeError, ValueError) as e:
            raise e
        except Exception as e:
            print(f"Error running judge: {e}")
            return False
    
    def sync_to_csv(self) -> bool:
        """
        Sync approved claims to CSV database.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.csv_database_path:
                raise ValueError("CSV database path not set")
            
            # Load version history
            with open(self.version_history_path, 'r') as f:
                version_history = json.load(f)
            
            # Collect approved claims
            rows = []
            for filename, versions in version_history.items():
                if not versions:
                    continue
                    
                latest_version = versions[-1]
                review = latest_version.get('review', {})
                
                # Check if there are approved claims
                approved_claims = [
                    claim for claim in review.get('Requirement(s)', [])
                    if claim.get('status') == 'approved'
                ]
                
                if approved_claims:
                    row = {
                        'FILENAME': review.get('FILENAME', filename),
                        'TITLE': review.get('TITLE', ''),
                        'PUBLICATION_YEAR': review.get('PUBLICATION_YEAR', ''),
                        'Requirement(s)': json.dumps(approved_claims)
                    }
                    rows.append(row)
            
            # Create DataFrame and save to CSV
            if rows:
                df = pd.DataFrame(rows)
                df.to_csv(self.csv_database_path, index=False)
                
            return True
            
        except Exception as e:
            print(f"Error syncing to CSV: {e}")
            return False
    
    def triangulate_evidence(self) -> bool:
        """
        Perform evidence triangulation across Journal and Deep reviewers.
        
        Aggregates claims from multiple reviewers for the same sub-requirements,
        computes consensus scores, and detects conflicts.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.version_history_path, 'r') as f:
                version_history = json.load(f)
            
            for filename, versions in version_history.items():
                # Group claims by sub_requirement
                claims_by_subreq = {}
                
                for version in versions:
                    claims = version.get('review', {}).get('Requirement(s)', [])
                    for claim in claims:
                        subreq = claim.get('sub_requirement')
                        if subreq:
                            if subreq not in claims_by_subreq:
                                claims_by_subreq[subreq] = []
                            claims_by_subreq[subreq].append(claim)
                
                # Triangulate claims with multiple sources
                triangulation_data = {
                    'cross_references': [],
                    'conflicts_detected': False,
                    'conflict_resolution': {}
                }
                
                for subreq, claims in claims_by_subreq.items():
                    if len(claims) > 1:
                        # Multiple reviewers covered same sub-req
                        # Extract quality scores
                        scores = []
                        for c in claims:
                            quality = c.get('evidence_quality', {})
                            composite = quality.get('composite_score', 0)
                            if composite > 0:
                                scores.append(composite)
                        
                        if not scores:
                            continue
                        
                        # Add cross-reference
                        triangulation_data['cross_references'].append({
                            'sub_requirement': subreq,
                            'num_reviewers': len(claims),
                            'sources': [c.get('source', 'unknown') for c in claims]
                        })
                        
                        # Check for conflict (significant score difference)
                        if max(scores) - min(scores) > 1.5:
                            triangulation_data['conflicts_detected'] = True
                            triangulation_data['conflict_resolution'] = {
                                'sub_requirement': subreq,
                                'strategy': 'take_higher_score',
                                'resolved_composite_score': max(scores)
                            }
                        
                        # Compute consensus
                        triangulation_data['consensus_composite_score'] = sum(scores) / len(scores)
                        
                        # Combine provenance
                        all_pages = []
                        for c in claims:
                            provenance = c.get('provenance', {})
                            pages = provenance.get('page_numbers', [])
                            if isinstance(pages, list):
                                all_pages.extend(pages)
                            # Also check for single page_number field
                            elif c.get('page_number'):
                                all_pages.append(c.get('page_number'))
                        
                        triangulation_data['combined_provenance'] = {
                            'page_numbers': sorted(list(set(all_pages)))
                        }
                
                # Append triangulation analysis to version history
                if triangulation_data['cross_references'] or triangulation_data['conflicts_detected']:
                    versions.append({
                        'timestamp': datetime.now().isoformat(),
                        'review': {
                            'FILENAME': filename,
                            'TITLE': versions[-1].get('review', {}).get('TITLE', ''),
                            'triangulation_analysis': triangulation_data
                        }
                    })
            
            # Save updated version history
            with open(self.version_history_path, 'w') as f:
                json.dump(version_history, f, indent=2)
                
            return True
            
        except Exception as e:
            print(f"Error in triangulation: {e}")
            return False
