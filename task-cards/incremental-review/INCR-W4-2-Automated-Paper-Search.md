# INCR-W4-2: Automated Paper Search Integration

**Wave:** 4 (Advanced Features - Optional)  
**Priority:** 🟢 Low (Optional)  
**Effort:** 5-6 hours  
**Status:** 🟡 Blocked (requires Waves 1-3 validated)  
**Assignable:** Backend Developer

---

## Overview

Integrate with academic search APIs (Google Scholar, arXiv, PubMed) to automatically suggest papers that could close identified gaps. Generate search queries from gap keywords and recommend papers for incremental analysis.

---

## Dependencies

**Prerequisites:**
- ✅ Waves 1-3 complete and validated in production
- ✅ INCR-W1-1 (Gap Extraction Engine)

---

## Scope

### Included
- [x] Google Scholar API integration
- [x] arXiv API integration
- [x] PubMed API integration
- [x] Search query generation from gaps
- [x] Rate limiting and caching
- [x] UI: "Suggested Papers" panel
- [x] Download/import suggested papers

### Excluded
- ❌ Paid API tiers (use free tiers only)
- ❌ Full-text PDF download (metadata only)
- ❌ Citation network analysis

---

## Technical Specification

### Search Query Generation

```python
"""Generate search queries from gaps."""

from typing import List, Dict

class SearchQueryGenerator:
    """Generate academic search queries from gap analysis."""
    
    def generate_query(self, gap: Dict) -> str:
        """
        Generate search query from gap keywords.
        
        Args:
            gap: Gap object with keywords, pillar, requirement
        
        Returns:
            Search query string
        """
        keywords = gap['keywords']
        pillar_name = gap.get('pillar_name', '')
        
        # Build query
        # Use top 3 keywords, combine with AND
        primary_keywords = keywords[:3]
        query = ' AND '.join(f'"{kw}"' for kw in primary_keywords)
        
        # Add pillar context if relevant
        if pillar_name:
            query += f' AND {pillar_name}'
        
        # Add year filter (recent papers only)
        query += ' AND year:2023-2025'
        
        return query
    
    def generate_queries_for_gaps(self, gaps: List[Dict]) -> List[Tuple[Dict, str]]:
        """
        Generate queries for all gaps.
        
        Returns:
            List of (gap, query) tuples
        """
        return [(gap, self.generate_query(gap)) for gap in gaps]
```

### API Integrations

#### 1. arXiv API (Free, No Auth)

```python
"""arXiv API integration."""

import urllib.request
import urllib.parse
import feedparser
from typing import List, Dict

class ArXivSearcher:
    """Search arXiv for papers."""
    
    BASE_URL = 'http://export.arxiv.org/api/query'
    
    def search(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Search arXiv.
        
        Args:
            query: Search query string
            max_results: Max results to return
        
        Returns:
            List of paper metadata dicts
        """
        params = {
            'search_query': query,
            'start': 0,
            'max_results': max_results,
            'sortBy': 'relevance',
            'sortOrder': 'descending'
        }
        
        url = f"{self.BASE_URL}?{urllib.parse.urlencode(params)}"
        
        response = urllib.request.urlopen(url).read()
        feed = feedparser.parse(response)
        
        papers = []
        for entry in feed.entries:
            papers.append({
                'title': entry.title,
                'authors': [author.name for author in entry.authors],
                'abstract': entry.summary,
                'published': entry.published,
                'arxiv_id': entry.id.split('/abs/')[-1],
                'url': entry.id,
                'source': 'arXiv'
            })
        
        return papers
```

#### 2. PubMed API (Free, No Auth)

