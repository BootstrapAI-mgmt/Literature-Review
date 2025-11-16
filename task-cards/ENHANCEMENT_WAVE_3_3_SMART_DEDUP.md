# Task Card: Smart Semantic Deduplication

**Task ID:** ENHANCE-W3-3  
**Wave:** 3 (Automation & Optimization)  
**Priority:** LOW  
**Estimated Effort:** 8 hours  
**Status:** Not Started  
**Dependencies:** None

---

## Objective

Use embeddings to detect and merge near-duplicate papers that simple title matching misses.

## Background

Strategic addition from synthesis: Current deduplication only catches exact title matches. Need semantic matching to catch papers with different titles but same content (e.g., preprint vs. published version).

## Success Criteria

- [ ] Detect semantic duplicates using sentence-transformers
- [ ] Calculate similarity scores (>90% = duplicate)
- [ ] Merge duplicate entries, keep best version
- [ ] 10-20% reduction in false unique papers
- [ ] Preserve metadata from both versions

## Deliverables

### 1. Core Deduplication Module

**File:** `literature_review/utils/smart_dedup.py`

```python
"""Smart Semantic Deduplication using embeddings."""

import json
import os
from typing import Dict, List, Tuple
from sentence_transformers import SentenceTransformer
import numpy as np
import logging

logger = logging.getLogger(__name__)


class SmartDeduplicator:
    """Detect and merge semantic duplicates."""
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)
        self.similarity_threshold = 0.90  # 90% similarity = duplicate
    
    def deduplicate_papers(self, review_log_file: str) -> Dict:
        """Find and merge duplicate papers."""
        logger.info("Running smart semantic deduplication...")
        
        with open(review_log_file, 'r') as f:
            reviews = json.load(f)
        
        # Extract paper metadata
        papers = []
        for paper_file, review in reviews.items():
            metadata = review.get('metadata', {})
            title = metadata.get('title', '')
            abstract = metadata.get('abstract', '')
            
            if not title:
                continue
            
            papers.append({
                'file': paper_file,
                'title': title,
                'abstract': abstract,
                'text': f"{title}. {abstract}"  # Combined for embedding
            })
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(papers)} papers...")
        texts = [p['text'] for p in papers]
        embeddings = self.model.encode(texts, show_progress_bar=True)
        
        # Find duplicates
        duplicates = self._find_duplicates(papers, embeddings)
        
        # Merge duplicates
        merged_reviews = self._merge_duplicates(reviews, duplicates)
        
        return {
            'original_count': len(reviews),
            'duplicate_pairs': len(duplicates),
            'unique_count': len(merged_reviews),
            'reduction': round((1 - len(merged_reviews) / len(reviews)) * 100, 1),
            'duplicates_found': duplicates,
            'merged_reviews': merged_reviews
        }
    
    def _find_duplicates(self, papers: List[Dict], embeddings: np.ndarray) -> List[Tuple[str, str, float]]:
        """Find duplicate pairs using cosine similarity."""
        duplicates = []
        n = len(papers)
        
        # Compute pairwise similarities
        for i in range(n):
            for j in range(i + 1, n):
                similarity = np.dot(embeddings[i], embeddings[j]) / (
                    np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[j])
                )
                
                if similarity >= self.similarity_threshold:
                    duplicates.append((
                        papers[i]['file'],
                        papers[j]['file'],
                        round(float(similarity), 3)
                    ))
        
        return duplicates
    
    def _merge_duplicates(self, reviews: Dict, duplicates: List[Tuple]) -> Dict:
        """Merge duplicate entries, keeping best version."""
        merged = dict(reviews)
        
        for file1, file2, similarity in duplicates:
            if file1 not in merged or file2 not in merged:
                continue  # Already merged
            
            # Keep the one with more complete data
            review1 = merged[file1]
            review2 = merged[file2]
            
            # Heuristic: keep the one with longer abstract or more judge data
            score1 = len(review1.get('metadata', {}).get('abstract', '')) + \
                    len(str(review1.get('judge_analysis', {})))
            score2 = len(review2.get('metadata', {}).get('abstract', '')) + \
                    len(str(review2.get('judge_analysis', {})))
            
            if score1 >= score2:
                keep, remove = file1, file2
            else:
                keep, remove = file2, file1
            
            # Merge metadata
            merged[keep]['duplicates'] = merged[keep].get('duplicates', []) + [remove]
            merged[keep]['similarity_score'] = similarity
            
            # Remove duplicate
            del merged[remove]
            
            logger.info(f"Merged duplicate: {remove} -> {keep} ({similarity:.2%} similar)")
        
        return merged


def run_smart_dedup(review_log: str, output_file: str = 'review_log_deduped.json'):
    """Run smart deduplication and save results."""
    deduplicator = SmartDeduplicator()
    result = deduplicator.deduplicate_papers(review_log)
    
    # Save deduplicated reviews
    with open(output_file, 'w') as f:
        json.dump(result['merged_reviews'], f, indent=2)
    
    print("\n" + "="*60)
    print("SMART SEMANTIC DEDUPLICATION")
    print("="*60)
    print(f"\nOriginal Papers: {result['original_count']}")
    print(f"Duplicates Found: {result['duplicate_pairs']}")
    print(f"Unique Papers: {result['unique_count']}")
    print(f"Reduction: {result['reduction']}%")
    
    if result['duplicates_found']:
        print(f"\nTop Duplicates:")
        for file1, file2, sim in result['duplicates_found'][:5]:
            print(f"  {file1} ≈ {file2} ({sim:.0%} similar)")
    
    print("\n" + "="*60)
    print(f"Deduplicated reviews saved to: {output_file}")
    print("="*60 + "\n")
    
    return result
```

