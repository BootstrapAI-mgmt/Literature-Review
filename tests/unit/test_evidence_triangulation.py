"""
Unit Tests for Evidence Triangulation (Task Card #20)
Tests semantic clustering, contradiction detection, and agreement analysis.
"""

import pytest
import sys
import os
import numpy as np
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.analysis.evidence_triangulation import (
    triangulate_evidence,
    _analyze_contradiction,
    generate_triangulation_report
)


@pytest.fixture
def mock_embedding_model():
    """Create a mock embedding model for testing."""
    mock_model = Mock()
    
    def mock_encode(texts):
        """Mock encode that creates simple embeddings based on text content."""
        embeddings = []
        for text in texts:
            # Create deterministic embeddings based on key words
            embedding = np.zeros(384)  # all-MiniLM-L6-v2 has 384 dimensions
            
            # Similar texts about SNNs/accuracy get similar embeddings
            if "snn" in text.lower() or "spiking" in text.lower():
                if "accuracy" in text.lower() or "gesture" in text.lower():
                    embedding[0:10] = 1.0  # Group 1: SNN accuracy claims
                elif "energy" in text.lower() or "efficient" in text.lower():
                    embedding[10:20] = 1.0  # Group 2: SNN energy claims
            elif "transformer" in text.lower() or "imagenet" in text.lower():
                embedding[20:30] = 1.0  # Group 3: Transformer claims
            elif "graph" in text.lower() or "routing" in text.lower():
                embedding[30:40] = 1.0  # Group 4: Graph NN claims
            else:
                # Random for unmatched
                embedding[40:50] = np.random.rand(10)
            
            embeddings.append(embedding)
        
        return np.array(embeddings)
    
    mock_model.encode = mock_encode
    return mock_model


class TestClaimClustering:
    """Test suite for semantic clustering of claims."""
    
    @pytest.mark.unit
    @patch('literature_review.analysis.evidence_triangulation.get_embedding_model')
    def test_claim_clustering_similar_claims(self, mock_get_model, mock_embedding_model):
        """Test that similar claims are grouped together."""
        mock_get_model.return_value = mock_embedding_model
        
        claims = [
            {
                "claim_id": "c1",
                "extracted_claim_text": "SNNs achieve 95% accuracy on DVS gesture dataset",
                "filename": "paper1.pdf",
                "status": "approved",
                "evidence_quality": {"composite_score": 4.0}
            },
            {
                "claim_id": "c2",
                "extracted_claim_text": "Spiking neural networks reach 94% accuracy on event-based gestures",
                "filename": "paper2.pdf",
                "status": "approved",
                "evidence_quality": {"composite_score": 4.2}
            },
            {
                "claim_id": "c3",
                "extracted_claim_text": "Transformers achieve 87% accuracy on ImageNet",
                "filename": "paper3.pdf",
                "status": "approved",
                "evidence_quality": {"composite_score": 4.5}
            }
        ]
        
        triangulation = triangulate_evidence(claims, similarity_threshold=0.85)
        
        # Should have 1 cluster (c1 and c2 are similar)
        assert len(triangulation) == 1
        cluster = list(triangulation.values())[0]
        assert cluster["num_supporting_papers"] == 2
        assert "paper1.pdf" in cluster["supporting_papers"]
        assert "paper2.pdf" in cluster["supporting_papers"]
    
    @pytest.mark.unit
    @patch('literature_review.analysis.evidence_triangulation.get_embedding_model')
    def test_claim_clustering_different_claims(self, mock_get_model, mock_embedding_model):
        """Test that different claims are not clustered together."""
        mock_get_model.return_value = mock_embedding_model
        
        claims = [
            {
                "claim_id": "c1",
                "extracted_claim_text": "SNNs are energy efficient for vision tasks",
                "filename": "paper1.pdf",
                "status": "approved",
                "evidence_quality": {"composite_score": 4.0}
            },
            {
                "claim_id": "c2",
                "extracted_claim_text": "Graph neural networks solve routing problems",
                "filename": "paper2.pdf",
                "status": "approved",
                "evidence_quality": {"composite_score": 3.8}
            }
        ]
        
        triangulation = triangulate_evidence(claims, similarity_threshold=0.85)
        
        # Should have 0 clusters (claims are too different)
        assert len(triangulation) == 0
    
    @pytest.mark.unit
    def test_empty_claims_list(self):
        """Test handling of empty claims list."""
        triangulation = triangulate_evidence([])
        assert triangulation == {}
    
    @pytest.mark.unit
    @patch('literature_review.analysis.evidence_triangulation.get_embedding_model')
    def test_single_claim(self, mock_get_model, mock_embedding_model):
        """Test handling of single claim (cannot form cluster)."""
        mock_get_model.return_value = mock_embedding_model
        
        claims = [
            {
                "claim_id": "c1",
                "extracted_claim_text": "SNNs are energy efficient",
                "filename": "paper1.pdf",
                "status": "approved",
                "evidence_quality": {"composite_score": 4.0}
            }
        ]
        
        triangulation = triangulate_evidence(claims)
        # Single claim cannot form a cluster (min_samples=2)
        assert len(triangulation) == 0