```python
"""PubMed API integration."""

from Bio import Entrez
from typing import List, Dict

class PubMedSearcher:
    """Search PubMed for papers."""
    
    def __init__(self, email: str = 'your_email@example.com'):
        Entrez.email = email
    
    def search(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Search PubMed.
        
        Args:
            query: Search query string
            max_results: Max results to return
        
        Returns:
            List of paper metadata dicts
        """
        # Search for IDs
        handle = Entrez.esearch(db='pubmed', term=query, retmax=max_results)
        record = Entrez.read(handle)
        handle.close()
        
        ids = record['IdList']
        
        if not ids:
            return []
        
        # Fetch metadata
        handle = Entrez.efetch(db='pubmed', id=','.join(ids), rettype='medline', retmode='text')
        records = handle.read()
        handle.close()
        
        # Parse records
        papers = self._parse_medline(records)
        
        return papers
    
    def _parse_medline(self, medline_text: str) -> List[Dict]:
        """Parse MEDLINE format."""
        papers = []
        current_paper = {}
        
        for line in medline_text.split('\n'):
            if line.startswith('TI  - '):
                current_paper['title'] = line[6:]
            elif line.startswith('AB  - '):
                current_paper['abstract'] = line[6:]
            elif line.startswith('PMID- '):
                current_paper['pubmed_id'] = line[6:]
                current_paper['url'] = f"https://pubmed.ncbi.nlm.nih.gov/{current_paper['pubmed_id']}/"
                current_paper['source'] = 'PubMed'
            elif line.strip() == '' and current_paper:
                papers.append(current_paper)
                current_paper = {}
        
        return papers
```

#### 3. Google Scholar (via serpapi.com - Free Tier)

```python
"""Google Scholar search via SerpAPI."""

import requests
from typing import List, Dict

class ScholarSearcher:
    """Search Google Scholar."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('SERPAPI_KEY')
    
    def search(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Search Google Scholar.
        
        Args:
            query: Search query string
            max_results: Max results to return
        
        Returns:
            List of paper metadata dicts
        """
        if not self.api_key:
            print("⚠️ No SerpAPI key, skipping Scholar search")
            return []
        
        url = 'https://serpapi.com/search'
        params = {
            'engine': 'google_scholar',
            'q': query,
            'num': max_results,
            'api_key': self.api_key
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        papers = []
        for result in data.get('organic_results', []):
            papers.append({
                'title': result.get('title'),
                'authors': result.get('publication_info', {}).get('authors', []),
                'abstract': result.get('snippet'),
                'url': result.get('link'),
                'citations': result.get('inline_links', {}).get('cited_by', {}).get('total', 0),
                'source': 'Google Scholar'
            })
        
        return papers
```

### Unified Search API

```python
"""Unified paper search across multiple sources."""

from typing import List, Dict
import time

class PaperSearcher:
    """Search multiple academic databases."""
    
    def __init__(self):
        self.arxiv = ArXivSearcher()
        self.pubmed = PubMedSearcher()
        self.scholar = ScholarSearcher()
        
        self.cache = {}  # Simple in-memory cache
    
    def search_for_gaps(self, gaps: List[Dict], max_per_gap: int = 5) -> Dict[str, List[Dict]]:
        """
        Search for papers to close gaps.
        
        Args:
            gaps: List of gap objects
            max_per_gap: Max papers to find per gap
        
        Returns:
            Dict mapping gap_id -> list of suggested papers
        """
        query_gen = SearchQueryGenerator()
        suggestions = {}
        
        for gap in gaps:
            gap_id = gap['sub_requirement_id']
            query = query_gen.generate_query(gap)
            
            # Check cache
            if query in self.cache:
                suggestions[gap_id] = self.cache[query]
                continue
            
            # Search all sources
            results = []
            
            # arXiv (CS/physics papers)
            results.extend(self.arxiv.search(query, max_results=max_per_gap))
            time.sleep(3)  # Rate limit
            
            # PubMed (bio/neuro papers)
            results.extend(self.pubmed.search(query, max_results=max_per_gap))
            time.sleep(1)  # Rate limit
            
            # Google Scholar (all fields)
            results.extend(self.scholar.search(query, max_results=max_per_gap))
            
            # Deduplicate by title
            seen_titles = set()
            unique_results = []
            for paper in results:
                if paper['title'] not in seen_titles:
                    seen_titles.add(paper['title'])
                    unique_results.append(paper)
            
            # Sort by relevance (citations, recency)
            unique_results.sort(
                key=lambda p: p.get('citations', 0),
                reverse=True
            )
            
            # Take top N
            suggestions[gap_id] = unique_results[:max_per_gap]
            
            # Cache
            self.cache[query] = suggestions[gap_id]
        
        return suggestions
```

---

## API Endpoint

