"""
Research Configuration Loader

Provides a centralized interface for loading and accessing 
research-domain-specific configuration. This module decouples 
domain-specific knowledge from the core pipeline processing logic.

Usage:
    from literature_review.config import load_config, get_config
    
    # At application startup
    load_config("research_config.json")
    
    # In any module that needs research context
    config = get_config()
    prompt = f"Analyze for {config.short_description}"
"""

import json
import os
import logging
import warnings
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# =============================================================================
# LEGACY FALLBACK VALUES (for backward compatibility during migration)
# =============================================================================

_LEGACY_RESEARCH_TOPIC = (
    "The mapping of human brain functions to machine learning frameworks, "
    "specifically in the areas of skill acquisition, memory consolidation, "
    "and stimulus-response, with emphasis on neuromorphic computing architectures."
)

_LEGACY_SHORT_DESCRIPTION = "neuromorphic computing and brain-inspired AI"

_LEGACY_DATABASE_FILENAME = "neuromorphic-research_database.csv"

_LEGACY_RESEARCHER_ROLE = (
    "PhD-level research assistant specializing in literature review "
    "for neuromorphic computing and neuroscience"
)


# =============================================================================
# RESEARCH CONFIG DATACLASS
# =============================================================================

@dataclass
class ResearchConfig:
    """
    Holds loaded research configuration.
    
    This dataclass provides typed access to all research-domain-specific
    configuration values, making it easy to use in prompts and file operations.
    
    Attributes:
        domain_id: Unique identifier for the research domain (e.g., "neuromorphic-computing")
        domain_name: Human-readable name for the domain
        research_topic: The primary research question/topic (full text)
        short_description: Brief description for use in prompts
        researcher_role: Role description for AI prompts
        domain_focus: Focus area description
        example_domains: List of example domain names for prompts
        example_subdomains: List of example subdomain names
        example_keywords: List of example keywords
        primary_keywords: Primary vocabulary for the domain
        secondary_keywords: Secondary/technical vocabulary
        database_filename: Generated filename for the research database
        pillar_definitions: Loaded pillar definitions dict
        raw_config: The full raw configuration dict
    """
    domain_id: str
    domain_name: str
    research_topic: str
    short_description: str
    researcher_role: str
    domain_focus: str
    example_domains: List[str]
    example_subdomains: List[str]
    example_keywords: List[str]
    primary_keywords: List[str]
    secondary_keywords: List[str]
    database_filename: str
    non_journal_filename: str
    pillar_definitions_file: str
    pillar_definitions: dict
    proof_goal: str
    proof_failure_message: str
    search_query_prefix: str
    ai_pillar_context: str
    raw_config: dict
    
    @classmethod
    def load(cls, config_path: str = "research_config.json") -> "ResearchConfig":
        """
        Load research configuration from JSON file.
        
        Args:
            config_path: Path to the research_config.json file
            
        Returns:
            ResearchConfig instance with all values loaded
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            KeyError: If required configuration keys are missing
            json.JSONDecodeError: If config file is not valid JSON
        """
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(
                f"Research configuration file not found: {config_path}\n"
                "Please create a research_config.json file or specify the correct path."
            )
        
        logger.info(f"Loading research configuration from: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Extract nested configuration sections
        domain = config['domain']
        topic = config['research_topic']
        prompt_ctx = config['prompt_context']
        vocab = config['vocabulary']
        naming = config['file_naming']
        search_ctx = config.get('search_context', {})
        proof_chain = config.get('proof_chain', {})
        
        # Generate filenames from templates
        database_filename = naming['database'].format(domain_id=domain['id'])
        non_journal_filename = naming.get('non_journal', '{domain_id}-non_journal_database.csv').format(domain_id=domain['id'])
        
        # Load pillar definitions
        pillar_file = config.get('pillar_definitions_file', 'pillar_definitions.json')
        pillar_definitions = cls._load_pillar_definitions(pillar_file, config_path.parent)
        
        return cls(
            domain_id=domain['id'],
            domain_name=domain['name'],
            research_topic=topic['primary'],
            short_description=topic['short_description'],
            researcher_role=prompt_ctx['researcher_role'],
            domain_focus=prompt_ctx['domain_focus'],
            example_domains=prompt_ctx.get('example_domains', []),
            example_subdomains=prompt_ctx.get('example_subdomains', []),
            example_keywords=prompt_ctx.get('example_keywords', []),
            primary_keywords=vocab.get('primary_keywords', []),
            secondary_keywords=vocab.get('secondary_keywords', []),
            database_filename=database_filename,
            non_journal_filename=non_journal_filename,
            pillar_definitions_file=pillar_file,
            pillar_definitions=pillar_definitions,
            proof_goal=proof_chain.get('ultimate_goal', ''),
            proof_failure_message=proof_chain.get('failure_message', ''),
            search_query_prefix=search_ctx.get('default_query_prefix', ''),
            ai_pillar_context=search_ctx.get('ai_pillar_context', ''),
            raw_config=config
        )
    
    @staticmethod
    def _load_pillar_definitions(pillar_file: str, config_dir: Path) -> dict:
        """Load pillar definitions from JSON file."""
        # Try relative to config directory first, then absolute/cwd
        pillar_path = config_dir / pillar_file
        if not pillar_path.exists():
            pillar_path = Path(pillar_file)
        
        if not pillar_path.exists():
            logger.warning(f"Pillar definitions file not found: {pillar_file}")
            return {}
        
        with open(pillar_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_pillar_definitions_str(self) -> str:
        """Return pillar definitions as formatted JSON string for prompts."""
        return json.dumps(self.pillar_definitions, indent=2)
    
    def get_example_domains_str(self) -> str:
        """Return example domains as comma-separated string."""
        return ", ".join(f'"{d}"' for d in self.example_domains)
    
    def get_example_subdomains_str(self) -> str:
        """Return example subdomains as comma-separated string."""
        return ", ".join(f'"{s}"' for s in self.example_subdomains)
    
    def get_example_keywords_str(self) -> str:
        """Return example keywords as comma-separated string."""
        return ", ".join(f'"{k}"' for k in self.example_keywords)


# =============================================================================
# GLOBAL SINGLETON MANAGEMENT
# =============================================================================

_config: Optional[ResearchConfig] = None


def load_config(config_path: str = "research_config.json") -> ResearchConfig:
    """
    Load and cache research configuration.
    
    This should be called once at application startup. After loading,
    use get_config() to access the configuration from any module.
    
    Args:
        config_path: Path to research_config.json
        
    Returns:
        Loaded ResearchConfig instance
    """
    global _config
    _config = ResearchConfig.load(config_path)
    logger.info(f"Loaded research configuration for domain: {_config.domain_id}")
    return _config


def get_config() -> ResearchConfig:
    """
    Get cached research configuration.
    
    Returns:
        Cached ResearchConfig instance
        
    Raises:
        RuntimeError: If load_config() has not been called
    """
    if _config is None:
        raise RuntimeError(
            "Research configuration not loaded. "
            "Call load_config() at application startup before using get_config()."
        )
    return _config


def reset_config() -> None:
    """
    Reset cached configuration.
    
    Useful for testing or when switching between research domains.
    """
    global _config
    _config = None
    logger.info("Research configuration reset")


def is_config_loaded() -> bool:
    """Check if configuration has been loaded."""
    return _config is not None


# =============================================================================
# LEGACY FALLBACK HELPERS (for backward compatibility during migration)
# =============================================================================

def get_research_topic_safe() -> str:
    """
    Get research topic with fallback to legacy hardcoded value.
    
    Use this during migration to maintain backward compatibility.
    Emits a deprecation warning when using fallback.
    """
    try:
        return get_config().research_topic
    except RuntimeError:
        warnings.warn(
            "Using legacy hardcoded research topic. "
            "Please create research_config.json and call load_config() at startup.",
            DeprecationWarning,
            stacklevel=2
        )
        return _LEGACY_RESEARCH_TOPIC


def get_short_description_safe() -> str:
    """Get short description with fallback to legacy value."""
    try:
        return get_config().short_description
    except RuntimeError:
        warnings.warn(
            "Using legacy hardcoded short description. "
            "Please create research_config.json.",
            DeprecationWarning,
            stacklevel=2
        )
        return _LEGACY_SHORT_DESCRIPTION


def get_database_filename_safe() -> str:
    """Get database filename with fallback to legacy value."""
    try:
        return get_config().database_filename
    except RuntimeError:
        warnings.warn(
            "Using legacy hardcoded database filename. "
            "Please create research_config.json.",
            DeprecationWarning,
            stacklevel=2
        )
        return _LEGACY_DATABASE_FILENAME


def get_researcher_role_safe() -> str:
    """Get researcher role with fallback to legacy value."""
    try:
        return get_config().researcher_role
    except RuntimeError:
        warnings.warn(
            "Using legacy hardcoded researcher role. "
            "Please create research_config.json.",
            DeprecationWarning,
            stacklevel=2
        )
        return _LEGACY_RESEARCHER_ROLE
