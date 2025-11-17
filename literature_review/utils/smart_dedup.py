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