### 2. Batch Processing for Large Datasets

**File:** `literature_review/utils/smart_dedup.py` (enhancement)

```python
class SmartDeduplicator:
    # ... existing code ...
    
    def deduplicate_papers_batch(self, review_log_file: str, batch_size: int = 50) -> Dict:
        """
        Deduplicate papers in batches for large datasets.
        
        Args:
            review_log_file: Path to review log
            batch_size: Number of papers per batch
        
        Returns:
            Deduplication report
        """
        logger.info("Running smart deduplication in batch mode...")
        
        with open(review_log_file, 'r') as f:
            reviews = json.load(f)
        
        # Extract papers
        papers = []
        for paper_file, review in reviews.items():
            metadata = review.get('metadata', {})
            title = metadata.get('title', '')
            abstract = metadata.get('abstract', '')
            
            if not title:
                continue
            
            papers.append({
                'file': paper_file,
                'title': title,
                'abstract': abstract,
                'text': f"{title}. {abstract}"
            })
        
        # Process in batches
        all_duplicates = []
        
        for i in range(0, len(papers), batch_size):
            batch = papers[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(papers)-1)//batch_size + 1}")
            
            texts = [p['text'] for p in batch]
            embeddings = self.model.encode(texts, show_progress_bar=False)
            
            # Find duplicates within batch
            batch_duplicates = self._find_duplicates(batch, embeddings)
            all_duplicates.extend(batch_duplicates)
        
        # Merge duplicates
        merged_reviews = self._merge_duplicates(reviews, all_duplicates)
        
        return {
            'original_count': len(reviews),
            'duplicate_pairs': len(all_duplicates),
            'unique_count': len(merged_reviews),
            'reduction': round((1 - len(merged_reviews) / len(reviews)) * 100, 1),
            'duplicates_found': all_duplicates,
            'merged_reviews': merged_reviews
        }
```

### 3. CLI Tool

**File:** `scripts/deduplicate_papers.py`

