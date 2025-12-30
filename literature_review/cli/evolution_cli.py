"""
CLI for pillar evolution management.
"""

import click
import json
from pathlib import Path

from literature_review.analysis.pillar_evolution import (
    PillarEvolutionManager,
    ProposalStatus,
    ModificationType
)


@click.group()
def evolution():
    """Pillar evolution and proposal management."""
    pass


@evolution.command()
@click.option('--pillar-path', required=True, help='Path to pillar definitions')
@click.option('--proposals-path', help='Path to proposals file')
def list_proposals(pillar_path, proposals_path):
    """List all proposals."""
    manager = PillarEvolutionManager(pillar_path, proposals_path)
    
    click.echo(f"\n{'ID':<25} {'Status':<15} {'Title':<50}")
    click.echo("-" * 90)
    
    for proposal_id, proposal in manager.proposals.items():
        click.echo(f"{proposal_id:<25} {proposal.status.value:<15} {proposal.title[:50]:<50}")


@evolution.command()
@click.option('--pillar-path', required=True, help='Path to pillar definitions')
@click.option('--gap-path', required=True, help='Path to gap analysis')
@click.option('--requirement', required=True, help='Requirement ID')
@click.option('--proposals-path', help='Path to save proposals')
def create_proposal(pillar_path, gap_path, requirement, proposals_path):
    """Create a proposal from gap analysis."""
    manager = PillarEvolutionManager(pillar_path, proposals_path)
    
    with open(gap_path) as f:
        gap = json.load(f)
    
    proposal = manager.generate_proposal_from_gap(gap, requirement)
    
    if proposals_path:
        manager.save_proposals(proposals_path)
    
    click.echo(f"Created proposal: {proposal.proposal_id}")
    click.echo(f"  Title: {proposal.title}")
    click.echo(f"  Impact: {proposal.impact_assessment.risk_level}")


@evolution.command()
@click.option('--pillar-path', required=True, help='Path to pillar definitions')
@click.option('--proposals-path', required=True, help='Path to proposals file')
@click.option('--proposal-id', required=True, help='Proposal ID to submit')
def submit(pillar_path, proposals_path, proposal_id):
    """Submit a proposal for review."""
    manager = PillarEvolutionManager(pillar_path, proposals_path)
    
    proposal = manager.submit_for_review(proposal_id)
    manager.save_proposals(proposals_path)
    
    click.echo(f"Proposal {proposal_id} submitted for review")


@evolution.command()
@click.option('--pillar-path', required=True, help='Path to pillar definitions')
@click.option('--proposals-path', required=True, help='Path to proposals file')
@click.option('--proposal-id', required=True, help='Proposal ID to review')
@click.option('--reviewer', required=True, help='Reviewer name')
def start_review(pillar_path, proposals_path, proposal_id, reviewer):
    """Start reviewing a proposal."""
    manager = PillarEvolutionManager(pillar_path, proposals_path)
    
    proposal = manager.start_review(proposal_id, reviewer)
    manager.save_proposals(proposals_path)
    
    click.echo(f"Review started for {proposal_id} by {reviewer}")


@evolution.command()
@click.option('--pillar-path', required=True, help='Path to pillar definitions')
@click.option('--proposals-path', required=True, help='Path to proposals file')
@click.option('--proposal-id', required=True, help='Proposal ID to approve')
@click.option('--approver', required=True, help='Approver name')
def approve(pillar_path, proposals_path, proposal_id, approver):
    """Approve a proposal."""
    manager = PillarEvolutionManager(pillar_path, proposals_path)
    
    proposal = manager.approve_proposal(proposal_id, approver)
    manager.save_proposals(proposals_path)
    
    click.echo(f"Proposal {proposal_id} approved by {approver}")


@evolution.command()
@click.option('--pillar-path', required=True, help='Path to pillar definitions')
@click.option('--proposals-path', required=True, help='Path to proposals file')
@click.option('--proposal-id', required=True, help='Proposal ID to reject')
@click.option('--reviewer', required=True, help='Reviewer name')
@click.option('--reason', required=True, help='Rejection reason')
def reject(pillar_path, proposals_path, proposal_id, reviewer, reason):
    """Reject a proposal."""
    manager = PillarEvolutionManager(pillar_path, proposals_path)
    
    proposal = manager.reject_proposal(proposal_id, reviewer, reason)
    manager.save_proposals(proposals_path)
    
    click.echo(f"Proposal {proposal_id} rejected: {reason}")


@evolution.command()
@click.option('--pillar-path', required=True, help='Path to pillar definitions')
@click.option('--proposals-path', required=True, help='Path to proposals file')
@click.option('--proposal-id', required=True, help='Proposal ID to apply')
@click.option('--output-path', help='Path to save updated definitions')
def apply(pillar_path, proposals_path, proposal_id, output_path):
    """Apply an approved proposal."""
    manager = PillarEvolutionManager(pillar_path, proposals_path)
    
    output_path = output_path or pillar_path
    definitions, version = manager.apply_proposal(proposal_id, output_path)
    manager.save_proposals(proposals_path)
    
    click.echo(f"Applied proposal {proposal_id}")
    click.echo(f"New version: {version}")
    click.echo(f"Saved to: {output_path}")


if __name__ == "__main__":
    evolution()
