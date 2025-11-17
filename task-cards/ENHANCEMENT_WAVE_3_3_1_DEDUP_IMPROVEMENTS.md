# Task Card: Advanced Deduplication Improvements

**Task ID:** ENHANCE-W3-3.1  
**Wave:** 3 (Automation & Optimization)  
**Priority:** LOW  
**Estimated Effort:** 6-8 hours  
**Status:** Not Started  
**Dependencies:** ENHANCE-W3-3 (Smart Deduplication - PR #44)

---

## Objective

Enhance the smart semantic deduplication module with cross-batch duplicate detection, full metadata preservation, and optional pipeline integration.

## Background

PR #44 successfully implemented core semantic deduplication using sentence-transformers. During review, several enhancement opportunities were identified that are valuable but not critical for the initial release:

1. **Batch Processing Limitation:** Current implementation only detects duplicates within each batch, missing cross-batch duplicates
2. **Partial Metadata Preservation:** Only filename and similarity score are preserved from duplicate papers
3. **Pipeline Integration:** Not yet integrated with the automated pipeline orchestrator

These improvements will make the deduplication more robust and production-ready.

## Success Criteria

- [ ] Batch processing detects duplicates across all batches
- [ ] Full metadata from both versions preserved in merged papers
- [ ] Performance benchmarks show <10% overhead for cross-batch detection
- [ ] Optional integration with pipeline orchestrator
- [ ] Documentation updated with new capabilities

## Deliverables

### 1. Cross-Batch Duplicate Detection

**File:** `literature_review/utils/smart_dedup.py` (enhancement)

**Problem:**
Current batch processing only compares papers within the same batch:
```python
for i in range(0, len(papers), batch_size):
    batch = papers[i:i + batch_size]
    embeddings = self.model.encode(texts, show_progress_bar=False)
    
    # Only finds duplicates within this batch
    batch_duplicates = self._find_duplicates(batch, embeddings)
```

**Solution Option A: Progressive Comparison (Simpler)**
```python
def deduplicate_papers_batch(self, review_log_file: str, batch_size: int = 50) -> Dict:
    """Deduplicate papers in batches with cross-batch detection."""
    # ... setup code ...
    
    all_embeddings = []
    all_papers = []
    all_duplicates = []
    
    # Generate embeddings in batches (memory efficient)
    for i in range(0, len(papers), batch_size):
        batch = papers[i:i + batch_size]
        texts = [p['text'] for p in batch]
        batch_embeddings = self.model.encode(texts, show_progress_bar=False)
        
        # Compare current batch against ALL previous papers
        for j, paper in enumerate(batch):
            current_emb = batch_embeddings[j]
            
            # Check against all previous embeddings
            for k, prev_emb in enumerate(all_embeddings):
                similarity = np.dot(current_emb, prev_emb) / (
                    np.linalg.norm(current_emb) * np.linalg.norm(prev_emb)
                )
                
                if similarity >= self.similarity_threshold:
                    all_duplicates.append((
                        all_papers[k]['file'],
                        paper['file'],
                        round(float(similarity), 3)
                    ))
        
        # Also check within current batch
        batch_dupes = self._find_duplicates(batch, batch_embeddings)
        all_duplicates.extend(batch_dupes)
        
        # Accumulate for next iteration
        all_embeddings.extend(batch_embeddings)
        all_papers.extend(batch)
    
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

**Solution Option B: FAISS for Large Datasets (Advanced)**
```python
import faiss

def deduplicate_papers_batch_faiss(self, review_log_file: str, batch_size: int = 50) -> Dict:
    """Use FAISS for efficient nearest neighbor search."""
    # ... setup code ...
    
    # Generate all embeddings in batches
    all_embeddings = []
    for i in range(0, len(papers), batch_size):
        batch = papers[i:i + batch_size]
        texts = [p['text'] for p in batch]
        batch_embeddings = self.model.encode(texts, show_progress_bar=False)
        all_embeddings.extend(batch_embeddings)
    
    # Convert to numpy array
    embeddings_array = np.array(all_embeddings).astype('float32')
    
    # Normalize for cosine similarity
    faiss.normalize_L2(embeddings_array)
    
    # Build FAISS index
    dimension = embeddings_array.shape[1]
    index = faiss.IndexFlatIP(dimension)  # Inner product = cosine after normalization
    index.add(embeddings_array)
    
    # Search for similar papers
    k = 10  # Find top 10 most similar for each paper
    similarities, indices = index.search(embeddings_array, k)
    
    # Extract duplicates above threshold
    duplicates = []
    for i in range(len(papers)):
        for j in range(1, k):  # Skip first result (self)
            if similarities[i][j] >= self.similarity_threshold:
                if i < indices[i][j]:  # Avoid duplicates (A,B) and (B,A)
                    duplicates.append((
                        papers[i]['file'],
                        papers[indices[i][j]]['file'],
                        round(float(similarities[i][j]), 3)
                    ))
    
    # Merge duplicates
    merged_reviews = self._merge_duplicates(reviews, duplicates)
    
    return { ... }
```

**Recommendation:** Start with Option A (progressive comparison) for simplicity. Add Option B if performance becomes an issue with >1000 papers.

---

### 2. Full Metadata Preservation

**File:** `literature_review/utils/smart_dedup.py` (enhancement)

**Current State:**
```python
# Only preserves filename and similarity
merged[keep]['duplicates'] = merged[keep].get('duplicates', []) + [remove]
merged[keep]['similarity_score'] = similarity
```

**Enhanced Implementation:**
```python
def _merge_duplicates(self, reviews: Dict, duplicates: List[Tuple]) -> Dict:
    """Merge duplicate entries with full metadata preservation."""
    merged = dict(reviews)
    
    for file1, file2, similarity in duplicates:
        if file1 not in merged or file2 not in merged:
            continue
        
        # Keep the one with more complete data
        review1 = merged[file1]
        review2 = merged[file2]
        
        score1 = len(review1.get('metadata', {}).get('abstract', '')) + \
                len(str(review1.get('judge_analysis', {})))
        score2 = len(review2.get('metadata', {}).get('abstract', '')) + \
                len(str(review2.get('judge_analysis', {})))
        
        if score1 >= score2:
            keep, remove = file1, file2
            kept_review, removed_review = review1, review2
        else:
            keep, remove = file2, file1
            kept_review, removed_review = review2, review1
        
        # NEW: Preserve full metadata from duplicate
        duplicate_info = {
            'filename': remove,
            'similarity_score': similarity,
            'metadata': removed_review.get('metadata', {}),
            'title': removed_review.get('metadata', {}).get('title', ''),
            'abstract': removed_review.get('metadata', {}).get('abstract', ''),
            'merged_at': datetime.now().isoformat()
        }
        
        # Append to duplicates list (handle multiple duplicates)
        if 'duplicate_versions' not in merged[keep]:
            merged[keep]['duplicate_versions'] = []
        merged[keep]['duplicate_versions'].append(duplicate_info)
        
        # Also keep simple list for backward compatibility
        merged[keep]['duplicates'] = merged[keep].get('duplicates', []) + [remove]
        
        # Remove duplicate
        del merged[remove]
        
        logger.info(f"Merged duplicate: {remove} -> {keep} ({similarity:.2%} similar)")
    
    return merged
```

**Benefits:**
- Can recover metadata if needed
- Transparency for auditing
- Enables analysis of duplicate patterns
- Preserves publication history (preprint → published)

---

### 3. Performance Benchmarking

**File:** `tests/performance/test_dedup_performance.py` (new)

```python
"""Performance benchmarks for smart deduplication."""

import pytest
import time
import json
from literature_review.utils.smart_dedup import SmartDeduplicator


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
    test_sizes = [10, 50, 100, 200]
    
    for size in test_sizes:
        reviews = generate_test_data(size)
        
        # Write to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(reviews, f)
            temp_file = f.name
        
        # Benchmark
        deduplicator = SmartDeduplicator()
        start = time.time()
        result = deduplicator.deduplicate_papers(temp_file)
        elapsed = time.time() - start
        
        print(f"\n{size} papers: {elapsed:.2f}s ({result['duplicate_pairs']} duplicates found)")
        
        # Cleanup
        import os
        os.unlink(temp_file)


@pytest.mark.performance
def test_batch_mode_performance():
    """Benchmark batch mode with cross-batch detection."""
    reviews = generate_test_data(200)
    
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(reviews, f)
        temp_file = f.name
    
    deduplicator = SmartDeduplicator()
    
    # Test different batch sizes
    for batch_size in [25, 50, 100]:
        start = time.time()
        result = deduplicator.deduplicate_papers_batch(temp_file, batch_size=batch_size)
        elapsed = time.time() - start
        
        print(f"\nBatch size {batch_size}: {elapsed:.2f}s ({result['duplicate_pairs']} duplicates)")
    
    import os
    os.unlink(temp_file)
```

**Run benchmarks:**
```bash
pytest tests/performance/test_dedup_performance.py -v -m performance
```

---

### 4. Optional Pipeline Integration

**File:** `literature_review/orchestrator.py` (integration)

```python
class LiteratureReviewOrchestrator:
    def __init__(self, ...):
        # ... existing code ...
        self.enable_deduplication = config.get('enable_deduplication', True)
        self.dedup_threshold = config.get('dedup_threshold', 0.90)
    
    def run_review_pipeline(self):
        """Run complete review pipeline with optional deduplication."""
        # ... existing steps ...
        
        # NEW: Deduplication step (before gap analysis)
        if self.enable_deduplication:
            logger.info("Running semantic deduplication...")
            from literature_review.utils.smart_dedup import SmartDeduplicator
            
            deduplicator = SmartDeduplicator()
            deduplicator.similarity_threshold = self.dedup_threshold
            
            result = deduplicator.deduplicate_papers('review_log.json')
            
            # Save deduplicated version
            with open('review_log_deduped.json', 'w') as f:
                json.dump(result['merged_reviews'], f, indent=2)
            
            logger.info(f"Deduplication complete: {result['duplicate_pairs']} duplicates merged")
            logger.info(f"Reduction: {result['reduction']}%")
            
            # Use deduplicated version for gap analysis
            self.review_log_file = 'review_log_deduped.json'
        
        # Continue with gap analysis using deduplicated reviews
        # ... rest of pipeline ...
```

**Configuration:**
```json
{
  "enable_deduplication": true,
  "dedup_threshold": 0.90,
  "dedup_batch_size": 50
}
```

---

### 5. Documentation Updates

**File:** `docs/smart_deduplication.md` (enhancements)

Add sections:

```markdown
## Advanced Features

### Cross-Batch Duplicate Detection

The enhanced batch processing mode now detects duplicates across all batches:

```python
# Finds ALL duplicates, even across batches
result = deduplicator.deduplicate_papers_batch('review_log.json', batch_size=50)
```

Performance overhead: ~10-15% compared to within-batch only detection.

### Full Metadata Preservation

Duplicate papers now preserve complete metadata:

```python
# Access duplicate information
for paper_file, review in result['merged_reviews'].items():
    if 'duplicate_versions' in review:
        for dup in review['duplicate_versions']:
            print(f"Duplicate: {dup['filename']}")
            print(f"Title: {dup['title']}")
            print(f"Similarity: {dup['similarity_score']}")
```

### Pipeline Integration

Enable automatic deduplication in the pipeline:

```python
orchestrator = LiteratureReviewOrchestrator(
    config={'enable_deduplication': True, 'dedup_threshold': 0.90}
)
orchestrator.run_review_pipeline()
```
```

---

## Testing Plan

### Unit Tests

**File:** `tests/unit/test_smart_dedup.py` (additions)

```python
def test_cross_batch_detection(tmp_path):
    """Test that batch mode finds cross-batch duplicates."""
    reviews = {
        f"paper_{i}.json": {
            "metadata": {
                "title": f"Paper on Topic {i % 3}",
                "abstract": f"This discusses topic {i % 3}"
            }
        }
        for i in range(10)
    }
    
    review_file = tmp_path / "review.json"
    with open(review_file, 'w') as f:
        json.dump(reviews, f)
    
    deduplicator = SmartDeduplicator()
    deduplicator.similarity_threshold = 0.85
    
    # Use small batch size to force cross-batch scenarios
    result = deduplicator.deduplicate_papers_batch(str(review_file), batch_size=3)
    
    # Should find duplicates across batches
    assert result['duplicate_pairs'] > 0


def test_full_metadata_preservation(tmp_path, sample_reviews_with_duplicates):
    """Test that full metadata is preserved from duplicates."""
    review_file = tmp_path / "review.json"
    with open(review_file, 'w') as f:
        json.dump(sample_reviews_with_duplicates, f)
    
    deduplicator = SmartDeduplicator()
    result = deduplicator.deduplicate_papers(str(review_file))
    
    # Check for duplicate_versions field
    for paper_file, review in result['merged_reviews'].items():
        if 'duplicate_versions' in review:
            for dup in review['duplicate_versions']:
                assert 'filename' in dup
                assert 'similarity_score' in dup
                assert 'metadata' in dup
                assert 'title' in dup
                assert 'merged_at' in dup
```

### Performance Tests

```bash
# Run performance benchmarks
pytest tests/performance/test_dedup_performance.py -v -m performance

# Expected results:
# 10 papers: <5s
# 50 papers: <30s
# 100 papers: <90s
# 200 papers (batch): <120s
```

---

## Acceptance Criteria

- [ ] Batch mode detects cross-batch duplicates (verified by tests)
- [ ] Performance overhead <15% for cross-batch detection
- [ ] Full metadata preserved in `duplicate_versions` field
- [ ] Backward compatibility maintained (`duplicates` field still exists)
- [ ] Pipeline integration works with config flag
- [ ] All existing tests still pass
- [ ] New tests cover cross-batch scenarios
- [ ] Documentation updated with new features
- [ ] Performance benchmarks documented

---

## Migration Notes

### Backward Compatibility

The enhancements maintain backward compatibility:

**Old format (still supported):**
```json
{
  "paper1.json": {
    "duplicates": ["paper2.json"],
    "similarity_score": 0.95
  }
}
```

**New format (enhanced):**
```json
{
  "paper1.json": {
    "duplicates": ["paper2.json"],
    "duplicate_versions": [
      {
        "filename": "paper2.json",
        "similarity_score": 0.95,
        "metadata": {...},
        "title": "...",
        "abstract": "...",
        "merged_at": "2025-11-17T10:30:00"
      }
    ]
  }
}
```

Code using old format will continue to work.

---

## Dependencies

**Python Packages:**
- `sentence-transformers>=2.2.0` (already required)
- `faiss-cpu>=1.7.0` (optional, for FAISS implementation)
- `numpy>=1.20.0` (already required)

**Installation (if using FAISS):**
```bash
pip install faiss-cpu  # CPU version
# or
pip install faiss-gpu  # GPU version (faster)
```

---

## Notes

- This is an enhancement, not a bug fix
- All changes are additive (backward compatible)
- Can be implemented incrementally (cross-batch first, then metadata, then integration)
- FAISS implementation is optional (only needed for >1000 papers)
- Performance benchmarks should be run on realistic data

---

**Created:** 2025-11-17  
**Assigned To:** TBD  
**Target Completion:** Wave 3+ (Optional Enhancement)  
**Blocked By:** PR #44 must be merged first
