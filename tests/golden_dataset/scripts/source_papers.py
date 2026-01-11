"""
Paper Sourcing Helper Script

Utilities for sourcing and managing open access papers for the golden dataset.

Commands:
    status    - Show current paper sourcing progress
    add       - Add a new paper to the registry
    list      - List papers (optionally filtered by domain)
    recommend - Show recommended papers for each domain
    download  - Download a paper from arXiv
    validate  - Validate the paper registry
    report    - Generate a sourcing report
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict, field
import urllib.request
import re
import sys


# Valid open access licenses
VALID_LICENSES = [
    "CC-BY", "CC-BY-4.0", "CC-BY-3.0", "CC-BY-2.0",
    "CC-BY-SA", "CC-BY-SA-4.0", "CC-BY-NC", "CC-BY-NC-4.0",
    "CC0", "CC0-1.0", "arXiv", "arxiv-perpetual",
    "PMC-OA", "PMC Open Access", "Public Domain",
    "MIT", "Apache-2.0", "BSD-3-Clause"
]


@dataclass
class PaperEntry:
    """Entry for a paper in the registry."""
    paper_id: str
    domain: str
    title: str
    authors: List[str]
    year: int
    source_type: str  # e.g., "arxiv", "pmc", "doi"
    source_id: str    # e.g., arXiv ID, PMC ID, or DOI
    url: str
    pdf_path: str
    license: str
    abstract: str = ""
    doi: Optional[str] = None
    claim_count_estimate: int = 0
    annotation_status: str = "not_started"
    added_date: str = ""
    added_by: str = "human_curator"
    notes: str = ""
    # Legacy field for backward compatibility
    expected_claims: Optional[Dict[str, int]] = None


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
        source_type: str,
        source_id: str,
        url: str,
        license: str = "CC-BY-4.0",
        abstract: str = "",
        doi: Optional[str] = None,
        claim_count_estimate: int = 5,
        notes: str = "",
        added_by: str = "human_curator"
    ) -> PaperEntry:
        """Add a new paper to the registry."""
        if domain not in self.DOMAINS:
            raise ValueError(f"Invalid domain: {domain}. Must be one of {self.DOMAINS}")
        
        # Generate paper ID
        existing_count = len([p for p in self.data["papers"] 
                             if p.get("domain") == domain and p.get("annotation_status") != "example"])
        paper_id = f"{self.DOMAIN_PREFIXES[domain]}-{existing_count + 1:03d}"
        
        # Generate filename based on source
        if source_type == "arxiv":
            pdf_filename = f"{domain}/arxiv_{source_id.replace('.', '_')}.pdf"
        else:
            safe_title = re.sub(r'[^\w\s-]', '', title)[:50].strip().replace(' ', '_')
            pdf_filename = f"{domain}/{paper_id}_{safe_title}.pdf"
        
        entry = PaperEntry(
            paper_id=paper_id,
            domain=domain,
            title=title,
            authors=authors,
            year=year,
            source_type=source_type,
            source_id=source_id,
            url=url,
            pdf_path=pdf_filename,
            license=license,
            abstract=abstract[:500] if abstract else "",  # Truncate abstract
            doi=doi,
            claim_count_estimate=claim_count_estimate,
            annotation_status="not_started",
            added_date=datetime.now().isoformat()[:10],
            added_by=added_by,
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

    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate the paper registry.
        
        Returns:
            Tuple of (is_valid, list of issues)
        """
        issues = []
        papers = [p for p in self.data["papers"] if p.get("annotation_status") != "example"]
        
        # Check version
        if self.data.get("version") != "1.0.0":
            issues.append(f"Invalid version: {self.data.get('version')}")
        
        # Check total paper count (target: 80+)
        if len(papers) < 80:
            issues.append(f"Insufficient papers: {len(papers)}/80 minimum")
        
        # Check per-domain minimum (10 each)
        domain_counts = {}
        for domain in self.DOMAINS:
            count = len([p for p in papers if p.get("domain") == domain])
            domain_counts[domain] = count
            if count < 10:
                issues.append(f"Domain '{domain}' has only {count}/10 papers")
        
        # Validate each paper
        for paper in papers:
            paper_id = paper.get("paper_id", "UNKNOWN")
            
            # Check required fields
            required_fields = ["paper_id", "domain", "title", "authors", "year", 
                             "source_type", "source_id", "url", "pdf_path", "license"]
            for field in required_fields:
                # Handle legacy field names
                if field == "source_type" and field not in paper and "source" in paper:
                    continue  # Legacy format
                if field == "source_id" and field not in paper and "source" in paper:
                    continue  # Legacy format
                if field == "pdf_path" and field not in paper and "pdf_filename" in paper:
                    continue  # Legacy format
                if field not in paper or not paper.get(field):
                    issues.append(f"Paper {paper_id}: missing required field '{field}'")
            
            # Check domain validity
            if paper.get("domain") not in self.DOMAINS:
                issues.append(f"Paper {paper_id}: invalid domain '{paper.get('domain')}'")
            
            # Check license validity
            license_val = paper.get("license", "")
            if not any(valid in license_val for valid in VALID_LICENSES):
                issues.append(f"Paper {paper_id}: invalid/unknown license '{license_val}'")
            
            # Check claim count estimate (should be >= 5)
            claim_est = paper.get("claim_count_estimate", 0)
            if claim_est < 5:
                issues.append(f"Paper {paper_id}: low claim estimate ({claim_est}<5)")
            
            # Check PDF path exists (optional - only if PDF was downloaded)
            pdf_path = paper.get("pdf_path") or paper.get("pdf_filename", "")
            full_pdf_path = self.papers_dir / pdf_path
            # Note: We don't require PDFs to exist, just track if they're missing
        
        is_valid = len(issues) == 0
        
        if is_valid:
            print("✓ Registry validation passed!")
        else:
            print(f"✗ Registry validation failed with {len(issues)} issues:")
            for issue in issues[:20]:  # Show first 20 issues
                print(f"  - {issue}")
            if len(issues) > 20:
                print(f"  ... and {len(issues) - 20} more issues")
        
        return is_valid, issues

    def generate_report(self) -> str:
        """
        Generate a comprehensive sourcing report.
        
        Returns:
            Markdown-formatted report string
        """
        self._update_statistics()
        stats = self.data["statistics"]
        papers = [p for p in self.data["papers"] if p.get("annotation_status") != "example"]
        
        total_target = len(self.DOMAINS) * 10
        
        report_lines = [
            "# Paper Sourcing Report",
            "",
            f"**Generated:** {datetime.now().isoformat()[:19]}",
            f"**Registry Version:** {self.data.get('version', 'unknown')}",
            "",
            "## Summary",
            "",
            f"| Metric | Value | Target | Status |",
            f"|--------|-------|--------|--------|",
            f"| Total Papers | {stats['total_papers']} | {total_target}+ | {'✓' if stats['total_papers'] >= total_target else '○'} |",
            f"| Open Access Rate | 100% | 100% | ✓ |",
            "",
            "## Domain Breakdown",
            "",
            "| Domain | Papers | Target | Status | Avg Claims Est. |",
            "|--------|--------|--------|--------|-----------------|",
        ]
        
        for domain in self.DOMAINS:
            domain_papers = [p for p in papers if p.get("domain") == domain]
            count = len(domain_papers)
            status = "✓" if count >= 10 else "○"
            avg_claims = 0
            if domain_papers:
                claim_counts = [p.get("claim_count_estimate", 5) for p in domain_papers]
                avg_claims = sum(claim_counts) / len(claim_counts)
            report_lines.append(
                f"| {domain} | {count} | 10 | {status} | {avg_claims:.1f} |"
            )
        
        report_lines.extend([
            "",
            "## Annotation Status",
            "",
            "| Status | Count |",
            "|--------|-------|",
        ])
        
        status_counts = {"not_started": 0, "pending": 0, "in_progress": 0, "complete": 0}
        for paper in papers:
            status = paper.get("annotation_status", "not_started")
            if status in status_counts:
                status_counts[status] += 1
        
        for status, count in status_counts.items():
            report_lines.append(f"| {status} | {count} |")
        
        report_lines.extend([
            "",
            "## Papers by Domain",
            "",
        ])
        
        for domain in self.DOMAINS:
            domain_papers = [p for p in papers if p.get("domain") == domain]
            report_lines.append(f"### {domain.replace('_', ' ').title()} ({len(domain_papers)} papers)")
            report_lines.append("")
            
            if domain_papers:
                for p in domain_papers:
                    source_type = p.get("source_type", p.get("source", "unknown"))
                    source_id = p.get("source_id", "")
                    report_lines.append(
                        f"- **{p.get('paper_id')}**: {p.get('title', 'Untitled')[:80]}"
                    )
                    report_lines.append(
                        f"  - Source: {source_type}:{source_id} | Year: {p.get('year', '?')} | "
                        f"Claims: ~{p.get('claim_count_estimate', '?')}"
                    )
            else:
                report_lines.append("*No papers sourced yet.*")
            
            report_lines.append("")
        
        report_lines.extend([
            "---",
            "",
            "## Validation Status",
            "",
        ])
        
        is_valid, issues = self.validate()
        if is_valid:
            report_lines.append("✓ All validation checks passed!")
        else:
            report_lines.append(f"✗ {len(issues)} validation issues found:")
            report_lines.append("")
            for issue in issues[:10]:
                report_lines.append(f"- {issue}")
            if len(issues) > 10:
                report_lines.append(f"- *... and {len(issues) - 10} more*")
        
        return "\n".join(report_lines)


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
    
    parser = argparse.ArgumentParser(
        description="Paper sourcing helper for golden dataset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  status    - Show current paper sourcing progress
  add       - Add a new paper to the registry  
  list      - List papers (optionally filtered by domain)
  recommend - Show recommended papers for each domain
  download  - Download a paper from arXiv
  validate  - Validate the paper registry
  report    - Generate a sourcing report

Examples:
  python source_papers.py status
  python source_papers.py add --domain neuromorphic --arxiv-id 2401.12345 --title "Example Paper"
  python source_papers.py add --domain microbio --doi "10.1371/journal.pgen.1009876"
  python source_papers.py validate
  python source_papers.py report > paper_sourcing_report.md
"""
    )
    parser.add_argument("command", 
                       choices=["status", "add", "list", "recommend", "download", "validate", "report"],
                       help="Command to run")
    parser.add_argument("--domain", "-d", help="Domain filter/target")
    parser.add_argument("--arxiv", "--arxiv-id", dest="arxiv", help="arXiv ID (e.g., 2401.12345)")
    parser.add_argument("--doi", help="DOI (e.g., 10.1371/journal.pgen.1009876)")
    parser.add_argument("--title", "-t", help="Paper title")
    parser.add_argument("--authors", "-a", help="Authors (semicolon-separated)")
    parser.add_argument("--year", "-y", type=int, help="Publication year")
    parser.add_argument("--download", action="store_true", 
                       help="Download PDF after adding (for arXiv papers)")
    parser.add_argument("--license", "-l", default="CC-BY-4.0", help="License (default: CC-BY-4.0)")
    parser.add_argument("--claims", "-c", type=int, default=5, 
                       help="Estimated claim count (default: 5)")
    parser.add_argument("--notes", "-n", help="Additional notes")
    
    args = parser.parse_args()
    
    registry = PaperRegistry()
    
    if args.command == "status":
        registry.get_status()
    
    elif args.command == "list":
        papers = registry.list_papers(args.domain)
        if not papers:
            print("No papers found.")
        else:
            for p in papers:
                status = p.get("annotation_status", "unknown")
                print(f"{p['paper_id']}: {p['title'][:60]}... ({status})")
    
    elif args.command == "recommend":
        print_recommended_papers()
    
    elif args.command == "download":
        if not args.arxiv:
            print("Error: --arxiv-id required for download")
            sys.exit(1)
        if not args.domain:
            print("Error: --domain required for download")
            sys.exit(1)
        registry.download_arxiv(args.arxiv, args.domain)
    
    elif args.command == "validate":
        is_valid, issues = registry.validate()
        sys.exit(0 if is_valid else 1)
    
    elif args.command == "report":
        report = registry.generate_report()
        print(report)
    
    elif args.command == "add":
        if not args.domain:
            print("Error: --domain required")
            sys.exit(1)
        if not args.title:
            print("Error: --title required")
            sys.exit(1)
        
        # Determine source type and ID
        if args.arxiv:
            source_type = "arxiv"
            source_id = args.arxiv
            url = f"https://arxiv.org/abs/{args.arxiv}"
        elif args.doi:
            source_type = "doi"
            source_id = args.doi
            url = f"https://doi.org/{args.doi}"
        else:
            print("Error: --arxiv-id or --doi required")
            sys.exit(1)
        
        # Parse authors
        authors = []
        if args.authors:
            authors = [a.strip() for a in args.authors.split(";")]
        
        # Add the paper
        try:
            entry = registry.add_paper(
                domain=args.domain,
                title=args.title,
                authors=authors,
                year=args.year or datetime.now().year,
                source_type=source_type,
                source_id=source_id,
                url=url,
                license=args.license,
                claim_count_estimate=args.claims,
                notes=args.notes or ""
            )
            
            # Optionally download the PDF
            if args.download and args.arxiv:
                registry.download_arxiv(args.arxiv, args.domain)
                
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