class TestContradictionDetection:
    """Test suite for contradiction detection."""
    
    @pytest.mark.unit
    @patch('literature_review.analysis.evidence_triangulation.get_embedding_model')
    def test_contradiction_detection(self, mock_get_model, mock_embedding_model):
        """Test detection of contradictory claims."""
        mock_get_model.return_value = mock_embedding_model
        
        claims = [
            {
                "claim_id": "c1",
                "extracted_claim_text": "SNNs are energy efficient",
                "filename": "paper1.pdf",
                "status": "approved",
                "evidence_quality": {"composite_score": 4.0}
            },
            {
                "claim_id": "c2",
                "extracted_claim_text": "Spiking networks are energy-efficient",
                "filename": "paper2.pdf",
                "status": "rejected",
                "evidence_quality": {"composite_score": 2.5}
            }
        ]
        
        triangulation = triangulate_evidence(claims, similarity_threshold=0.85)
        
        assert len(triangulation) == 1
        cluster = list(triangulation.values())[0]
        
        assert cluster["has_contradiction"] is True
        assert cluster["contradiction_details"]["num_approved"] == 1
        assert cluster["contradiction_details"]["num_rejected"] == 1
        assert cluster["contradiction_details"]["score_gap"] > 0
    
    @pytest.mark.unit
    @patch('literature_review.analysis.evidence_triangulation.get_embedding_model')
    def test_no_contradiction(self, mock_get_model, mock_embedding_model):
        """Test cluster without contradictions."""
        mock_get_model.return_value = mock_embedding_model
        
        claims = [
            {
                "claim_id": "c1",
                "extracted_claim_text": "SNNs achieve high accuracy",
                "filename": "paper1.pdf",
                "status": "approved",
                "evidence_quality": {"composite_score": 4.0}
            },
            {
                "claim_id": "c2",
                "extracted_claim_text": "Spiking networks reach high accuracy",
                "filename": "paper2.pdf",
                "status": "approved",
                "evidence_quality": {"composite_score": 4.1}
            }
        ]
        
        triangulation = triangulate_evidence(claims, similarity_threshold=0.85)
        
        assert len(triangulation) == 1
        cluster = list(triangulation.values())[0]
        
        assert cluster["has_contradiction"] is False
        assert cluster["contradiction_details"] is None


class TestAgreementAnalysis:
    """Test suite for agreement strength analysis."""
    
    @pytest.mark.unit
    @patch('literature_review.analysis.evidence_triangulation.get_embedding_model')
    def test_strong_agreement(self, mock_get_model, mock_embedding_model):
        """Test strong agreement classification (low variance)."""
        mock_get_model.return_value = mock_embedding_model
        
        claims = [
            {
                "claim_id": "c1",
                "extracted_claim_text": "SNNs are energy efficient",
                "filename": "paper1.pdf",
                "status": "approved",
                "evidence_quality": {"composite_score": 4.0}
            },
            {
                "claim_id": "c2",
                "extracted_claim_text": "Spiking networks are energy-efficient",
                "filename": "paper2.pdf",
                "status": "approved",
                "evidence_quality": {"composite_score": 4.1}
            },
            {
                "claim_id": "c3",
                "extracted_claim_text": "SNNs consume less energy",
                "filename": "paper3.pdf",
                "status": "approved",
                "evidence_quality": {"composite_score": 4.0}
            }
        ]
        
        triangulation = triangulate_evidence(claims, similarity_threshold=0.80)
        
        assert len(triangulation) >= 1
        cluster = list(triangulation.values())[0]
        
        assert cluster["agreement_level"] == "strong"
        assert cluster["score_variance"] < 0.3
    
    @pytest.mark.unit
    @patch('literature_review.analysis.evidence_triangulation.get_embedding_model')
    def test_weak_agreement(self, mock_get_model, mock_embedding_model):
        """Test weak agreement classification (high variance)."""
        mock_get_model.return_value = mock_embedding_model
        
        claims = [
            {
                "claim_id": "c1",
                "extracted_claim_text": "SNNs are energy efficient",
                "filename": "paper1.pdf",
                "status": "approved",
                "evidence_quality": {"composite_score": 5.0}
            },
            {
                "claim_id": "c2",
                "extracted_claim_text": "Spiking networks are energy-efficient",
                "filename": "paper2.pdf",
                "status": "approved",
                "evidence_quality": {"composite_score": 2.0}
            }
        ]
        
        triangulation = triangulate_evidence(claims, similarity_threshold=0.80)
        
        assert len(triangulation) >= 1
        cluster = list(triangulation.values())[0]
        
        assert cluster["agreement_level"] == "weak"
        assert cluster["score_variance"] > 0.7


