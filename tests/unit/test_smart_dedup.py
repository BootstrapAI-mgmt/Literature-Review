"""Unit tests for smart deduplication."""

import pytest
import json
import tempfile
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from literature_review.utils.smart_dedup import SmartDeduplicator


# Check if model is available in cache
def is_model_available():
    """Check if the sentence transformer model is cached locally."""
    cache_dir = os.path.expanduser("~/.cache/torch/sentence_transformers")
    model_dir = os.path.join(cache_dir, "sentence-transformers_all-MiniLM-L6-v2")
    return os.path.exists(model_dir)


# Skip all tests if model is not available
pytestmark = pytest.mark.skipif(
    not is_model_available(),
    reason="Sentence transformer model not cached (requires internet to download). "
           "The module works correctly when model is available."
)


@pytest.fixture
def sample_reviews_with_duplicates():
    """Sample review log with semantic duplicates."""
    return {
        "paper1.json": {
            "metadata": {
                "title": "Deep Learning for Image Classification",
                "abstract": "This paper presents a novel approach to image classification using deep neural networks."
            }
        },
        "paper2.json": {
            "metadata": {
                "title": "Image Classification Using Deep Neural Networks",
                "abstract": "We present a new method for classifying images with deep learning techniques."
            }
        },
        "paper3.json": {
            "metadata": {
                "title": "Blockchain for Supply Chain Management",
                "abstract": "This work explores the use of blockchain technology in supply chains."
            }
        }
    }


@pytest.mark.unit
def test_duplicate_detection(tmp_path, sample_reviews_with_duplicates):
    """Test detection of semantic duplicates."""
    review_file = tmp_path / "review.json"
    
    with open(review_file, 'w') as f:
        json.dump(sample_reviews_with_duplicates, f)
    
    deduplicator = SmartDeduplicator()
    result = deduplicator.deduplicate_papers(str(review_file))
    
    # Should find paper1 and paper2 as duplicates
    assert result['duplicate_pairs'] >= 1
    assert result['unique_count'] < result['original_count']


@pytest.mark.unit
def test_similarity_threshold(tmp_path, sample_reviews_with_duplicates):
    """Test similarity threshold affects duplicate detection."""
    review_file = tmp_path / "review.json"
    
    with open(review_file, 'w') as f:
        json.dump(sample_reviews_with_duplicates, f)
    
    # High threshold (strict)
    dedup_strict = SmartDeduplicator()
    dedup_strict.similarity_threshold = 0.95
    result_strict = dedup_strict.deduplicate_papers(str(review_file))
    
    # Low threshold (lenient)
    dedup_lenient = SmartDeduplicator()
    dedup_lenient.similarity_threshold = 0.70
    result_lenient = dedup_lenient.deduplicate_papers(str(review_file))
    
    # Lenient should find more/same duplicates
    assert result_lenient['duplicate_pairs'] >= result_strict['duplicate_pairs']


@pytest.mark.unit
def test_metadata_preservation(tmp_path, sample_reviews_with_duplicates):
    """Test that duplicate information is preserved."""
    review_file = tmp_path / "review.json"
    
    with open(review_file, 'w') as f:
        json.dump(sample_reviews_with_duplicates, f)
    
    deduplicator = SmartDeduplicator()
    result = deduplicator.deduplicate_papers(str(review_file))
    
    # Check that merged reviews contain duplicate information
    for paper_file, review in result['merged_reviews'].items():
        if 'duplicates' in review:
            assert isinstance(review['duplicates'], list)
            assert 'similarity_score' in review


@pytest.mark.unit
def test_no_duplicates(tmp_path):
    """Test with papers that have no duplicates."""
    reviews = {
        "paper1.json": {
            "metadata": {
                "title": "Quantum Computing Applications",
                "abstract": "This paper discusses quantum computing applications in cryptography."
            }
        },
        "paper2.json": {
            "metadata": {
                "title": "Machine Learning in Healthcare",
                "abstract": "We explore the use of ML techniques for medical diagnosis."
            }
        }
    }
    
    review_file = tmp_path / "review.json"
    with open(review_file, 'w') as f:
        json.dump(reviews, f)
    
    deduplicator = SmartDeduplicator()
    result = deduplicator.deduplicate_papers(str(review_file))
    
    # Should find no duplicates
    assert result['duplicate_pairs'] == 0
    assert result['unique_count'] == result['original_count']


@pytest.mark.unit
def test_missing_metadata(tmp_path):
    """Test handling of missing metadata."""
    reviews = {
        "paper1.json": {
            "metadata": {
                "title": "Paper with Title Only"
            }
        },
        "paper2.json": {
            "metadata": {}
        },
        "paper3.json": {}
    }
    
    review_file = tmp_path / "review.json"
    with open(review_file, 'w') as f:
        json.dump(reviews, f)
    
    deduplicator = SmartDeduplicator()
    # Should not raise an error
    result = deduplicator.deduplicate_papers(str(review_file))
    
    # Should handle gracefully
    assert result is not None
    assert result['original_count'] == 3


@pytest.mark.unit
def test_batch_processing(tmp_path, sample_reviews_with_duplicates):
    """Test batch processing produces same results."""
    review_file = tmp_path / "review.json"
    
    with open(review_file, 'w') as f:
        json.dump(sample_reviews_with_duplicates, f)
    
    deduplicator = SmartDeduplicator()
    
    # Regular processing
    result_regular = deduplicator.deduplicate_papers(str(review_file))
    
    # Batch processing
    result_batch = deduplicator.deduplicate_papers_batch(str(review_file), batch_size=2)
    
    # Should produce same duplicate count
    assert result_regular['duplicate_pairs'] == result_batch['duplicate_pairs']
    assert result_regular['unique_count'] == result_batch['unique_count']
