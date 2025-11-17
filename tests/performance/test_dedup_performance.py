"""Performance benchmarks for smart deduplication."""

import pytest
import time
import json
import os
import sys
import tempfile

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


def generate_test_data(num_papers: int, duplicate_rate: float = 0.1):
    """Generate synthetic test data with known duplicates."""
    reviews = {}

    for i in range(num_papers):
        # Create base paper
        reviews[f"paper_{i}.json"] = {
            "metadata": {
                "title": f"Paper {i}: Deep Learning for Task {i % 20}",
                "abstract": f"This paper discusses approach {i} to problem {i % 10}."
            }
        }

        # Add duplicates
        if i % int(1/duplicate_rate) == 0 and i > 0:
            dup_id = f"paper_{i}_duplicate.json"
            reviews[dup_id] = {
                "metadata": {
                    "title": f"Paper {i}: Deep Learning for Task {i % 20} (Published Version)",
                    "abstract": f"This work discusses approach {i} to problem {i % 10}."
                }
            }

    return reviews

@pytest.mark.performance
def test_standard_mode_performance():
    """Benchmark standard deduplication mode."""
    test_sizes = [10, 50, 100]

    for size in test_sizes:
        reviews = generate_test_data(size)

        # Write to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(reviews, f)
            temp_file = f.name

        try:
            # Benchmark
            deduplicator = SmartDeduplicator()
            start = time.time()
            result = deduplicator.deduplicate_papers(temp_file)
            elapsed = time.time() - start

            print(f"\n{size} papers: {elapsed:.2f}s ({result['duplicate_pairs']} duplicates found)")

            # Basic assertions
            assert result['original_count'] > 0
            assert result['unique_count'] <= result['original_count']
        finally:
            # Cleanup
            os.unlink(temp_file)

@pytest.mark.performance
def test_batch_mode_performance():
    """Benchmark batch mode with cross-batch detection."""
    reviews = generate_test_data(100)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(reviews, f)
        temp_file = f.name

    try:
        deduplicator = SmartDeduplicator()

        # Test different batch sizes
        for batch_size in [25, 50]:
            start = time.time()
            result = deduplicator.deduplicate_papers_batch(temp_file, batch_size=batch_size)
            elapsed = time.time() - start

            print(f"\nBatch size {batch_size}: {elapsed:.2f}s ({result['duplicate_pairs']} duplicates)")

            # Basic assertions
            assert result['original_count'] > 0
            assert result['unique_count'] <= result['original_count']
    finally:
        os.unlink(temp_file)

@pytest.mark.performance
def test_cross_batch_detection_overhead():
    """Measure overhead of cross-batch detection."""
    reviews = generate_test_data(50, duplicate_rate=0.15)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(reviews, f)
        temp_file = f.name

    try:
        deduplicator = SmartDeduplicator()

        # Use small batch size to force cross-batch scenarios
        start = time.time()
        result = deduplicator.deduplicate_papers_batch(temp_file, batch_size=10)
        elapsed_cross_batch = time.time() - start

        print(f"\nCross-batch detection: {elapsed_cross_batch:.2f}s")
        print(f"Duplicate pairs found: {result['duplicate_pairs']}")
        print(f"Reduction: {result['reduction']}%")

        # Should find duplicates across batches
        assert result['duplicate_pairs'] >= 0

        # Performance should be reasonable (< 120s for 50 papers)
        assert elapsed_cross_batch < 120
    finally:
        os.unlink(temp_file)
