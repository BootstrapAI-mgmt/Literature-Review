"""
Publication Bias Detection Module (Task Card #22)

This module implements optional publication bias detection for systematic literature
reviews using funnel plot analysis, Egger's regression test, and trim-and-fill method.

Only applies to sub-requirements with ≥20 papers.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from typing import Dict, List, Optional


def detect_publication_bias(claims: List[Dict], sub_req_name: str) -> Optional[Dict]:
    """
    Detect publication bias using funnel plot and statistical tests.
    
    Args:
        claims: List of claims for a sub-requirement
        sub_req_name: Name of sub-requirement
        
    Returns:
        Bias assessment dict or None if insufficient data
    """
    # Require at least 20 papers for meaningful analysis
    if len(claims) < 20:
        return None
    
    # Extract effect sizes (composite scores) and precision (1/std_dev)
    effect_sizes = []
    precisions = []
    
    for claim in claims:
        quality = claim.get("evidence_quality", {})
        score = quality.get("composite_score")
        
        if score is not None:
            effect_sizes.append(score)
            # Use score as proxy for precision (higher quality = more precise)
            precision = score / 5.0  # Normalize to 0-1
            precisions.append(precision)
    
    if len(effect_sizes) < 20:
        return None
    
    effect_sizes = np.array(effect_sizes)
    precisions = np.array(precisions)
    
    # Egger's regression test
    egger_result = _eggers_test(effect_sizes, precisions)
    
    # Trim-and-fill analysis
    trimfill_result = _trim_and_fill(effect_sizes, precisions)
    
    # Visual asymmetry score
    asymmetry_score = _calculate_funnel_asymmetry(effect_sizes, precisions)
    
    # Overall bias assessment
    bias_detected = bool(
        egger_result["p_value"] < 0.05 or
        asymmetry_score > 0.3 or
        trimfill_result["missing_studies"] > 5
    )
    
    return {
        "sub_requirement": sub_req_name,
        "num_studies": len(effect_sizes),
        "bias_detected": bias_detected,
        "eggers_test": egger_result,
        "trim_and_fill": trimfill_result,
        "asymmetry_score": round(asymmetry_score, 3),
        "interpretation": _interpret_bias(bias_detected, egger_result, trimfill_result)
    }


def _eggers_test(effect_sizes: np.ndarray, precisions: np.ndarray) -> Dict:
    """
    Perform Egger's regression test for funnel plot asymmetry.
    
    Tests if small studies have different average effects than large studies.
    """
    # Regression: effect_size ~ precision
    slope, intercept, r_value, p_value, std_err = stats.linregress(precisions, effect_sizes)
    
    return {
        "slope": round(float(slope), 3),
        "intercept": round(float(intercept), 3),
        "p_value": round(float(p_value), 4),
        "significant": bool(p_value < 0.05)
    }


def _trim_and_fill(effect_sizes: np.ndarray, precisions: np.ndarray) -> Dict:
    """
    Duval & Tweedie trim-and-fill method to estimate missing studies.
    
    Simplified implementation: assumes symmetric funnel plot.
    """
    # Sort by precision
    sorted_indices = np.argsort(precisions)[::-1]  # High to low precision
    sorted_effects = effect_sizes[sorted_indices]
    
    # Estimate center (median effect)
    center = np.median(sorted_effects)
    
    # Count studies on each side of center
    left_studies = int(np.sum(sorted_effects < center))
    right_studies = int(np.sum(sorted_effects > center))
    
    # Missing studies = imbalance
    missing_studies = abs(left_studies - right_studies)
    
    # Adjusted effect (after imputing missing studies)
    if missing_studies > 0:
        if left_studies < right_studies:
            # Missing negative studies
            imputed_effects = np.concatenate([sorted_effects, np.repeat(center - 0.5, missing_studies)])
        else:
            # Missing positive studies
            imputed_effects = np.concatenate([sorted_effects, np.repeat(center + 0.5, missing_studies)])
        adjusted_mean = float(np.mean(imputed_effects))
    else:
        adjusted_mean = float(np.mean(sorted_effects))
    
    original_mean = float(np.mean(sorted_effects))
    
    return {
        "missing_studies": int(missing_studies),
        "original_mean": round(original_mean, 2),
        "adjusted_mean": round(adjusted_mean, 2),
        "bias_magnitude": round(abs(adjusted_mean - original_mean), 2)
    }


def _calculate_funnel_asymmetry(effect_sizes: np.ndarray, precisions: np.ndarray) -> float:
    """
    Calculate visual funnel plot asymmetry score.
    
    Returns score 0-1 (higher = more asymmetric).
    """
    # Split by precision (high vs low)
    median_precision = np.median(precisions)
    
    high_precision = effect_sizes[precisions >= median_precision]
    low_precision = effect_sizes[precisions < median_precision]
    
    if len(high_precision) < 5 or len(low_precision) < 5:
        return 0.0
    
    # Compare mean effects
    mean_diff = abs(np.mean(high_precision) - np.mean(low_precision))
    
    # Normalize by overall std dev
    overall_std = np.std(effect_sizes)
    asymmetry = mean_diff / overall_std if overall_std > 0 else 0.0
    
    return min(asymmetry, 1.0)  # Cap at 1.0


def _interpret_bias(bias_detected: bool, egger: Dict, trimfill: Dict) -> str:
    """Generate interpretation of bias assessment."""
    if not bias_detected:
        return "No significant publication bias detected. Evidence base appears balanced."
    
    interpretation = f"⚠️ **Publication bias suspected**. "
    
    if egger["significant"]:
        interpretation += f"Egger's test significant (p={egger['p_value']}). "
    
    if trimfill["missing_studies"] > 0:
        interpretation += f"Estimated {trimfill['missing_studies']} missing studies. "
        interpretation += f"Adjusted effect: {trimfill['adjusted_mean']} (vs. {trimfill['original_mean']} observed). "
    
    interpretation += "Consider targeted search for unpublished studies or negative results."
    
    return interpretation


def plot_funnel_plot(claims: List[Dict], sub_req_name: str, output_file: str):
    """Generate funnel plot visualization."""
    effect_sizes = []
    precisions = []
    
    for claim in claims:
        quality = claim.get("evidence_quality", {})
        score = quality.get("composite_score")
        if score is not None:
            effect_sizes.append(score)
            precisions.append(score / 5.0)
    
    if len(effect_sizes) < 10:
        return
    
    effect_sizes = np.array(effect_sizes)
    precisions = np.array(precisions)
    
    # Create funnel plot
    plt.figure(figsize=(10, 8))
    plt.scatter(effect_sizes, precisions, alpha=0.6, s=100)
    
    # Add reference lines (expected funnel)
    mean_effect = np.mean(effect_sizes)
    plt.axvline(mean_effect, color='red', linestyle='--', label=f'Mean Effect: {mean_effect:.2f}')
    
    plt.xlabel('Effect Size (Composite Score)')
    plt.ylabel('Precision')
    plt.title(f'Funnel Plot: {sub_req_name}')
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.close()