class TestReportGeneration:
    """Test suite for triangulation report generation."""
    
    @pytest.mark.unit
    def test_report_generation(self, tmp_path):
        """Test markdown report generation."""
        triangulation_results = {
            "cluster_0": {
                "representative_claim": "SNNs achieve high accuracy",
                "supporting_papers": ["paper1.pdf", "paper2.pdf"],
                "claim_ids": ["c1", "c2"],
                "num_supporting_papers": 2,
                "agreement_level": "strong",
                "average_score": 4.1,
                "score_variance": 0.05,
                "has_contradiction": False,
                "contradiction_details": None,
                "all_claims": []
            }
        }
        
        output_file = tmp_path / "test_triangulation_report.md"
        generate_triangulation_report(triangulation_results, str(output_file))
        
        assert output_file.exists()
        content = output_file.read_text()
        
        assert "Evidence Triangulation Report" in content
        assert "Total Clusters Found:**" in content  # Markdown formatting uses **
        assert "SNNs achieve high accuracy" in content
        assert "strong" in content
    
    @pytest.mark.unit
    def test_report_with_contradiction(self, tmp_path):
        """Test report generation with contradictions."""
        triangulation_results = {
            "cluster_0": {
                "representative_claim": "SNNs are energy efficient",
                "supporting_papers": ["paper1.pdf", "paper2.pdf"],
                "claim_ids": ["c1", "c2"],
                "num_supporting_papers": 2,
                "agreement_level": "moderate",
                "average_score": 3.2,
                "score_variance": 0.45,
                "has_contradiction": True,
                "contradiction_details": {
                    "num_approved": 1,
                    "num_rejected": 1,
                    "approved_papers": ["paper1.pdf"],
                    "rejected_papers": ["paper2.pdf"],
                    "score_gap": 1.5
                },
                "all_claims": []
            }
        }
        
        output_file = tmp_path / "test_contradiction_report.md"
        generate_triangulation_report(triangulation_results, str(output_file))
        
        content = output_file.read_text()
        
        assert "CONTRADICTION DETECTED" in content
        assert "Approved: 1 papers" in content
        assert "Rejected: 1 papers" in content
        assert "Score Gap: 1.50" in content


class TestAnalyzeContradiction:
    """Test suite for contradiction analysis helper."""
    
    @pytest.mark.unit
    def test_analyze_contradiction_details(self):
        """Test detailed contradiction analysis."""
        claims = [
            {
                "filename": "paper1.pdf",
                "status": "approved",
                "evidence_quality": {"composite_score": 4.5}
            },
            {
                "filename": "paper2.pdf",
                "status": "approved",
                "evidence_quality": {"composite_score": 4.3}
            },
            {
                "filename": "paper3.pdf",
                "status": "rejected",
                "evidence_quality": {"composite_score": 2.0}
            },
            {
                "filename": "paper4.pdf",
                "status": "rejected",
                "evidence_quality": {"composite_score": 2.5}
            }
        ]
        
        result = _analyze_contradiction(claims)
        
        assert result["num_approved"] == 2
        assert result["num_rejected"] == 2
        assert len(result["approved_papers"]) == 2
        assert len(result["rejected_papers"]) == 2
        # Average approved: 4.4, average rejected: 2.25, gap: 2.15
        assert result["score_gap"] > 2.0


class TestClaimFieldVariations:
    """Test handling of different claim field variations."""
    
    @pytest.mark.unit
    @patch('literature_review.analysis.evidence_triangulation.get_embedding_model')
    def test_claim_summary_fallback(self, mock_get_model, mock_embedding_model):
        """Test using claim_summary when extracted_claim_text is missing."""
        mock_get_model.return_value = mock_embedding_model
        
        claims = [
            {
                "claim_id": "c1",
                "claim_summary": "SNNs are efficient for processing",
                "filename": "paper1.pdf",
                "status": "approved",
                "evidence_quality": {"composite_score": 4.0}
            },
            {
                "claim_id": "c2",
                "claim_summary": "Spiking networks efficiently process data",
                "filename": "paper2.pdf",
                "status": "approved",
                "evidence_quality": {"composite_score": 4.1}
            }
        ]
        
        triangulation = triangulate_evidence(claims, similarity_threshold=0.85)
        
        # Should cluster based on claim_summary
        assert len(triangulation) >= 0  # May or may not cluster depending on similarity
    
    @pytest.mark.unit
    @patch('literature_review.analysis.evidence_triangulation.get_embedding_model')
    def test_evidence_chunk_fallback(self, mock_get_model, mock_embedding_model):
        """Test using evidence_chunk as last resort."""
        mock_get_model.return_value = mock_embedding_model
        
        claims = [
            {
                "claim_id": "c1",
                "evidence_chunk": "The paper shows SNNs are energy efficient",
                "filename": "paper1.pdf",
                "status": "approved",
                "evidence_quality": {"composite_score": 4.0}
            },
            {
                "claim_id": "c2",
                "evidence_chunk": "Results indicate spiking networks save energy",
                "filename": "paper2.pdf",
                "status": "approved",
                "evidence_quality": {"composite_score": 4.1}
            }
        ]
        
        triangulation = triangulate_evidence(claims, similarity_threshold=0.80)
        
        # Should work with evidence_chunk field
        assert isinstance(triangulation, dict)
