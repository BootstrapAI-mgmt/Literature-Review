# Smart Semantic Deduplication

This module implements smart semantic deduplication using sentence-transformers to detect and merge near-duplicate papers that simple title matching misses.

## Features

- **Semantic Similarity Detection**: Uses embeddings to find papers with similar content even if titles differ
- **Configurable Threshold**: Default 90% similarity threshold (configurable)
- **Full Metadata Preservation**: Complete metadata from duplicate papers preserved for transparency
- **Cross-Batch Duplicate Detection**: Enhanced batch processing finds duplicates across all batches
- **Batch Processing**: Efficient processing for large datasets
- **CLI Tool**: Easy-to-use command-line interface with dry-run mode

## Usage

### Basic Usage

```bash
python scripts/deduplicate_papers.py --review-log review_log.json
```

### Dry Run (Preview Duplicates)

```bash
python scripts/deduplicate_papers.py --dry-run
```

### Custom Threshold

```bash
python scripts/deduplicate_papers.py --threshold 0.85
```

### Custom Output File

```bash
python scripts/deduplicate_papers.py --output custom_output.json
```

## How It Works

1. **Embedding Generation**: Combines title and abstract into embeddings using `all-MiniLM-L6-v2` model
2. **Similarity Calculation**: Computes cosine similarity between all paper pairs
3. **Duplicate Detection**: Papers with similarity ≥ threshold are marked as duplicates
4. **Merging**: Keeps the paper with more complete metadata, preserves duplicate information

## API Usage

```python
from literature_review.utils.smart_dedup import SmartDeduplicator

deduplicator = SmartDeduplicator()
result = deduplicator.deduplicate_papers('review_log.json')

print(f"Found {result['duplicate_pairs']} duplicate pairs")
print(f"Reduced from {result['original_count']} to {result['unique_count']} papers")
```

## Advanced Features

### Cross-Batch Duplicate Detection

The enhanced batch processing mode now detects duplicates across all batches, not just within each batch:

```python
# Finds ALL duplicates, even across batches
result = deduplicator.deduplicate_papers_batch('review_log.json', batch_size=50)
```

Performance overhead: ~10-15% compared to within-batch only detection.

### Full Metadata Preservation

Duplicate papers now preserve complete metadata in the `duplicate_versions` field:

```python
# Access duplicate information
for paper_file, review in result['merged_reviews'].items():
    if 'duplicate_versions' in review:
        for dup in review['duplicate_versions']:
            print(f"Duplicate: {dup['filename']}")
            print(f"Title: {dup['title']}")
            print(f"Similarity: {dup['similarity_score']}")
            print(f"Authors: {dup['metadata'].get('authors', [])}")
            print(f"Merged at: {dup['merged_at']}")
```

**Backward Compatibility**: The legacy `duplicates` field (list of filenames) is still maintained for compatibility with existing code.

### Data Structure

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
        "metadata": {
          "title": "...",
          "abstract": "...",
          "authors": ["..."],
          "year": 2023
        },
        "title": "...",
        "abstract": "...",
        "merged_at": "2025-11-17T10:30:00"
      }
    ]
  }
}
```

### Pipeline Integration

#### Option 1: Using Configuration

Enable automatic deduplication in `pipeline_config.json`:

```json
{
  "deduplication": {
    "enabled": true,
    "threshold": 0.90,
    "batch_size": 50,
    "run_before_gap_analysis": true,
    "output_file": "review_log_deduped.json"
  }
}
```

#### Option 2: Manual Integration

Run deduplication as a pipeline step before gap analysis:

```bash
# Step 1: Run deduplication
python scripts/deduplicate_papers.py --review-log review_log.json --output review_log_deduped.json

# Step 2: Run gap analysis with deduplicated file
python -m literature_review.orchestrator --review-log review_log_deduped.json
```

#### Option 3: Programmatic Integration

Integrate deduplication in your Python code:

```python
from literature_review.utils.smart_dedup import SmartDeduplicator
import json

# Load configuration
with open('pipeline_config.json') as f:
    config = json.load(f)

dedup_config = config.get('deduplication', {})

if dedup_config.get('enabled', False):
    print("Running semantic deduplication...")
    
    deduplicator = SmartDeduplicator()
    deduplicator.similarity_threshold = dedup_config.get('threshold', 0.90)
    
    batch_size = dedup_config.get('batch_size', 50)
    result = deduplicator.deduplicate_papers_batch('review_log.json', batch_size=batch_size)
    
    # Save deduplicated version
    output_file = dedup_config.get('output_file', 'review_log_deduped.json')
    with open(output_file, 'w') as f:
        json.dump(result['merged_reviews'], f, indent=2)
    
    print(f"✅ Deduplication complete: {result['duplicate_pairs']} duplicates merged")
    print(f"   Reduction: {result['reduction']}%")
    
    # Continue with deduplicated data
    review_log_file = output_file
else:
    review_log_file = 'review_log.json'

# Continue with gap analysis...
```

## Performance

- **Small datasets (10 papers)**: ~5 seconds
- **Medium datasets (50 papers)**: ~30 seconds  
- **Large datasets (100 papers)**: ~90 seconds

For datasets >200 papers, use batch processing:

```python
result = deduplicator.deduplicate_papers_batch('review_log.json', batch_size=50)
```

### Performance Benchmarks

Run performance benchmarks to measure the overhead of cross-batch detection:

```bash
pytest tests/performance/test_dedup_performance.py -v -m performance
```

Expected results:
- 10 papers: <5s
- 50 papers: <30s
- 100 papers (batch): <120s
- Cross-batch detection overhead: ~10-15%

## Requirements

- sentence-transformers >= 2.2.0
- torch (auto-installed with sentence-transformers)

Model will be automatically downloaded on first use (requires internet connection).

## Testing

```bash
# Run unit tests
python -m pytest tests/unit/test_smart_dedup.py -v

# Run performance benchmarks
python -m pytest tests/performance/test_dedup_performance.py -v -m performance

# Note: Tests will skip if model is not cached locally
```

## Notes

- Papers without titles are skipped
- Missing abstracts are handled gracefully (uses title only)
- Duplicate information is preserved in both legacy and new formats
- Similarity scores are stored for transparency
- Cross-batch detection ensures all duplicates are found, regardless of batch size
