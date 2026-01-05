"""
Gold Standard Loader
Loads and parses YAML gold standard definition files.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml


class GoldStandardLoader:
    """Loads gold standard YAML files for validation comparison"""
    
    def __init__(self, path: Path):
        self.path = Path(path)
        self._data: Optional[Dict] = None
    
    def load(self) -> Dict:
        """Load the YAML file and return as dictionary"""
        if self._data is not None:
            return self._data
        
        if not self.path.exists():
            raise FileNotFoundError(f"Gold standard file not found: {self.path}")
        
        with open(self.path, 'r', encoding='utf-8') as f:
            self._data = yaml.safe_load(f)
        
        return self._data or {}
    
    def get_section(self, section_name: str) -> Dict:
        """Get a specific section from the gold standard"""
        data = self.load()
        sections = data.get('sections', [])
        for section in sections:
            if section.get('name') == section_name:
                return section
        return {}
    
    def get_rules(self, section_name: str) -> List[Dict]:
        """Get validation rules for a section"""
        section = self.get_section(section_name)
        return section.get('rules', [])
    
    def get_required_modules(self) -> List[str]:
        """Get list of required modules from architecture gold standard"""
        data = self.load()
        modules = []
        for section in data.get('sections', []):
            if section.get('validation_type') == 'module_coverage':
                for mod in section.get('required_modules', []):
                    if mod.get('documented'):
                        modules.append(mod.get('path', ''))
        return [m for m in modules if m]
    
    def get_required_outputs(self) -> List[str]:
        """Get list of required output files"""
        data = self.load()
        outputs = []
        for section in data.get('sections', []):
            if section.get('validation_type') == 'output_coverage':
                for out in section.get('required_outputs', []):
                    if out.get('documented'):
                        outputs.append(out.get('name', ''))
        return [o for o in outputs if o]
    
    def get_freshness_threshold(self) -> int:
        """Get max age in days before document is considered stale"""
        data = self.load()
        freshness = data.get('freshness', {})
        return freshness.get('max_age_days', 7)
    
    def get_expected_wave_status(self, wave_name: str) -> Dict:
        """Get expected status for a development wave"""
        data = self.load()
        for section in data.get('sections', []):
            if section.get('name') == wave_name:
                return section.get('expected_state', {})
        return {}


def load_yaml(path: Path) -> Dict:
    """Convenience function to load a YAML file"""
    loader = GoldStandardLoader(path)
    return loader.load()
