"""
Paper Sourcing Helper Script

Utilities for sourcing and managing open access papers for the golden dataset.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import urllib.request
import re


@dataclass
class PaperEntry:
    """Entry for a paper in the registry."""
    paper_id: str
    domain: str
    title: str
    authors: List[str]
    year: int
    source: str
    url: str
    pdf_filename: str
    license: str
    annotation_status: str = "pending"
    expected_claims: Optional[Dict[str, int]] = None
    notes: str = ""


class PaperRegistry:
    """Manage the paper registry for golden dataset sourcing."""
    
    DOMAINS = [
        "neuromorphic",
        "nano_thermal", 
        "fusion",
        "quantum",
        "microbio",
        "climate",
        "materials",
        "bioimaging"
    ]
    
    DOMAIN_PREFIXES = {
        "neuromorphic": "NEURO",
        "nano_thermal": "NANO",
        "fusion": "FUSION",
        "quantum": "QUANT",
        "microbio": "MICRO",
        "climate": "CLIM",
        "materials": "MATL",
        "bioimaging": "BIIMG"
    }
    
    def __init__(self, registry_path: Optional[Path] = None):
        if registry_path is None:
            registry_path = Path(__file__).parent.parent / "papers" / "paper_registry.json"
        self.registry_path = registry_path
        self.papers_dir = registry_path.parent
        self._load()
    
    def _load(self):
        """Load registry from file."""
        if self.registry_path.exists():
            with open(self.registry_path, 'r') as f:
                self.data = json.load(f)
        else:
            self.data = {
                "version": "1.0.0",
                "description": "Registry of open access papers for golden dataset annotation",
                "created_date": datetime.now().isoformat()[:10],
                "domains": self.DOMAINS,
                "papers": [],
                "statistics": {
                    "total_papers": 0,
                    "by_domain": {d: 0 for d in self.DOMAINS},
                    "annotation_status": {"pending": 0, "in_progress": 0, "complete": 0}
                }
            }
    
    def save(self):
        """Save registry to file."""
        self._update_statistics()
        with open(self.registry_path, 'w') as f:
            json.dump(self.data, f, indent=2)
        print(f"Saved registry to {self.registry_path}")
    
    def _update_statistics(self):
        """Update statistics based on current papers."""
        papers = [p for p in self.data["papers"] if p.get("annotation_status") != "example"]
        
        self.data["statistics"]["total_papers"] = len(papers)
        
        for domain in self.DOMAINS:
            self.data["statistics"]["by_domain"][domain] = len(
                [p for p in papers if p.get("domain") == domain]
            )
        
        for status in ["pending", "in_progress", "complete"]:
            self.data["statistics"]["annotation_status"][status] = len(
                [p for p in papers if p.get("annotation_status") == status]
            )
    
    def add_paper(
        self,
        domain: str,
        title: str,
        authors: List[str],
        year: int,
        source: str,
        url: str,
        license: str = "CC-BY-4.0",
        notes: str = ""
    ) -> PaperEntry:
        """Add a new paper to the registry."""
        if domain not in self.DOMAINS:
            raise ValueError(f"Invalid domain: {domain}. Must be one of {self.DOMAINS}")
        
        # Generate paper ID
        existing_count = len([p for p in self.data["papers"] 
                             if p.get("domain") == domain and p.get("annotation_status") != "example"])
        paper_id = f"{self.DOMAIN_PREFIXES[domain]}-{existing_count + 1:03d}"
        
        # Generate filename
        safe_title = re.sub(r'[^\w\s-]', '', title)[:50].strip().replace(' ', '_')
        pdf_filename = f"{domain}/{paper_id}_{safe_title}.pdf"
        
        entry = PaperEntry(
            paper_id=paper_id,
            domain=domain,
            title=title,
            authors=authors,
            year=year,
            source=source,
            url=url,
            pdf_filename=pdf_filename,
            license=license,
            notes=notes
        )
        
        self.data["papers"].append(asdict(entry))
        self.save()
        
        print(f"Added paper: {paper_id} - {title[:60]}...")
        return entry
    
    def list_papers(self, domain: Optional[str] = None) -> List[Dict]:
        """List papers, optionally filtered by domain."""
        papers = [p for p in self.data["papers"] if p.get("annotation_status") != "example"]
        if domain:
            papers = [p for p in papers if p.get("domain") == domain]
        return papers
    
    def get_status(self) -> Dict:
        """Get current status of paper sourcing."""
        self._update_statistics()
        stats = self.data["statistics"]
        
        total_target = len(self.DOMAINS) * 10  # 8 domains × 10 papers = 80
        
        print("\n=== Paper Sourcing Status ===")
        print(f"Total Papers: {stats['total_papers']}/{total_target}")
        print("\nBy Domain:")
        for domain, count in stats["by_domain"].items():
            status = "✓" if count >= 10 else "○"
            print(f"  {status} {domain}: {count}/10")
        print("\nBy Annotation Status:")
        for status, count in stats["annotation_status"].items():
            print(f"  {status}: {count}")
        
        return stats
    
    def download_arxiv(self, arxiv_id: str, domain: str) -> Optional[str]:
        """Download a paper from arXiv."""
        # Validate arXiv ID format
        if not re.match(r'^\d{4}\.\d{4,5}(v\d+)?$', arxiv_id):
            print(f"Invalid arXiv ID format: {arxiv_id}")
            return None
        
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        dest_dir = self.papers_dir / domain
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        dest_file = dest_dir / f"arxiv_{arxiv_id.replace('.', '_')}.pdf"
        
        try:
            print(f"Downloading {pdf_url}...")
            urllib.request.urlretrieve(pdf_url, dest_file)
            print(f"Saved to {dest_file}")
            return str(dest_file)
        except Exception as e:
            print(f"Error downloading: {e}")
            return None


# Curated list of recommended open access papers by domain
RECOMMENDED_PAPERS = {
    "neuromorphic": [
        {
            "title": "Spiking Neural Networks: A Survey",
            "arxiv": "2204.13969",
            "year": 2022,
            "notes": "Comprehensive SNN overview with performance comparisons"
        },
        {
            "title": "Deep Spiking Neural Networks",
            "arxiv": "2003.02944",
            "year": 2020,
            "notes": "Deep learning techniques for SNNs"
        },
        {
            "title": "Event-based Vision: A Survey",
            "arxiv": "1904.08405",
            "year": 2019,
            "notes": "DVS and event cameras, good for sensor claims"
        },
        {
            "title": "Training Spiking Neural Networks Using Lessons From Deep Learning",
            "arxiv": "2109.12894",
            "year": 2021,
            "notes": "Surrogate gradients and training techniques"
        },
    ],
    "nano_thermal": [
        {
            "title": "A Review on Nanofluids: Preparation, Stability Mechanisms, and Applications",
            "arxiv": "2103.08547",
            "year": 2021,
            "notes": "Nanofluid thermal properties overview"
        },
        {
            "title": "Heat Transfer Enhancement Using Nanofluids",
            "source": "Renewable and Sustainable Energy Reviews (Elsevier Open)",
            "year": 2020,
            "notes": "Quantitative thermal conductivity improvements"
        },
        {
            "title": "Thermal Conductivity of Nanoparticle Suspensions",
            "arxiv": "cond-mat/0511290",
            "year": 2005,
            "notes": "Classic paper on nanoparticle thermal effects"
        },
        {
            "title": "Heat Transfer in Nanofluids: A Review",
            "source": "Applied Thermal Engineering (open articles)",
            "year": 2019,
            "notes": "Experimental validation of heat transfer models"
        },
    ],
    "fusion": [
        {
            "title": "Progress in the ITER Physics Basis",
            "source": "Nuclear Fusion (IOP Open)",
            "year": 2007,
            "notes": "Foundational ITER physics documentation"
        },
        {
            "title": "Achieving a Long-Pulsed High-Confinement Plasma in EAST",
            "arxiv": "2201.10687",
            "year": 2022,
            "notes": "EAST tokamak experimental results"
        },
        {
            "title": "Stellarator Optimization",
            "arxiv": "2204.00833",
            "year": 2022,
            "notes": "Wendelstein 7-X and stellarator design"
        },
        {
            "title": "Inertial Confinement Fusion: Status and Prospects",
            "source": "DOE OSTI",
            "year": 2023,
            "notes": "NIF breakthrough context"
        },
        {
            "title": "Plasma Instabilities and Turbulence in Tokamaks",
            "arxiv": "physics/0501089",
            "year": 2005,
            "notes": "Plasma physics fundamentals"
        },
    ],
    "quantum": [
        {
            "title": "Quantum Computing: An Overview Across the System Stack",
            "arxiv": "1905.07714",
            "year": 2019,
            "notes": "Comprehensive quantum computing survey"
        },
        {
            "title": "Quantum Error Correction: An Introductory Guide",
            "arxiv": "1907.11157",
            "year": 2019,
            "notes": "Error correction fundamentals"
        },
        {
            "title": "Quantum Supremacy Using a Programmable Superconducting Processor",
            "arxiv": "1910.11333",
            "year": 2019,
            "notes": "Google's quantum supremacy paper"
        },
        {
            "title": "Variational Quantum Eigensolver Review",
            "arxiv": "2111.05176",
            "year": 2021,
            "notes": "VQE algorithms and applications"
        },
    ],
    "microbio": [
        {
            "title": "CRISPR-Cas9: A Revolutionary Tool for Genome Editing",
            "source": "eLife",
            "year": 2020,
            "notes": "CRISPR mechanism and applications"
        },
        {
            "title": "The Human Microbiome: A Systematic Review",
            "source": "PLOS Biology",
            "year": 2019,
            "notes": "Microbiome health associations"
        },
        {
            "title": "Antibiotic Resistance Mechanisms in Bacteria",
            "source": "PubMed Central",
            "year": 2021,
            "notes": "AMR mechanisms and epidemiology"
        },
        {
            "title": "Single-Cell RNA Sequencing Technologies",
            "arxiv": "1908.02203",
            "year": 2019,
            "notes": "scRNA-seq methods comparison"
        },
    ],
    "climate": [
        {
            "title": "Climate Model Intercomparison Project (CMIP6)",
            "source": "Earth System Science Data",
            "year": 2020,
            "notes": "CMIP6 model documentation"
        },
        {
            "title": "Sea Level Rise Projections for the 21st Century",
            "arxiv": "2109.00846",
            "year": 2021,
            "notes": "Ice sheet contributions to SLR"
        },
        {
            "title": "Global Carbon Budget 2023",
            "source": "Earth System Science Data (Copernicus)",
            "year": 2023,
            "notes": "Annual carbon flux estimates"
        },
        {
            "title": "Attribution of Extreme Weather Events",
            "source": "Nature Climate Change (open)",
            "year": 2022,
            "notes": "Extreme event attribution methods"
        },
    ],
    "materials": [
        {
            "title": "Lithium-Ion Battery Materials: Present and Future",
            "arxiv": "2106.01452",
            "year": 2021,
            "notes": "Battery cathode/anode materials review"
        },
        {
            "title": "Room-Temperature Superconductivity: Current Status",
            "arxiv": "2308.14847",
            "year": 2023,
            "notes": "LK-99 controversy and RTSC progress"
        },
        {
            "title": "Two-Dimensional Materials Beyond Graphene",
            "arxiv": "1801.05233",
            "year": 2018,
            "notes": "2D materials survey: TMDs, phosphorene, etc."
        },
        {
            "title": "High-Entropy Alloys: A Review",
            "source": "npj Computational Materials",
            "year": 2020,
            "notes": "HEA design and properties"
        },
        {
            "title": "Metamaterials and Metasurfaces",
            "arxiv": "2001.01456",
            "year": 2020,
            "notes": "Electromagnetic metamaterial applications"
        },
    ],
    "bioimaging": [
        {
            "title": "Deep Learning for Medical Image Analysis",
            "arxiv": "1702.05747",
            "year": 2017,
            "notes": "CNN applications in radiology"
        },
        {
            "title": "Compressed Sensing MRI: A Review",
            "arxiv": "2001.03286",
            "year": 2020,
            "notes": "CS reconstruction techniques"
        },
        {
            "title": "PET/CT in Oncology: Clinical Applications",
            "source": "PubMed Central",
            "year": 2021,
            "notes": "PET imaging quantification"
        },
        {
            "title": "Ultrasound Image Segmentation: A Survey",
            "arxiv": "2108.10340",
            "year": 2021,
            "notes": "US segmentation methods comparison"
        },
        {
            "title": "Physics-Informed Neural Networks for Medical Imaging",
            "arxiv": "2205.08224",
            "year": 2022,
            "notes": "PINN applications in imaging"
        },
    ]
}


def print_recommended_papers():
    """Print recommended papers for each domain."""
    print("\n=== Recommended Open Access Papers ===\n")
    
    for domain, papers in RECOMMENDED_PAPERS.items():
        print(f"\n## {domain.upper()} ({len(papers)} suggestions)")
        print("-" * 50)
        for p in papers:
            source = p.get("arxiv", p.get("source", "unknown"))
            if "arxiv" in p:
                source = f"arXiv:{p['arxiv']}"
            print(f"  • {p['title']}")
            print(f"    Year: {p['year']} | Source: {source}")
            print(f"    Notes: {p['notes']}")
            print()


def main():
    """Interactive paper management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Paper sourcing helper")
    parser.add_argument("command", choices=["status", "add", "list", "recommend", "download"],
                       help="Command to run")
    parser.add_argument("--domain", "-d", help="Domain filter")
    parser.add_argument("--arxiv", help="arXiv ID for download")
    
    args = parser.parse_args()
    
    registry = PaperRegistry()
    
    if args.command == "status":
        registry.get_status()
    elif args.command == "list":
        papers = registry.list_papers(args.domain)
        for p in papers:
            print(f"{p['paper_id']}: {p['title'][:60]}... ({p['annotation_status']})")
    elif args.command == "recommend":
        print_recommended_papers()
    elif args.command == "download" and args.arxiv and args.domain:
        registry.download_arxiv(args.arxiv, args.domain)
    else:
        print("Use: python source_papers.py [status|list|recommend|download]")


if __name__ == "__main__":
    main()
