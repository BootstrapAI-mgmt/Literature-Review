"""Field-specific half-life presets for evidence decay.

This module provides predefined half-life values for different research fields
based on typical publication cycles and knowledge evolution rates.
"""

from typing import Dict, List


FIELD_PRESETS = {
    'ai_ml': {
        'name': 'AI & Machine Learning',
        'half_life_years': 3.0,
        'description': 'Rapidly evolving field. Papers older than 3 years may be outdated.',
        'examples': ['Deep Learning', 'NLP', 'Computer Vision', 'Reinforcement Learning'],
        'recommended_for': ['artificial intelligence', 'machine learning', 'neural networks', 'deep learning']
    },
    'software_engineering': {
        'name': 'Software Engineering',
        'half_life_years': 5.0,
        'description': 'Moderate pace. Practices evolve but core principles remain valid.',
        'examples': ['Design Patterns', 'Testing', 'DevOps', 'Agile'],
        'recommended_for': ['software', 'programming', 'development', 'engineering']
    },
    'computer_science': {
        'name': 'Computer Science (General)',
        'half_life_years': 7.0,
        'description': 'Broad field with varied sub-areas. Moderate decay rate.',
        'examples': ['Algorithms', 'Data Structures', 'HCI', 'Databases'],
        'recommended_for': ['computer science', 'algorithms', 'data structures', 'computational']
    },
    'mathematics': {
        'name': 'Mathematics',
        'half_life_years': 10.0,
        'description': 'Slow-changing field. Theorems and proofs remain valid indefinitely.',
        'examples': ['Number Theory', 'Algebra', 'Topology', 'Analysis'],
        'recommended_for': ['mathematics', 'theorem', 'proof', 'mathematical']
    },
    'medicine': {
        'name': 'Medicine & Healthcare',
        'half_life_years': 5.0,
        'description': 'Clinical guidelines update regularly. Moderate decay.',
        'examples': ['Clinical Trials', 'Treatments', 'Diagnostics', 'Public Health'],
        'recommended_for': ['medicine', 'healthcare', 'clinical', 'treatment', 'medical']
    },
    'biology': {
        'name': 'Biology & Life Sciences',
        'half_life_years': 6.0,
        'description': 'Research builds incrementally. Moderate-slow decay.',
        'examples': ['Genetics', 'Molecular Biology', 'Ecology', 'Neuroscience'],
        'recommended_for': ['biology', 'genetics', 'molecular', 'cell', 'biological']
    },
    'physics': {
        'name': 'Physics',
        'half_life_years': 8.0,
        'description': 'Foundational science. Discoveries endure.',
        'examples': ['Particle Physics', 'Astrophysics', 'Quantum Mechanics'],
        'recommended_for': ['physics', 'quantum', 'particle', 'relativity', 'physical']
    },
    'chemistry': {
        'name': 'Chemistry',
        'half_life_years': 7.0,
        'description': 'Established field with ongoing discoveries.',
        'examples': ['Organic Chemistry', 'Materials Science', 'Catalysis'],
        'recommended_for': ['chemistry', 'chemical', 'molecular', 'catalysis']
    },
    'custom': {
        'name': 'Custom',
        'half_life_years': 5.0,
        'description': 'Set your own half-life value',
        'examples': [],
        'recommended_for': []
    }
}


def get_preset(field_key: str) -> Dict:
    """Get preset configuration for a research field.
    
    Args:
        field_key: Key identifying the research field (e.g., 'ai_ml', 'mathematics')
    
    Returns:
        Dictionary containing preset configuration with keys:
        - name: Human-readable field name
        - half_life_years: Recommended half-life in years
        - description: Explanation of the field's decay characteristics
        - examples: List of example sub-fields
        - recommended_for: Keywords used for auto-detection
    
    Examples:
        >>> preset = get_preset('ai_ml')
        >>> preset['half_life_years']
        3.0
        >>> preset['name']
        'AI & Machine Learning'
    """
    return FIELD_PRESETS.get(field_key, FIELD_PRESETS['custom'])


def suggest_field_from_papers(papers: List[Dict]) -> str:
    """Auto-detect research field based on paper titles and abstracts.
    
    Analyzes paper metadata to suggest the most appropriate research field
    preset based on keyword matching.
    
    Args:
        papers: List of paper dictionaries, each optionally containing:
            - title: Paper title
            - abstract: Paper abstract
            - Any other metadata fields
    
    Returns:
        Field key of the suggested preset (e.g., 'ai_ml', 'mathematics').
        Returns 'custom' if no clear field match is found.
    
    Examples:
        >>> papers = [
        ...     {'title': 'Deep Learning for Image Recognition', 'abstract': 'Neural networks...'},
        ...     {'title': 'Attention Mechanisms in NLP', 'abstract': 'Machine learning...'}
        ... ]
        >>> suggest_field_from_papers(papers)
        'ai_ml'
    """
    if not papers:
        return 'custom'
    
    # Aggregate all text from titles and abstracts
    all_text = ' '.join([
        str(p.get('title', '')) + ' ' + str(p.get('abstract', ''))
        for p in papers
    ]).lower()
    
    # Score each field based on keyword matches
    field_scores = {}
    for field_key, preset in FIELD_PRESETS.items():
        if field_key == 'custom':
            continue
        
        keywords = preset.get('recommended_for', [])
        score = sum(all_text.count(keyword) for keyword in keywords)
        field_scores[field_key] = score
    
    # Return field with highest score
    if not field_scores or max(field_scores.values()) == 0:
        return 'custom'
    
    return max(field_scores, key=field_scores.get)


def list_all_presets() -> Dict[str, Dict]:
    """Get all available field presets.
    
    Returns:
        Dictionary mapping field keys to their preset configurations.
        Excludes 'custom' preset unless explicitly needed.
    
    Examples:
        >>> presets = list_all_presets()
        >>> 'ai_ml' in presets
        True
        >>> len(presets) >= 8
        True
    """
    return FIELD_PRESETS.copy()