```python
#!/usr/bin/env python3
"""Smart semantic deduplication of papers."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from literature_review.utils.smart_dedup import run_smart_dedup
import argparse


def main():
    parser = argparse.ArgumentParser(
        description='Deduplicate papers using semantic similarity'
    )
    parser.add_argument(
        '--review-log',
        default='review_log.json',
        help='Path to review log'
    )
    parser.add_argument(
        '--output',
        default='review_log_deduped.json',
        help='Output file for deduplicated reviews'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.90,
        help='Similarity threshold (0-1, default: 0.90)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show duplicates without merging'
    )
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("Running in dry-run mode (no files will be modified)")
    
    # Run deduplication
    result = run_smart_dedup(
        review_log=args.review_log,
        output_file=args.output if not args.dry_run else None
    )
    
    # Show duplicates
    if result['duplicates_found']:
        print("\nDuplicates Found:")
        for file1, file2, sim in result['duplicates_found']:
            print(f"  {file1}")
            print(f"  ≈ {file2}")
            print(f"  Similarity: {sim:.0%}\n")
    
    if not args.dry_run:
        print(f"\n✅ Deduplicated reviews saved to: {args.output}")
        print("\n⚠️ Remember to use the deduplicated file for gap analysis!")


if __name__ == '__main__':
    main()
```

## Testing Plan

### Unit Tests

**File:** `tests/unit/test_smart_dedup.py`

```python
"""Unit tests for smart deduplication."""

import pytest
import json
import tempfile
from literature_review.utils.smart_dedup import SmartDeduplicator


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
```

### Integration Tests

```bash
# Test deduplication
python scripts/deduplicate_papers.py --review-log review_log.json

# Dry run to preview duplicates
python scripts/deduplicate_papers.py --dry-run

# Custom threshold
python scripts/deduplicate_papers.py --threshold 0.85

# Verify output
cat review_log_deduped.json | jq '. | length'
cat review_log_deduped.json | jq '.[].duplicates'
```

### Performance Testing

```python
# Test with various dataset sizes
import time
from literature_review.utils.smart_dedup import SmartDeduplicator

deduplicator = SmartDeduplicator()

# Time small dataset (10 papers)
start = time.time()
deduplicator.deduplicate_papers('test_10_papers.json')
print(f"10 papers: {time.time() - start:.2f}s")

# Time medium dataset (50 papers)
start = time.time()
deduplicator.deduplicate_papers('test_50_papers.json')
print(f"50 papers: {time.time() - start:.2f}s")

# Time large dataset (100 papers)
start = time.time()
deduplicator.deduplicate_papers('test_100_papers.json')
print(f"100 papers: {time.time() - start:.2f}s")
```

## Acceptance Criteria

- [ ] Detects semantic duplicates with >90% similarity
- [ ] Merges duplicates keeping most complete version
- [ ] Preserves all metadata (duplicate list, similarity scores)
- [ ] Achieves 10-20% reduction in false unique papers
- [ ] Runs in <2 minutes for 100 papers
- [ ] Integrated with pipeline orchestrator
- [ ] CLI tool supports dry-run mode
- [ ] Configurable similarity threshold
- [ ] Handles missing abstracts gracefully

## Performance Optimization

### Expected Runtime

- **10 papers:** ~5 seconds
- **50 papers:** ~30 seconds
- **100 papers:** ~90 seconds
- **Complexity:** O(n²) for pairwise similarity

### Optimization Tips

1. **Batch Processing:** Use `deduplicate_papers_batch()` for >200 papers
2. **GPU Acceleration:** Install `torch` with CUDA for faster embedding generation
3. **Model Selection:** Use smaller models for speed (MiniLM-L6 vs L12)
4. **Caching:** Cache embeddings if re-running multiple times

## Dependencies

**Add to `requirements.txt`:**

```txt
sentence-transformers>=2.2.0
torch>=2.0.0
```

**Installation:**

```bash
pip install sentence-transformers torch
```

## Notes

- **Model:** Uses `all-MiniLM-L6-v2` (lightweight, fast, 384-dimensional embeddings)
- **Similarity:** Cosine similarity between title+abstract embeddings
- **Threshold:** Default 90% (configurable via CLI or code)
- **Metadata:** Preserves duplicate list for transparency
- **Best Version:** Keeps paper with longer abstract or more complete judge analysis
- **GPU Support:** Automatically uses GPU if available (via PyTorch)

---

**Created:** 2025-11-16  
**Assigned To:** TBD  
**Target Completion:** Wave 3 (Week 5-6)