```python
# webdashboard/api/paper_search.py

from flask import Blueprint, request, jsonify
from literature_review.utils.paper_searcher import PaperSearcher

search_bp = Blueprint('search', __name__, url_prefix='/api/papers')

searcher = PaperSearcher()

@search_bp.route('/suggest', methods=['POST'])
def suggest_papers():
    """
    Suggest papers to close gaps.
    
    POST /api/papers/suggest
    Body: {"gaps": [...], "max_per_gap": 5}
    """
    data = request.get_json()
    gaps = data.get('gaps', [])
    max_per_gap = data.get('max_per_gap', 5)
    
    if not gaps:
        return jsonify({'error': 'No gaps provided'}), 400
    
    # Search for papers
    suggestions = searcher.search_for_gaps(gaps, max_per_gap=max_per_gap)
    
    # Format response
    return jsonify({
        'suggestions': suggestions,
        'total_papers': sum(len(papers) for papers in suggestions.values())
    }), 200
```

---

## UI Integration

```html
<!-- templates/partials/suggested_papers.html -->

<div class="suggested-papers-panel card">
    <div class="card-body">
        <h5>🔍 Suggested Papers to Close Gaps</h5>
        <p class="text-muted">Based on gap analysis, these papers may help improve coverage.</p>
        
        <button id="loadSuggestions" class="btn btn-primary">
            Search Academic Databases
        </button>
        
        <div id="suggestedPapersList" style="display: none;">
            <!-- Populated via JS -->
        </div>
    </div>
</div>
```

```javascript
async function loadSuggestedPapers(jobId) {
    // Get gaps
    const gapsResponse = await fetch(`/api/jobs/${jobId}/gaps`);
    const gapsData = await gapsResponse.json();
    
    // Search for papers
    const searchResponse = await fetch('/api/papers/suggest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            gaps: gapsData.gaps,
            max_per_gap: 5
        })
    });
    
    const suggestions = await searchResponse.json();
    
    // Display
    const list = document.getElementById('suggestedPapersList');
    list.style.display = 'block';
    
    let html = '';
    for (const [gapId, papers] of Object.entries(suggestions.suggestions)) {
        html += `
            <div class="gap-suggestions">
                <h6>Gap: ${gapId}</h6>
                <ul class="paper-list">
        `;
        
        papers.forEach(paper => {
            html += `
                <li class="suggested-paper">
                    <a href="${paper.url}" target="_blank">${paper.title}</a>
                    <small class="text-muted">
                        (${paper.source}, ${paper.citations || 0} citations)
                    </small>
                    <button class="btn btn-sm btn-outline-primary add-paper-btn"
                            data-paper='${JSON.stringify(paper)}'>
                        Add to Review
                    </button>
                </li>
            `;
        });
        
        html += '</ul></div>';
    }
    
    list.innerHTML = html;
}
```

---

## Deliverables

- [ ] Search query generator
- [ ] arXiv API integration
- [ ] PubMed API integration
- [ ] Google Scholar integration (optional)
- [ ] Unified searcher with caching
- [ ] API endpoint (`/api/papers/suggest`)
- [ ] UI integration (suggested papers panel)
- [ ] Rate limiting logic
- [ ] Unit tests

---

## Success Criteria

✅ **Functional:**
- Searches 2+ academic databases
- Returns top 10 relevant papers per gap
- Respects API rate limits
- Cache prevents duplicate searches

✅ **Quality:**
- 60%+ of suggestions are relevant
- No duplicate papers
- Results sorted by relevance

✅ **Performance:**
- <10s search time for 10 gaps
- Cache hit rate >50% after initial use

---

**Status:** 🟡 Blocked (requires Waves 1-3 validated)  
**Assignee:** TBD  
**Estimated Start:** Week 4, Day 3 (if approved)  
**Estimated Completion:** Week 4, Day 5

---

## Notes

- **Google Scholar:** Requires paid API (SerpAPI) for programmatic access. Optional.
- **arXiv/PubMed:** Free, no authentication required.
- **Rate Limits:** 
  - arXiv: 1 request/3 seconds
  - PubMed: 3 requests/second (no API key), 10/s (with key)
  - Scholar: Depends on SerpAPI plan (100 searches/month free tier)
