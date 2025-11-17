# Smart Semantic Deduplication

This module implements smart semantic deduplication using sentence-transformers to detect and merge near-duplicate papers that simple title matching misses.

## Features

- **Semantic Similarity Detection**: Uses embeddings to find papers with similar content even if titles differ
- **Configurable Threshold**: Default 90% similarity threshold (configurable)
- **Metadata Preservation**: Keeps duplicate information for transparency
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

## Performance

- **Small datasets (10 papers)**: ~5 seconds
- **Medium datasets (50 papers)**: ~30 seconds  
- **Large datasets (100 papers)**: ~90 seconds

For datasets >200 papers, use batch processing:

```python
result = deduplicator.deduplicate_papers_batch('review_log.json', batch_size=50)
```

> **Note:** Batch processing currently only detects duplicates within each batch, not across batches. For complete duplicate detection on large datasets, use the standard `deduplicate_papers()` method or ensure batch size is large enough to contain all potential duplicates.

## Requirements

- sentence-transformers >= 2.2.0
- torch (auto-installed with sentence-transformers)

Model will be automatically downloaded on first use (requires internet connection).

## Testing

```bash
# Run unit tests
python -m pytest tests/unit/test_smart_dedup.py -v

# Note: Tests will skip if model is not cached locally
```

## Notes

- Papers without titles are skipped
- Missing abstracts are handled gracefully (uses title only)
- Duplicate information is preserved in the `duplicates` field
- Similarity scores are stored for transparency
