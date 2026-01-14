"""
Golden Dataset Population Script

Creates annotated samples from existing review data and manual annotation.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import hashlib

# Import schema models
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from schema import (
    AnnotatedClaim,
    EvidenceQualityAnnotation,
    ExpectedVerdict,
    KnownGap,
    RecommendationQuality,
    GoldenDataset,
    Verdict,
    ConfidenceLevel
)


class GoldenDatasetPopulator:
    """
    Populate golden dataset from various sources.
    
    Sources:
    1. Existing version history (reviewed claims)
    2. Manual annotation files
    3. Synthetic test cases
    """
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.claims: List[AnnotatedClaim] = []
        self.verdicts: List[ExpectedVerdict] = []
        self.gaps: List[KnownGap] = []
        self.recommendations: List[RecommendationQuality] = []
        
        self.claim_counter = 0
        self.gap_counter = 0
    
    def generate_claim_id(self) -> str:
        """Generate unique claim ID."""
        self.claim_counter += 1
        return f"GD-CLM-{self.claim_counter:04d}"
    
    def generate_gap_id(self) -> str:
        """Generate unique gap ID."""
        self.gap_counter += 1
        return f"GD-GAP-{self.gap_counter:04d}"
    
    def add_annotated_claim(
        self,
        source_paper: str,
        claim_text: str,
        evidence_text: str,
        pillar: str,
        requirement: str,
        sub_requirement: str,
        mapping_rationale: str,
        verdict: str,
        verdict_rationale: str,
        confidence: str,
        strength: int,
        rigor: int,
        relevance: int,
        directness: int,
        reproducibility: int,
        evidence_rationale: str,
        test_categories: List[str],
        is_edge_case: bool = False,
        edge_case_type: Optional[str] = None,
        source_page: Optional[int] = None,
        recency_bonus: float = 0.5
    ) -> AnnotatedClaim:
        """Add an annotated claim to the dataset."""
        
        claim = AnnotatedClaim(
            claim_id=self.generate_claim_id(),
            dataset_version="1.0.0",
            source_paper=source_paper,
            source_page=source_page,
            claim_text=claim_text,
            evidence_text=evidence_text,
            correct_pillar=pillar,
            correct_requirement=requirement,
            correct_sub_requirement=sub_requirement,
            mapping_rationale=mapping_rationale,
            expected_verdict=Verdict(verdict),
            verdict_rationale=verdict_rationale,
            verdict_confidence=ConfidenceLevel(confidence),
            evidence_quality=EvidenceQualityAnnotation(
                strength_score=strength,
                rigor_score=rigor,
                relevance_score=relevance,
                directness=directness,
                reproducibility_score=reproducibility,
                recency_bonus=recency_bonus,
                rationale=evidence_rationale
            ),
            annotator_ids=["golden_annotator_001"],
            annotation_date=datetime.now(),
            test_categories=test_categories,
            is_edge_case=is_edge_case,
            edge_case_type=edge_case_type
        )
        
        self.claims.append(claim)
        
        # Auto-generate expected verdict entry
        composite = claim.evidence_quality.composite_score
        self.verdicts.append(ExpectedVerdict(
            claim_id=claim.claim_id,
            expected_verdict=Verdict(verdict),
            expected_composite_score_range=(composite - 0.5, composite + 0.5),
            expected_strength_range=(max(1, strength - 1), min(5, strength + 1)),
            expected_relevance_range=(max(1, relevance - 1), min(5, relevance + 1)),
            true_positive_probability=0.9 if verdict == "approved" else (0.5 if verdict == "borderline" else 0.1),
            rejection_reasons=[] if verdict == "approved" else ["Insufficient evidence"]
        ))
        
        return claim
    
    def add_known_gap(
        self,
        pillar: str,
        requirement_id: str,
        sub_requirement_id: str,
        requirement_text: str,
        current_completeness: float,
        severity: str,
        database_state_file: str,
        why_is_gap: str,
        recommendation_themes: Optional[List[str]] = None,
        reference_recommendation: Optional[str] = None
    ) -> KnownGap:
        """Add a known gap to the dataset."""
        
        gap = KnownGap(
            gap_id=self.generate_gap_id(),
            dataset_version="1.0.0",
            pillar=pillar,
            requirement_id=requirement_id,
            sub_requirement_id=sub_requirement_id,
            requirement_text=requirement_text,
            current_completeness=current_completeness,
            expected_severity=severity,
            database_state_file=database_state_file,
            why_is_gap=why_is_gap,
            expected_in_report=True
        )
        
        self.gaps.append(gap)
        
        # Add recommendation if provided
        if recommendation_themes and reference_recommendation:
            self.recommendations.append(RecommendationQuality(
                gap_id=gap.gap_id,
                expected_recommendation_themes=recommendation_themes,
                expected_minimum_rating=4,
                reference_recommendation=reference_recommendation
            ))
        
        return gap
    
    def generate_synthetic_claims(self):
        """Generate synthetic claims for testing - creates 50+ claims."""
        
        # ===== PILLAR 1: BIOLOGICAL STIMULUS-RESPONSE =====
        # Strong evidence claims (approved)
        pillar1_strong = [
            {
                "claim_text": "The spiking neural network achieved 95.2% ± 0.3% accuracy on MNIST classification across 10 independent trials.",
                "evidence_text": "Table 3 shows classification accuracy with standard deviation. All trials used identical initialization and training parameters.",
                "requirement": "REQ-B1.1", "sub_requirement": "Sub-1.1.1",
                "strength": 5, "rigor": 4, "relevance": 5, "directness": 3, "reproducibility": 4
            },
            {
                "claim_text": "STDP learning rule produces synaptic potentiation with timing windows of ±20ms, matching biological measurements.",
                "evidence_text": "Figure 5A-C: Synaptic weight changes plotted against spike timing. Comparison with Bi & Poo (1998) data shows r=0.94 correlation.",
                "requirement": "REQ-B1.4", "sub_requirement": "Sub-1.4.2",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 4
            },
            {
                "claim_text": "Sensory encoding via population coding achieved 98% fidelity for natural images.",
                "evidence_text": "Figure 7 demonstrates population coding accuracy with n=500 neurons. Information theoretic analysis confirms 98.2% mutual information preservation.",
                "requirement": "REQ-B1.1", "sub_requirement": "Sub-1.1.3",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 5
            },
            {
                "claim_text": "Thalamic relay model reproduces <5ms latency for sensory signal propagation matching in vivo recordings.",
                "evidence_text": "Electrophysiology data in Table 2 shows mean latency of 4.2ms ± 0.3ms (n=50 trials), consistent with rodent thalamic recordings.",
                "requirement": "REQ-B1.2", "sub_requirement": "Sub-1.2.1",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 4
            },
            {
                "claim_text": "Evidence accumulation model achieves 89% accuracy on two-alternative forced choice with biologically plausible time constants.",
                "evidence_text": "Behavioral experiments (n=24 subjects) validated against drift-diffusion model predictions. R² = 0.91 for reaction time distributions.",
                "requirement": "REQ-B1.3", "sub_requirement": "Sub-1.3.1",
                "strength": 4, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 4
            },
            {
                "claim_text": "Multi-sensory integration in parietal cortex model shows 15% improvement in localization accuracy.",
                "evidence_text": "Cross-modal binding experiments demonstrate statistically significant improvement (p<0.001, paired t-test, n=30).",
                "requirement": "REQ-B1.2", "sub_requirement": "Sub-1.2.2",
                "strength": 4, "rigor": 4, "relevance": 5, "directness": 3, "reproducibility": 4
            },
            {
                "claim_text": "Short-term synaptic facilitation with τ=200ms matches paired-pulse ratios in hippocampal slices.",
                "evidence_text": "Figure 3: PPR of 1.8 ± 0.15 at 50ms ISI, validated against Zucker & Regehr (2002) reference data.",
                "requirement": "REQ-B1.4", "sub_requirement": "Sub-1.4.1",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 5
            },
            {
                "claim_text": "Long-term structural plasticity shows 23% increase in spine density after 7 days of enriched stimulation.",
                "evidence_text": "Two-photon imaging (n=6 mice): Spine count 45.2 ± 3.1 vs 36.7 ± 2.8 baseline (p<0.01).",
                "requirement": "REQ-B1.4", "sub_requirement": "Sub-1.4.3",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 4
            },
            {
                "claim_text": "Prefrontal top-down gating reduces irrelevant sensory responses by 40%.",
                "evidence_text": "Single-unit recordings (n=89 neurons) show 40% ± 8% reduction in non-attended stimulus responses.",
                "requirement": "REQ-B1.2", "sub_requirement": "Sub-1.2.3",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 4
            }
        ]
        
        # Weak evidence claims (rejected)
        pillar1_weak = [
            {
                "claim_text": "Neuromorphic systems are more efficient than traditional computing.",
                "evidence_text": "As is commonly known in the field, neuromorphic approaches offer inherent efficiency advantages.",
                "requirement": "REQ-B1.1", "sub_requirement": "Sub-1.1.1",
                "strength": 1, "rigor": 1, "relevance": 3, "directness": 1, "reproducibility": 1
            },
            {
                "claim_text": "The network learns patterns efficiently.",
                "evidence_text": "Similar to [45], our approach uses efficient learning mechanisms.",
                "requirement": "REQ-B1.4", "sub_requirement": "Sub-1.4.1",
                "strength": 1, "rigor": 1, "relevance": 2, "directness": 1, "reproducibility": 1
            },
            {
                "claim_text": "Our sensory model could potentially match biological performance.",
                "evidence_text": "Preliminary simulations suggest the architecture may achieve good results.",
                "requirement": "REQ-B1.1", "sub_requirement": "Sub-1.1.2",
                "strength": 1, "rigor": 1, "relevance": 3, "directness": 1, "reproducibility": 1
            },
            {
                "claim_text": "The neural pathway appears to function correctly.",
                "evidence_text": "Visual inspection of the output confirms expected behavior patterns.",
                "requirement": "REQ-B1.2", "sub_requirement": "Sub-1.2.1",
                "strength": 1, "rigor": 1, "relevance": 2, "directness": 1, "reproducibility": 1
            },
            {
                "claim_text": "Decision-making is improved with our approach.",
                "evidence_text": "Informal testing showed promising results that warrant further investigation.",
                "requirement": "REQ-B1.3", "sub_requirement": "Sub-1.3.1",
                "strength": 1, "rigor": 1, "relevance": 3, "directness": 1, "reproducibility": 1
            },
            {
                "claim_text": "Temporal dynamics are preserved in our encoding scheme.",
                "evidence_text": "We believe the spike timing captures essential temporal features.",
                "requirement": "REQ-B1.1", "sub_requirement": "Sub-1.1.4",
                "strength": 1, "rigor": 1, "relevance": 3, "directness": 1, "reproducibility": 1
            },
            {
                "claim_text": "Top-down attention modulates sensory processing.",
                "evidence_text": "This finding is consistent with established neuroscience literature.",
                "requirement": "REQ-B1.2", "sub_requirement": "Sub-1.2.3",
                "strength": 1, "rigor": 1, "relevance": 2, "directness": 1, "reproducibility": 1
            }
        ]
        
        # Borderline claims
        pillar1_borderline = [
            {
                "claim_text": "Initial tests show 82% classification accuracy on the DVS gesture dataset.",
                "evidence_text": "Pilot study (n=3) achieved 82% accuracy. Further validation ongoing.",
                "requirement": "REQ-B1.1", "sub_requirement": "Sub-1.1.2",
                "strength": 3, "rigor": 2, "relevance": 4, "directness": 2, "reproducibility": 2
            },
            {
                "claim_text": "Synaptic plasticity shows expected STDP curves in our simulations.",
                "evidence_text": "Figure 2 shows weight changes, though statistical analysis pending.",
                "requirement": "REQ-B1.4", "sub_requirement": "Sub-1.4.2",
                "strength": 3, "rigor": 2, "relevance": 4, "directness": 2, "reproducibility": 2
            },
            {
                "claim_text": "Basal ganglia model shows action selection improvement in 70% of trials.",
                "evidence_text": "Simulation results (n=10 runs) show improvement, but variance is high (SD=15%).",
                "requirement": "REQ-B1.3", "sub_requirement": "Sub-1.3.2",
                "strength": 3, "rigor": 2, "relevance": 4, "directness": 2, "reproducibility": 2
            }
        ]
        
        # ===== PILLAR 2: AI STIMULUS-RESPONSE =====
        pillar2_strong = [
            {
                "claim_text": "Power consumption measured at 1.2mW during inference, representing 10x reduction compared to GPU baseline.",
                "evidence_text": "Section 4.2: Power measurements using Keysight N6705C. Baseline GPU (RTX 3080) consumed 12W for equivalent task.",
                "requirement": "REQ-A2.4", "sub_requirement": "Sub-2.4.2",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 5
            },
            {
                "claim_text": "Event-based sensor achieves 120dB dynamic range with <1ms temporal resolution.",
                "evidence_text": "Characterization in Table 1: Dynamic range 123dB, median event latency 0.8ms, validated against DVS128 specifications.",
                "requirement": "REQ-A2.1", "sub_requirement": "Sub-2.1.1",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 5
            },
            {
                "claim_text": "Deep SNN with 8 layers trained via surrogate gradients achieves 94.1% on CIFAR-10.",
                "evidence_text": "Table 4: Test accuracy 94.1% ± 0.2% (5 runs), training with SuperSpike surrogate. Comparison to ANN baseline (94.8%).",
                "requirement": "REQ-A2.2", "sub_requirement": "Sub-2.2.1",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 5
            },
            {
                "claim_text": "SNN evidence accumulator matches DDM reaction time distributions (KL divergence < 0.05).",
                "evidence_text": "Figure 6: RT histograms for SNN vs DDM. Statistical analysis: KL=0.043, chi-square test p>0.1.",
                "requirement": "REQ-A2.3", "sub_requirement": "Sub-2.3.1",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 4
            },
            {
                "claim_text": "Sparse coding efficiency: average 7.2% neuron activation during inference.",
                "evidence_text": "Activation statistics over 10,000 samples: mean=7.2%, std=1.1%, max=12.3%. Threshold set at 0.5.",
                "requirement": "REQ-A2.4", "sub_requirement": "Sub-2.4.1",
                "strength": 5, "rigor": 4, "relevance": 5, "directness": 3, "reproducibility": 5
            },
            {
                "claim_text": "SNN attention mechanism reduces classification errors by 23% on cluttered backgrounds.",
                "evidence_text": "Table 5: Error rate 12.3% vs 16.0% baseline (p<0.01, McNemar test). Attention maps visualized in Figure 8.",
                "requirement": "REQ-A2.2", "sub_requirement": "Sub-2.2.3",
                "strength": 4, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 4
            },
            {
                "claim_text": "Hardware deployment on Loihi 2 achieves 15x energy efficiency over GPU with matching accuracy.",
                "evidence_text": "Table 7: Loihi 2 at 0.8mJ/inference vs GPU at 12mJ/inference. Accuracy within 0.5% (93.6% vs 94.1%).",
                "requirement": "REQ-A2.1", "sub_requirement": "Sub-2.1.3",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 5
            },
            {
                "claim_text": "Adaptive event thresholding reduces bandwidth by 40% with <1% accuracy loss.",
                "evidence_text": "Bandwidth analysis: 2.1MB/s baseline reduced to 1.26MB/s. Classification accuracy 93.1% vs 93.8%.",
                "requirement": "REQ-A2.1", "sub_requirement": "Sub-2.1.4",
                "strength": 5, "rigor": 4, "relevance": 5, "directness": 3, "reproducibility": 4
            }
        ]
        
        pillar2_weak = [
            {
                "claim_text": "Our SNN architecture is energy efficient.",
                "evidence_text": "The event-driven nature inherently provides efficiency benefits.",
                "requirement": "REQ-A2.4", "sub_requirement": "Sub-2.4.2",
                "strength": 1, "rigor": 1, "relevance": 3, "directness": 1, "reproducibility": 1
            },
            {
                "claim_text": "The neuromorphic chip should work well for this task.",
                "evidence_text": "Based on the specifications, we expect good performance.",
                "requirement": "REQ-A2.1", "sub_requirement": "Sub-2.1.3",
                "strength": 1, "rigor": 1, "relevance": 2, "directness": 1, "reproducibility": 1
            },
            {
                "claim_text": "Deep SNNs can achieve competitive accuracy.",
                "evidence_text": "Recent literature suggests SNNs are approaching ANN performance.",
                "requirement": "REQ-A2.2", "sub_requirement": "Sub-2.2.1",
                "strength": 1, "rigor": 1, "relevance": 3, "directness": 1, "reproducibility": 1
            },
            {
                "claim_text": "Action selection works as intended.",
                "evidence_text": "The agent successfully completes tasks in most cases.",
                "requirement": "REQ-A2.3", "sub_requirement": "Sub-2.3.2",
                "strength": 1, "rigor": 1, "relevance": 3, "directness": 1, "reproducibility": 1
            },
            {
                "claim_text": "Sparse activation is achieved in our network.",
                "evidence_text": "The network uses fewer spikes than fully connected alternatives.",
                "requirement": "REQ-A2.4", "sub_requirement": "Sub-2.4.1",
                "strength": 1, "rigor": 1, "relevance": 3, "directness": 1, "reproducibility": 1
            },
            {
                "claim_text": "Dynamic voltage scaling improves efficiency.",
                "evidence_text": "We applied standard DVFS techniques to the neuromorphic processor.",
                "requirement": "REQ-A2.4", "sub_requirement": "Sub-2.4.4",
                "strength": 1, "rigor": 1, "relevance": 3, "directness": 1, "reproducibility": 1
            },
            {
                "claim_text": "The SNN controller responds appropriately to inputs.",
                "evidence_text": "Manual testing confirmed correct behavior in tested scenarios.",
                "requirement": "REQ-A2.3", "sub_requirement": "Sub-2.3.3",
                "strength": 1, "rigor": 1, "relevance": 3, "directness": 1, "reproducibility": 1
            }
        ]
        
        pillar2_borderline = [
            {
                "claim_text": "The chip demonstrates sub-millisecond latency for pattern recognition.",
                "evidence_text": "Measured latency of 0.8ms ± 0.2ms across test patterns (methodology in supplementary).",
                "requirement": "REQ-A2.1", "sub_requirement": "Sub-2.1.1",
                "strength": 3, "rigor": 3, "relevance": 4, "directness": 2, "reproducibility": 3
            },
            {
                "claim_text": "Homeostatic plasticity maintains stable firing rates after perturbation.",
                "evidence_text": "Preliminary data shows recovery within 100 iterations, but n=2 networks tested.",
                "requirement": "REQ-A2.2", "sub_requirement": "Sub-2.2.4",
                "strength": 3, "rigor": 2, "relevance": 4, "directness": 2, "reproducibility": 2
            },
            {
                "claim_text": "Energy-accuracy trade-off shows 2x efficiency improvement at 95% accuracy.",
                "evidence_text": "Pareto analysis (Figure 5) with 5 operating points. Limited to single benchmark.",
                "requirement": "REQ-A2.4", "sub_requirement": "Sub-2.4.3",
                "strength": 3, "rigor": 3, "relevance": 4, "directness": 2, "reproducibility": 2
            }
        ]
        
        # ===== PILLAR 3: BIOLOGICAL SKILL AUTOMATIZATION =====
        pillar3_strong = [
            {
                "claim_text": "Hippocampal-PFC coupling decreases by 45% during motor skill consolidation.",
                "evidence_text": "fMRI coherence analysis (n=18) shows significant decrease from day 1 to day 7 (p<0.001, corrected).",
                "requirement": "REQ-B3.1", "sub_requirement": "Sub-3.1.1",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 4
            },
            {
                "claim_text": "Striatal activity increases by 60% during automatized skill execution.",
                "evidence_text": "PET imaging (n=12) shows significant striatal activation increase post-training (p<0.005).",
                "requirement": "REQ-B3.2", "sub_requirement": "Sub-3.2.2",
                "strength": 5, "rigor": 4, "relevance": 5, "directness": 3, "reproducibility": 4
            },
            {
                "claim_text": "Sleep spindle density correlates with motor learning consolidation (r=0.78).",
                "evidence_text": "EEG analysis (n=30) during post-training sleep. Spindle density predicts next-day performance.",
                "requirement": "REQ-B3.2", "sub_requirement": "Sub-3.2.3",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 5
            },
            {
                "claim_text": "Expert performers show 73% reduction in prefrontal activation during automatized tasks.",
                "evidence_text": "fMRI comparison of experts vs novices (n=20 each). BOLD signal analysis with FDR correction.",
                "requirement": "REQ-B3.3", "sub_requirement": "Sub-3.3.3",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 4
            },
            {
                "claim_text": "Dopaminergic reward signals strengthen skill consolidation with effect size d=1.2.",
                "evidence_text": "Pharmacological study (n=40): L-DOPA group shows 35% better retention vs placebo (p<0.001).",
                "requirement": "REQ-B3.2", "sub_requirement": "Sub-3.2.4",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 4
            },
            {
                "claim_text": "Cerebellar error correction reduces movement variability by 55% over 100 trials.",
                "evidence_text": "Kinematic analysis: CV decreased from 0.45 to 0.20 (n=25 subjects, p<0.001).",
                "requirement": "REQ-B3.4", "sub_requirement": "Sub-3.4.3",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 5
            }
        ]
        
        pillar3_weak = [
            {
                "claim_text": "Skills become automatic with practice.",
                "evidence_text": "This is a well-established finding in motor learning literature.",
                "requirement": "REQ-B3.3", "sub_requirement": "Sub-3.3.1",
                "strength": 1, "rigor": 1, "relevance": 2, "directness": 1, "reproducibility": 1
            },
            {
                "claim_text": "The cerebellum is involved in motor learning.",
                "evidence_text": "Standard textbooks describe cerebellar involvement in motor adaptation.",
                "requirement": "REQ-B3.4", "sub_requirement": "Sub-3.4.3",
                "strength": 1, "rigor": 1, "relevance": 2, "directness": 1, "reproducibility": 1
            },
            {
                "claim_text": "Our model might capture skill automatization.",
                "evidence_text": "Initial observations suggest possible learning effects.",
                "requirement": "REQ-B3.2", "sub_requirement": "Sub-3.2.1",
                "strength": 1, "rigor": 1, "relevance": 3, "directness": 1, "reproducibility": 1
            },
            {
                "claim_text": "Practice improves performance.",
                "evidence_text": "As expected, repeated practice led to better outcomes.",
                "requirement": "REQ-B3.3", "sub_requirement": "Sub-3.3.2",
                "strength": 1, "rigor": 1, "relevance": 2, "directness": 1, "reproducibility": 1
            }
        ]
        
        pillar3_borderline = [
            {
                "claim_text": "Procedural consolidation shows expected time course in our paradigm.",
                "evidence_text": "Learning curve analysis (n=8) shows improvement over 3 sessions, though variability high.",
                "requirement": "REQ-B3.2", "sub_requirement": "Sub-3.2.1",
                "strength": 3, "rigor": 3, "relevance": 4, "directness": 2, "reproducibility": 2
            },
            {
                "claim_text": "Dual-task interference reduces by 35% after 5 days of training.",
                "evidence_text": "Behavioral study (n=12) shows reduced interference. Single task paradigm tested.",
                "requirement": "REQ-B3.3", "sub_requirement": "Sub-3.3.1",
                "strength": 3, "rigor": 3, "relevance": 4, "directness": 2, "reproducibility": 2
            }
        ]
        
        # ===== PILLAR 4: AI SKILL AUTOMATIZATION =====
        pillar4_strong = [
            {
                "claim_text": "Policy distillation achieves 95% performance retention with 10x inference speedup.",
                "evidence_text": "Table 6: Distilled policy achieves 285 ± 12 (teacher: 300 ± 8) on Atari Breakout with 10x faster inference.",
                "requirement": "REQ-A4.2", "sub_requirement": "Sub-4.2.1",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 5
            },
            {
                "claim_text": "Hierarchical RL discovers 7 reusable subskills across 5 Atari games.",
                "evidence_text": "Skill analysis (Section 5.2): 7 skills with >80% reuse rate. Transfer learning shows 3x faster learning.",
                "requirement": "REQ-A4.2", "sub_requirement": "Sub-4.2.2",
                "strength": 5, "rigor": 4, "relevance": 5, "directness": 3, "reproducibility": 4
            },
            {
                "claim_text": "Offline optimization improves policy performance by 18% without additional environment interaction.",
                "evidence_text": "CQL training on 1M offline transitions. Test performance: 412 vs 350 baseline (5 seeds each).",
                "requirement": "REQ-A4.2", "sub_requirement": "Sub-4.2.3",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 5
            },
            {
                "claim_text": "Transfer efficiency of 62% achieved on related manipulation tasks.",
                "evidence_text": "Transfer from pushing to lifting: 62% sample efficiency improvement vs learning from scratch (Figure 9).",
                "requirement": "REQ-A4.5", "sub_requirement": "Sub-4.5.1",
                "strength": 4, "rigor": 4, "relevance": 5, "directness": 3, "reproducibility": 4
            },
            {
                "claim_text": "World model enables 5x sample efficiency improvement in exploration phase.",
                "evidence_text": "Table 8: Model-based approach reaches threshold in 200K steps vs 1M for model-free (5 seeds).",
                "requirement": "REQ-A4.1", "sub_requirement": "Sub-4.1.1",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 5
            },
            {
                "claim_text": "Compiled policy inference cost reduced by 92% vs exploration-phase network.",
                "evidence_text": "Profiling results: 0.8ms vs 10ms per decision. FLOPs reduced from 1.2G to 95M.",
                "requirement": "REQ-A4.3", "sub_requirement": "Sub-4.3.1",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 5
            },
            {
                "claim_text": "Compositional skill combination achieves 80% success on novel 3-skill sequences.",
                "evidence_text": "Table 11: 80% ± 5% success on held-out combinations (n=50). Comparison to 65% random baseline.",
                "requirement": "REQ-A4.5", "sub_requirement": "Sub-4.5.4",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 4
            },
            {
                "claim_text": "Adaptive learning rate based on performance improves convergence by 40%.",
                "evidence_text": "Training curves (10 seeds): Adaptive LR converges in 600K steps vs 1M baseline.",
                "requirement": "REQ-A4.4", "sub_requirement": "Sub-4.4.4",
                "strength": 5, "rigor": 4, "relevance": 5, "directness": 3, "reproducibility": 5
            }
        ]
        
        pillar4_weak = [
            {
                "claim_text": "Reinforcement learning can automate skills.",
                "evidence_text": "RL is widely used for learning sequential decision-making tasks.",
                "requirement": "REQ-A4.1", "sub_requirement": "Sub-4.1.1",
                "strength": 1, "rigor": 1, "relevance": 2, "directness": 1, "reproducibility": 1
            },
            {
                "claim_text": "Our agent learns to complete the task.",
                "evidence_text": "After training, the agent successfully reaches the goal state.",
                "requirement": "REQ-A4.3", "sub_requirement": "Sub-4.3.1",
                "strength": 1, "rigor": 1, "relevance": 3, "directness": 1, "reproducibility": 1
            },
            {
                "claim_text": "Transfer learning helps with new tasks.",
                "evidence_text": "Pre-training on related tasks appears beneficial.",
                "requirement": "REQ-A4.5", "sub_requirement": "Sub-4.5.1",
                "strength": 1, "rigor": 1, "relevance": 3, "directness": 1, "reproducibility": 1
            },
            {
                "claim_text": "The policy generalizes to new situations.",
                "evidence_text": "Anecdotal evidence suggests reasonable generalization.",
                "requirement": "REQ-A4.5", "sub_requirement": "Sub-4.5.2",
                "strength": 1, "rigor": 1, "relevance": 3, "directness": 1, "reproducibility": 1
            }
        ]
        
        pillar4_borderline = [
            {
                "claim_text": "Model-free policy shows 85% success rate after 1M steps.",
                "evidence_text": "Training curve in Figure 4 shows convergence. Single seed reported.",
                "requirement": "REQ-A4.2", "sub_requirement": "Sub-4.2.1",
                "strength": 3, "rigor": 2, "relevance": 4, "directness": 2, "reproducibility": 2
            },
            {
                "claim_text": "Error signal backpropagation latency measured at 5ms in hardware.",
                "evidence_text": "Timing analysis shows 5.2ms ± 0.8ms, but only 2 chips tested.",
                "requirement": "REQ-A4.4", "sub_requirement": "Sub-4.4.1",
                "strength": 3, "rigor": 2, "relevance": 4, "directness": 2, "reproducibility": 2
            }
        ]
        
        # ===== PILLAR 5: BIOLOGICAL MEMORY SYSTEMS =====
        pillar5_strong = [
            {
                "claim_text": "Hippocampal sharp-wave ripples during sleep replay behavioral sequences with 78% fidelity.",
                "evidence_text": "Multi-electrode recordings (n=4 rats) during sleep. Bayesian decoding shows 78% ± 5% reconstruction accuracy.",
                "requirement": "REQ-B5.1", "sub_requirement": "Sub-5.1.1",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 4
            },
            {
                "claim_text": "Pattern completion in CA3 achieves 92% accuracy with 30% partial cues.",
                "evidence_text": "Computational model validated against rodent data. 92% completion accuracy (n=100 patterns).",
                "requirement": "REQ-B5.2", "sub_requirement": "Sub-5.2.1",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 5
            },
            {
                "claim_text": "LTP induction follows BCM-like threshold dynamics with sliding modification threshold.",
                "evidence_text": "Slice electrophysiology (n=24 slices) confirms BCM rule. Threshold shift observed after high-frequency stimulation.",
                "requirement": "REQ-B5.1", "sub_requirement": "Sub-5.1.2",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 5
            },
            {
                "claim_text": "Amygdala lesions reduce emotional memory enhancement by 65%.",
                "evidence_text": "Patient study (n=12 amygdala patients vs n=24 controls). Recognition memory for emotional items significantly impaired.",
                "requirement": "REQ-B5.2", "sub_requirement": "Sub-5.2.2",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 4
            },
            {
                "claim_text": "Theta-gamma coupling strength predicts memory encoding success (r=0.72).",
                "evidence_text": "Intracranial EEG (n=15 epilepsy patients) during encoding. Coupling strength correlates with subsequent recall.",
                "requirement": "REQ-B5.1", "sub_requirement": "Sub-5.1.4",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 4
            },
            {
                "claim_text": "Place cell remapping occurs within 2 minutes of environmental change.",
                "evidence_text": "Single-unit recordings (n=120 cells, 8 rats). 85% of cells show significant remapping by trial 3.",
                "requirement": "REQ-B5.1", "sub_requirement": "Sub-5.1.3",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 5
            }
        ]
        
        pillar5_weak = [
            {
                "claim_text": "Our architecture may improve memory consolidation.",
                "evidence_text": "Preliminary observations suggest possible improvements in retention, though more testing is needed.",
                "requirement": "REQ-B5.1", "sub_requirement": "Sub-5.1.1",
                "strength": 1, "rigor": 2, "relevance": 3, "directness": 1, "reproducibility": 1
            },
            {
                "claim_text": "Memory retrieval works in our model.",
                "evidence_text": "The network successfully retrieves stored patterns.",
                "requirement": "REQ-B5.2", "sub_requirement": "Sub-5.2.1",
                "strength": 1, "rigor": 1, "relevance": 3, "directness": 1, "reproducibility": 1
            },
            {
                "claim_text": "Hippocampus is important for memory.",
                "evidence_text": "Classic lesion studies demonstrate hippocampal involvement in memory formation.",
                "requirement": "REQ-B5.1", "sub_requirement": "Sub-5.1.1",
                "strength": 1, "rigor": 1, "relevance": 2, "directness": 1, "reproducibility": 1
            },
            {
                "claim_text": "Working memory capacity is limited.",
                "evidence_text": "Miller's classic finding of 7±2 items is well known.",
                "requirement": "REQ-B5.3", "sub_requirement": "Sub-5.3.1",
                "strength": 1, "rigor": 1, "relevance": 2, "directness": 1, "reproducibility": 1
            }
        ]
        
        pillar5_borderline = [
            {
                "claim_text": "Working memory capacity of 6±1 items observed in our behavioral paradigm.",
                "evidence_text": "Behavioral study (n=15) using change detection. Capacity estimate via Cowan K formula.",
                "requirement": "REQ-B5.3", "sub_requirement": "Sub-5.3.1",
                "strength": 3, "rigor": 3, "relevance": 4, "directness": 2, "reproducibility": 3
            },
            {
                "claim_text": "Memory reconsolidation window shows 6-hour vulnerability period.",
                "evidence_text": "Behavioral study (n=20) shows memory modification possible within 6 hours of reactivation.",
                "requirement": "REQ-B5.2", "sub_requirement": "Sub-5.2.3",
                "strength": 3, "rigor": 3, "relevance": 4, "directness": 2, "reproducibility": 2
            }
        ]
        
        # ===== PILLAR 6: AI MEMORY SYSTEMS =====
        pillar6_strong = [
            {
                "claim_text": "Continual learning system retains 94% accuracy on previous tasks after learning 50 sequential tasks.",
                "evidence_text": "Split-MNIST benchmark: Final accuracy 94.2% ± 0.8% (5 seeds). Comparison: EWC 89%, SI 91%.",
                "requirement": "REQ-A6.1", "sub_requirement": "Sub-6.1.1",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 5
            },
            {
                "claim_text": "Memory-augmented network achieves 98% accuracy on one-shot Omniglot classification.",
                "evidence_text": "5-way 1-shot accuracy: 98.2% ± 0.3%. 20-way 1-shot: 93.8% ± 0.4% (Table 3).",
                "requirement": "REQ-A6.2", "sub_requirement": "Sub-6.2.1",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 5
            },
            {
                "claim_text": "Hebbian-inspired local learning rule achieves 87% accuracy on MNIST without backpropagation.",
                "evidence_text": "Section 4.1: Local learning achieves 87.3% vs 98% backprop baseline. Energy efficiency 5x better.",
                "requirement": "REQ-A6.1", "sub_requirement": "Sub-6.1.2",
                "strength": 5, "rigor": 4, "relevance": 5, "directness": 3, "reproducibility": 5
            },
            {
                "claim_text": "Episodic memory retrieval latency under 0.5ms for 100K stored episodes.",
                "evidence_text": "Benchmarking with LSH indexing: mean retrieval 0.42ms, 99th percentile 0.89ms (Figure 7).",
                "requirement": "REQ-A6.4", "sub_requirement": "Sub-6.4.3",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 5
            },
            {
                "claim_text": "Memory compression achieves 150:1 ratio while retaining 95% task performance.",
                "evidence_text": "Table 9: Compressed memory uses 0.67% of original size. Performance: 94.8% vs 99.2% uncompressed.",
                "requirement": "REQ-A6.1", "sub_requirement": "Sub-6.1.4",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 5
            },
            {
                "claim_text": "Similarity-based generalization improves novel class accuracy by 28%.",
                "evidence_text": "Zero-shot evaluation: 67% vs 52% baseline (p<0.001, n=1000 test cases).",
                "requirement": "REQ-A6.2", "sub_requirement": "Sub-6.2.4",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 5
            }
        ]
        
        pillar6_weak = [
            {
                "claim_text": "Our memory network can store and retrieve patterns.",
                "evidence_text": "Basic functionality tests show the network operates as expected.",
                "requirement": "REQ-A6.2", "sub_requirement": "Sub-6.2.1",
                "strength": 1, "rigor": 1, "relevance": 3, "directness": 1, "reproducibility": 1
            },
            {
                "claim_text": "Catastrophic forgetting is reduced in our approach.",
                "evidence_text": "Informal experiments suggest better retention than naive fine-tuning.",
                "requirement": "REQ-A6.1", "sub_requirement": "Sub-6.1.1",
                "strength": 1, "rigor": 1, "relevance": 3, "directness": 1, "reproducibility": 1
            },
            {
                "claim_text": "Memory capacity scales well with network size.",
                "evidence_text": "Larger networks store more patterns, as expected.",
                "requirement": "REQ-A6.4", "sub_requirement": "Sub-6.4.1",
                "strength": 1, "rigor": 1, "relevance": 3, "directness": 1, "reproducibility": 1
            }
        ]
        
        pillar6_borderline = [
            {
                "claim_text": "Context-dependent retrieval shows 80% accuracy in our preliminary tests.",
                "evidence_text": "Small-scale experiment (n=3 runs) shows context improves retrieval. Larger study planned.",
                "requirement": "REQ-A6.1", "sub_requirement": "Sub-6.1.3",
                "strength": 3, "rigor": 2, "relevance": 4, "directness": 2, "reproducibility": 2
            },
            {
                "claim_text": "Working memory integration with SNN shows 75% task accuracy.",
                "evidence_text": "Preliminary integration test (n=5 seeds) achieves 75% ± 8% on delayed match-to-sample.",
                "requirement": "REQ-A6.3", "sub_requirement": "Sub-6.3.1",
                "strength": 3, "rigor": 2, "relevance": 4, "directness": 2, "reproducibility": 2
            }
        ]
        
        # ===== PILLAR 7: SYSTEM INTEGRATION =====
        pillar7_strong = [
            {
                "claim_text": "Cross-pillar latency averages 0.3ms for priority signals with 99.9% delivery rate.",
                "evidence_text": "System benchmarks (100K messages): mean latency 0.31ms, max 0.89ms. Packet loss <0.1%.",
                "requirement": "REQ-7.1", "sub_requirement": "Sub-7.1.3",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 5
            },
            {
                "claim_text": "Integrated system shows emergent generalization to novel task combinations.",
                "evidence_text": "Table 8: 73% success rate on held-out task combinations (n=50 novel combinations, 10 trials each).",
                "requirement": "REQ-7.4", "sub_requirement": "Sub-7.4.2",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 4
            },
            {
                "claim_text": "System maintains 82% performance with single pillar degradation.",
                "evidence_text": "Ablation studies (Section 6.3): Performance drop ranges 12-25% depending on pillar removed.",
                "requirement": "REQ-7.4", "sub_requirement": "Sub-7.4.4",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 5
            },
            {
                "claim_text": "Spike-based communication protocol achieves 95% bandwidth efficiency vs baseline.",
                "evidence_text": "Table 10: Average 2.1 spikes/neuron/timestep vs 20 bits baseline. Semantic information preserved.",
                "requirement": "REQ-7.1", "sub_requirement": "Sub-7.1.1",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 5
            },
            {
                "claim_text": "Multi-timescale integration framework enables 5 concurrent temporal processes.",
                "evidence_text": "Timing analysis: processes at 1ms, 10ms, 100ms, 1s, and 10s successfully integrated.",
                "requirement": "REQ-7.2", "sub_requirement": "Sub-7.2.2",
                "strength": 5, "rigor": 4, "relevance": 5, "directness": 3, "reproducibility": 5
            },
            {
                "claim_text": "Hierarchical control reduces conflict resolution time by 67%.",
                "evidence_text": "Response time: 45ms vs 135ms flat architecture (n=1000 conflicts, p<0.001).",
                "requirement": "REQ-7.3", "sub_requirement": "Sub-7.3.1",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 5
            },
            {
                "claim_text": "Staged pillar activation achieves 25% faster system maturation.",
                "evidence_text": "Development time: 4.5 hours vs 6 hours simultaneous activation (10 runs each).",
                "requirement": "REQ-7.5", "sub_requirement": "Sub-7.5.1",
                "strength": 5, "rigor": 4, "relevance": 5, "directness": 3, "reproducibility": 5
            },
            {
                "claim_text": "Curriculum learning sequence optimizes inter-pillar connectivity development.",
                "evidence_text": "Final system performance 87% vs 78% random curriculum (p<0.01, n=15 systems).",
                "requirement": "REQ-7.5", "sub_requirement": "Sub-7.5.2",
                "strength": 5, "rigor": 4, "relevance": 5, "directness": 3, "reproducibility": 4
            },
            {
                "claim_text": "Novel situation adaptation succeeds in 68% of unseen scenarios.",
                "evidence_text": "Table 12: 68% ± 7% success on 100 novel scenarios not in training distribution.",
                "requirement": "REQ-7.4", "sub_requirement": "Sub-7.4.3",
                "strength": 5, "rigor": 5, "relevance": 5, "directness": 3, "reproducibility": 4
            }
        ]
        
        pillar7_weak = [
            {
                "claim_text": "The modules work together.",
                "evidence_text": "End-to-end testing confirms basic functionality.",
                "requirement": "REQ-7.1", "sub_requirement": "Sub-7.1.1",
                "strength": 1, "rigor": 1, "relevance": 3, "directness": 1, "reproducibility": 1
            },
            {
                "claim_text": "Integration overhead is acceptable.",
                "evidence_text": "The system runs at interactive speeds.",
                "requirement": "REQ-7.1", "sub_requirement": "Sub-7.1.2",
                "strength": 1, "rigor": 1, "relevance": 3, "directness": 1, "reproducibility": 1
            },
            {
                "claim_text": "The system shows emergent behavior.",
                "evidence_text": "Complex patterns emerge from component interactions.",
                "requirement": "REQ-7.4", "sub_requirement": "Sub-7.4.1",
                "strength": 1, "rigor": 1, "relevance": 3, "directness": 1, "reproducibility": 1
            }
        ]
        
        pillar7_borderline = [
            {
                "claim_text": "Phase-locking between oscillatory components achieves coherence of 0.7.",
                "evidence_text": "Coherence analysis shows mean 0.7 ± 0.15 (n=5 runs). Threshold for significance not yet established.",
                "requirement": "REQ-7.2", "sub_requirement": "Sub-7.2.4",
                "strength": 3, "rigor": 3, "relevance": 4, "directness": 2, "reproducibility": 3
            },
            {
                "claim_text": "Resource allocation algorithm reduces contention by 50%.",
                "evidence_text": "Simulation (n=10 runs) shows 50% ± 12% reduction in resource conflicts.",
                "requirement": "REQ-7.3", "sub_requirement": "Sub-7.3.3",
                "strength": 3, "rigor": 2, "relevance": 4, "directness": 2, "reproducibility": 2
            }
        ]
        
        # Now add all claims
        pillar_mapping = {
            1: "Pillar 1: Biological Stimulus-Response",
            2: "Pillar 2: AI Stimulus-Response (Bridge)",
            3: "Pillar 3: Biological Skill Automatization",
            4: "Pillar 4: AI Skill Automatization (Bridge)",
            5: "Pillar 5: Biological Memory Systems",
            6: "Pillar 6: AI Memory Systems (Bridge)",
            7: "Pillar 7: System Integration & Orchestration"
        }
        
        all_claims = [
            (1, pillar1_strong, "approved", "Strong quantitative evidence meeting all criteria"),
            (1, pillar1_weak, "rejected", "Insufficient evidence - no quantitative data or methodology"),
            (1, pillar1_borderline, "borderline", "Mixed evidence quality near threshold"),
            (2, pillar2_strong, "approved", "Strong quantitative evidence meeting all criteria"),
            (2, pillar2_weak, "rejected", "Insufficient evidence - no quantitative data or methodology"),
            (2, pillar2_borderline, "borderline", "Mixed evidence quality near threshold"),
            (3, pillar3_strong, "approved", "Strong quantitative evidence meeting all criteria"),
            (3, pillar3_weak, "rejected", "Insufficient evidence - no quantitative data or methodology"),
            (3, pillar3_borderline, "borderline", "Mixed evidence quality near threshold"),
            (4, pillar4_strong, "approved", "Strong quantitative evidence meeting all criteria"),
            (4, pillar4_weak, "rejected", "Insufficient evidence - no quantitative data or methodology"),
            (4, pillar4_borderline, "borderline", "Mixed evidence quality near threshold"),
            (5, pillar5_strong, "approved", "Strong quantitative evidence meeting all criteria"),
            (5, pillar5_weak, "rejected", "Insufficient evidence - no quantitative data or methodology"),
            (5, pillar5_borderline, "borderline", "Mixed evidence quality near threshold"),
            (6, pillar6_strong, "approved", "Strong quantitative evidence meeting all criteria"),
            (6, pillar6_weak, "rejected", "Insufficient evidence - no quantitative data or methodology"),
            (6, pillar6_borderline, "borderline", "Mixed evidence quality near threshold"),
            (7, pillar7_strong, "approved", "Strong quantitative evidence meeting all criteria"),
            (7, pillar7_weak, "rejected", "Insufficient evidence - no quantitative data or methodology"),
            (7, pillar7_borderline, "borderline", "Mixed evidence quality near threshold"),
        ]
        
        for pillar_num, claims_list, verdict, verdict_rationale in all_claims:
            pillar_name = pillar_mapping[pillar_num]
            is_edge = verdict == "borderline"
            edge_type = "borderline_evidence" if is_edge else None
            confidence = "high" if verdict != "borderline" else "medium"
            
            if verdict == "approved":
                test_cats = ["precision", "judge_accuracy", "pillar_mapping"]
                map_rationale = "Directly addresses requirement with quantitative evidence"
                ev_rationale = "Clear methodology with statistical measures"
            elif verdict == "rejected":
                test_cats = ["recall", "false_approval_prevention"]
                map_rationale = "Topic matches but evidence is insufficient"
                ev_rationale = "Lacks methodology, data, or concrete claims"
            else:
                test_cats = ["calibration", "borderline"]
                map_rationale = "Relevant topic with mixed evidence quality"
                ev_rationale = "Some data present but methodology concerns"
            
            for i, claim_data in enumerate(claims_list):
                self.add_annotated_claim(
                    source_paper=f"synthetic_p{pillar_num}_{verdict}_{i+1}.pdf",
                    source_page=10 + i,
                    claim_text=claim_data["claim_text"],
                    evidence_text=claim_data["evidence_text"],
                    pillar=pillar_name,
                    requirement=claim_data["requirement"],
                    sub_requirement=claim_data["sub_requirement"],
                    mapping_rationale=map_rationale,
                    verdict=verdict,
                    verdict_rationale=verdict_rationale,
                    confidence=confidence,
                    strength=claim_data["strength"],
                    rigor=claim_data["rigor"],
                    relevance=claim_data["relevance"],
                    directness=claim_data["directness"],
                    reproducibility=claim_data["reproducibility"],
                    evidence_rationale=ev_rationale,
                    test_categories=test_cats,
                    is_edge_case=is_edge,
                    edge_case_type=edge_type
                )
    
    def generate_synthetic_gaps(self):
        """Generate synthetic gaps for testing - creates 20+ gaps."""
        
        gaps = [
            # Pillar 1 gaps
            {
                "pillar": "Pillar 1: Biological Stimulus-Response",
                "requirement_id": "REQ-B1.2",
                "sub_requirement_id": "Sub-1.2.4",
                "requirement_text": "Feedback connections from higher to lower processing areas",
                "completeness": 20.0,
                "severity": "HIGH",
                "why": "Limited papers address feedback connection dynamics in biological systems",
                "themes": ["feedback connections", "top-down modulation", "cortical hierarchy", "predictive coding"],
                "recommendation": "Search for papers on cortical feedback connections and predictive processing frameworks."
            },
            {
                "pillar": "Pillar 1: Biological Stimulus-Response",
                "requirement_id": "REQ-B1.3",
                "sub_requirement_id": "Sub-1.3.4",
                "requirement_text": "Inhibitory control mechanisms for action suppression",
                "completeness": 25.0,
                "severity": "HIGH",
                "why": "Few papers provide quantitative models of response inhibition circuits",
                "themes": ["inhibitory control", "response suppression", "stop-signal", "prefrontal cortex"],
                "recommendation": "Search for computational models of response inhibition and stop-signal paradigms."
            },
            # Pillar 2 gaps
            {
                "pillar": "Pillar 2: AI Stimulus-Response (Bridge)",
                "requirement_id": "REQ-A2.1",
                "sub_requirement_id": "Sub-2.1.4",
                "requirement_text": "Adaptive sampling based on information content",
                "completeness": 15.0,
                "severity": "CRITICAL",
                "why": "No papers address adaptive sampling in event-based neuromorphic systems",
                "themes": ["adaptive sampling", "information content", "event-based sensing", "attention"],
                "recommendation": "Search for papers on attention-guided event-based sensing and adaptive sampling strategies."
            },
            {
                "pillar": "Pillar 2: AI Stimulus-Response (Bridge)",
                "requirement_id": "REQ-A2.2",
                "sub_requirement_id": "Sub-2.2.2",
                "requirement_text": "SNN architecture for multi-sensory fusion",
                "completeness": 30.0,
                "severity": "HIGH",
                "why": "Limited work on multi-modal SNNs with neuromorphic sensors",
                "themes": ["multi-sensory fusion", "SNN", "cross-modal", "neuromorphic"],
                "recommendation": "Search for spiking neural network approaches to multi-sensory integration and fusion."
            },
            # Pillar 3 gaps
            {
                "pillar": "Pillar 3: Biological Skill Automatization",
                "requirement_id": "REQ-B3.1",
                "sub_requirement_id": "Sub-3.1.3",
                "requirement_text": "Working memory maintenance during skill acquisition",
                "completeness": 35.0,
                "severity": "MEDIUM",
                "why": "Gap between working memory and motor skill acquisition literature",
                "themes": ["working memory", "skill acquisition", "PFC", "motor learning"],
                "recommendation": "Search for papers linking working memory capacity to motor skill learning."
            },
            {
                "pillar": "Pillar 3: Biological Skill Automatization",
                "requirement_id": "REQ-B3.4",
                "sub_requirement_id": "Sub-3.4.2",
                "requirement_text": "Error-based learning signal propagation",
                "completeness": 40.0,
                "severity": "MEDIUM",
                "why": "Incomplete understanding of error signal routing in motor circuits",
                "themes": ["error signals", "motor learning", "cerebellum", "climbing fibers"],
                "recommendation": "Search for papers on cerebellar error signal propagation and motor adaptation."
            },
            # Pillar 4 gaps
            {
                "pillar": "Pillar 4: AI Skill Automatization (Bridge)",
                "requirement_id": "REQ-A4.1",
                "sub_requirement_id": "Sub-4.1.3",
                "requirement_text": "Uncertainty-guided exploration strategies",
                "completeness": 25.0,
                "severity": "HIGH",
                "why": "Limited neuromorphic implementations of uncertainty-guided exploration",
                "themes": ["uncertainty", "exploration", "Bayesian RL", "information gain"],
                "recommendation": "Search for uncertainty-driven exploration in neuromorphic reinforcement learning."
            },
            {
                "pillar": "Pillar 4: AI Skill Automatization (Bridge)",
                "requirement_id": "REQ-A4.2",
                "sub_requirement_id": "Sub-4.2.4",
                "requirement_text": "Progressive network pruning during consolidation",
                "completeness": 20.0,
                "severity": "HIGH",
                "why": "Few papers combine pruning with skill consolidation in SNNs",
                "themes": ["network pruning", "consolidation", "SNN", "efficiency"],
                "recommendation": "Search for progressive pruning methods for SNN skill consolidation."
            },
            {
                "pillar": "Pillar 4: AI Skill Automatization (Bridge)",
                "requirement_id": "REQ-A4.5",
                "sub_requirement_id": "Sub-4.5.4",
                "requirement_text": "Compositional skill combination",
                "completeness": 30.0,
                "severity": "HIGH",
                "why": "Limited work on compositional skill learning in neuromorphic systems",
                "themes": ["compositional learning", "skill combination", "hierarchical RL", "modularity"],
                "recommendation": "Search for compositional and hierarchical skill learning approaches."
            },
            # Pillar 5 gaps
            {
                "pillar": "Pillar 5: Biological Memory Systems",
                "requirement_id": "REQ-B5.2",
                "sub_requirement_id": "Sub-5.2.3",
                "requirement_text": "Memory reconsolidation model",
                "completeness": 35.0,
                "severity": "MEDIUM",
                "why": "Computational models of reconsolidation are incomplete",
                "themes": ["reconsolidation", "memory updating", "labilization", "restabilization"],
                "recommendation": "Search for computational models of memory reconsolidation and updating."
            },
            {
                "pillar": "Pillar 5: Biological Memory Systems",
                "requirement_id": "REQ-B5.2",
                "sub_requirement_id": "Sub-5.2.4",
                "requirement_text": "Interference resolution mechanisms",
                "completeness": 30.0,
                "severity": "HIGH",
                "why": "Limited understanding of how brain resolves memory interference",
                "themes": ["interference", "pattern separation", "hippocampus", "dentate gyrus"],
                "recommendation": "Search for papers on pattern separation and interference resolution in hippocampus."
            },
            {
                "pillar": "Pillar 5: Biological Memory Systems",
                "requirement_id": "REQ-B5.3",
                "sub_requirement_id": "Sub-5.3.2",
                "requirement_text": "Episodic-semantic memory interaction",
                "completeness": 25.0,
                "severity": "HIGH",
                "why": "Gap in understanding episodic-semantic memory system interactions",
                "themes": ["episodic memory", "semantic memory", "memory systems", "abstraction"],
                "recommendation": "Search for papers on episodic-semantic memory interactions and abstraction."
            },
            # Pillar 6 gaps
            {
                "pillar": "Pillar 6: AI Memory Systems (Bridge)",
                "requirement_id": "REQ-A6.2",
                "sub_requirement_id": "Sub-6.2.3",
                "requirement_text": "Memory editing/reconsolidation",
                "completeness": 15.0,
                "severity": "CRITICAL",
                "why": "Very few papers address memory editing in artificial systems",
                "themes": ["memory editing", "reconsolidation", "neural networks", "updating"],
                "recommendation": "Search for memory editing and updating mechanisms in neural networks."
            },
            {
                "pillar": "Pillar 6: AI Memory Systems (Bridge)",
                "requirement_id": "REQ-A6.3",
                "sub_requirement_id": "Sub-6.3.4",
                "requirement_text": "Memory-based planning and simulation",
                "completeness": 40.0,
                "severity": "MEDIUM",
                "why": "Limited integration of episodic memory with planning algorithms",
                "themes": ["planning", "simulation", "episodic memory", "model-based RL"],
                "recommendation": "Search for episodic memory integration with planning and imagination."
            },
            {
                "pillar": "Pillar 6: AI Memory Systems (Bridge)",
                "requirement_id": "REQ-A6.4",
                "sub_requirement_id": "Sub-6.4.2",
                "requirement_text": "Active forgetting of irrelevant information",
                "completeness": 20.0,
                "severity": "HIGH",
                "why": "Active forgetting mechanisms underexplored in AI memory systems",
                "themes": ["active forgetting", "memory management", "relevance", "pruning"],
                "recommendation": "Search for active forgetting and memory management in neural networks."
            },
            # Pillar 7 gaps
            {
                "pillar": "Pillar 7: System Integration & Orchestration",
                "requirement_id": "REQ-7.2",
                "sub_requirement_id": "Sub-7.2.3",
                "requirement_text": "Temporal credit assignment across modules",
                "completeness": 10.0,
                "severity": "CRITICAL",
                "why": "Major gap in cross-module temporal credit assignment",
                "themes": ["credit assignment", "temporal", "multi-module", "learning"],
                "recommendation": "Search for temporal credit assignment in modular neural systems."
            },
            {
                "pillar": "Pillar 7: System Integration & Orchestration",
                "requirement_id": "REQ-7.3",
                "sub_requirement_id": "Sub-7.3.2",
                "requirement_text": "Conflict resolution between competing objectives",
                "completeness": 25.0,
                "severity": "HIGH",
                "why": "Limited work on multi-objective conflict resolution in integrated systems",
                "themes": ["conflict resolution", "multi-objective", "arbitration", "priority"],
                "recommendation": "Search for conflict resolution and priority arbitration in multi-objective systems."
            },
            {
                "pillar": "Pillar 7: System Integration & Orchestration",
                "requirement_id": "REQ-7.3",
                "sub_requirement_id": "Sub-7.3.4",
                "requirement_text": "Meta-learning for system-level adaptation",
                "completeness": 30.0,
                "severity": "HIGH",
                "why": "Meta-learning rarely applied to full system adaptation",
                "themes": ["meta-learning", "system adaptation", "learning to learn", "hyperparameters"],
                "recommendation": "Search for meta-learning approaches for system-level optimization."
            },
            {
                "pillar": "Pillar 7: System Integration & Orchestration",
                "requirement_id": "REQ-7.5",
                "sub_requirement_id": "Sub-7.5.3",
                "requirement_text": "Self-organization principles",
                "completeness": 35.0,
                "severity": "MEDIUM",
                "why": "Self-organization in integrated neuromorphic systems underexplored",
                "themes": ["self-organization", "emergence", "spontaneous structure", "development"],
                "recommendation": "Search for self-organization principles in neuromorphic system development."
            },
            {
                "pillar": "Pillar 7: System Integration & Orchestration",
                "requirement_id": "REQ-7.5",
                "sub_requirement_id": "Sub-7.5.4",
                "requirement_text": "Critical periods for inter-pillar connectivity",
                "completeness": 15.0,
                "severity": "CRITICAL",
                "why": "No work on developmental critical periods in artificial systems",
                "themes": ["critical periods", "development", "connectivity", "plasticity windows"],
                "recommendation": "Search for critical period phenomena in artificial developmental systems."
            },
        ]
        
        for gap_data in gaps:
            self.add_known_gap(
                pillar=gap_data["pillar"],
                requirement_id=gap_data["requirement_id"],
                sub_requirement_id=gap_data["sub_requirement_id"],
                requirement_text=gap_data["requirement_text"],
                current_completeness=gap_data["completeness"],
                severity=gap_data["severity"],
                database_state_file=f"gap_states/{gap_data['sub_requirement_id']}.json",
                why_is_gap=gap_data["why"],
                recommendation_themes=gap_data["themes"],
                reference_recommendation=gap_data["recommendation"]
            )
    
    def save(self, filename: str = "golden_dataset.json"):
        """Save the golden dataset to file."""
        
        dataset = GoldenDataset(
            version="1.0.0",
            created_date=datetime.now(),
            last_updated=datetime.now(),
            description="Golden dataset for Literature Review validation testing",
            annotated_claims=self.claims,
            expected_verdicts=self.verdicts,
            known_gaps=self.gaps,
            recommendation_quality=self.recommendations
        )
        
        output_file = self.output_dir / filename
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(dataset.model_dump(mode='json'), f, indent=2, default=str)
        
        print(f"Saved golden dataset to: {output_file}")
        print(f"  Claims: {len(self.claims)}")
        print(f"  Verdicts: {len(self.verdicts)}")
        print(f"  Gaps: {len(self.gaps)}")
        print(f"  Recommendations: {len(self.recommendations)}")
        
        # Print breakdown by verdict
        approved = len([c for c in self.claims if c.expected_verdict == Verdict.APPROVED])
        rejected = len([c for c in self.claims if c.expected_verdict == Verdict.REJECTED])
        borderline = len([c for c in self.claims if c.expected_verdict == Verdict.BORDERLINE])
        print(f"  Verdict breakdown: approved={approved}, rejected={rejected}, borderline={borderline}")
        
        return output_file


def main():
    """Generate the golden dataset."""
    output_dir = Path(__file__).parent.parent / "data"
    
    populator = GoldenDatasetPopulator(output_dir)
    
    # Generate synthetic claims
    populator.generate_synthetic_claims()
    
    # Generate synthetic gaps
    populator.generate_synthetic_gaps()
    
    # Save dataset
    populator.save()


if __name__ == "__main__":
    main()
