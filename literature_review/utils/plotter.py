"""
Enhanced Visualization Module for Gap Analysis (v2.0)
Includes interactive plots, network visualizations, and trend analysis.
Modified to be compatible with Orchestrator.py data structures.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import networkx as nx
from typing import Dict, List, Optional, Any
import json
import logging

# Setup logging
logger = logging.getLogger(__name__)

# Color schemes
COLOR_SCHEMES = {
    'completeness': {
        'critical': '#dc3545',  # Red: 0-20%
        'low': '#fd7e14',  # Orange: 21-40%
        'moderate': '#ffc107',  # Yellow: 41-60%
        'good': '#20c997',  # Teal: 61-80%
        'excellent': '#28a745'  # Green: 81-100%
    },
    'velocity': '#007bff', # Blue
    'comparison': '#6c757d' # Gray
}


def get_color_by_score(score: float) -> str:
    """Get color based on completeness score"""
    if score <= 20:
        return COLOR_SCHEMES['completeness']['critical']
    elif score <= 40:
        return COLOR_SCHEMES['completeness']['low']
    elif score <= 60:
        return COLOR_SCHEMES['completeness']['moderate']
    elif score <= 80:
        return COLOR_SCHEMES['completeness']['good']
    else:
        return COLOR_SCHEMES['completeness']['excellent']


def create_waterfall_plot(pillar_name: str, waterfall_data: List[Dict],
                          save_path: str, show_targets: bool = True):
    """
    Generate enhanced waterfall plot with cumulative progress and targets
    """
    if not waterfall_data:
        logger.warning(f"No data for waterfall plot: {pillar_name}")
        return

    try:
        requirements = [d['requirement'] for d in waterfall_data]
        values = [d['value'] for d in waterfall_data]
        gaps = [d['gap_analysis'] for d in waterfall_data]

        cumulative = np.cumsum(values)
        total_value = cumulative[-1]

        # Create figure with secondary y-axis
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # Add waterfall bars
        colors = [get_color_by_score(v) for v in values]
        fig.add_trace(
            go.Bar(
                name='Requirement Completeness',
                x=requirements,
                y=values,
                marker_color=colors,
                text=[f"{v:.1f}%" for v in values],
                textposition='outside',
                customdata=gaps,
                hovertemplate=(
                        "<b>%{x}</b><br>" +
                        "Completeness: %{y:.1f}%<br>" +
                        "<b>Gap Analysis:</b><br>%{customdata}<br>" +
                        "<extra></extra>"
                )
            ),
            secondary_y=False
        )

        # Add cumulative line
        fig.add_trace(
            go.Scatter(
                name='Cumulative Progress',
                x=requirements,
                y=cumulative,
                mode='lines+markers',
                line=dict(color='#333', width=2, dash='dash'),
                marker=dict(size=8),
                hovertemplate="Cumulative: %{y:.1f}%<extra></extra>"
            ),
            secondary_y=True
        )

        # Add target line
        if show_targets:
            target_value = len(requirements) * 100 # Max possible score
            fig.add_hline(
                y=target_value,
                line_dash="dot",
                line_color="gray",
                annotation_text=f"Target: {target_value:.0f}",
                annotation_position="bottom right",
                secondary_y=True
            )

        # Update layout
        fig.update_layout(
            title=f"Research Gap Analysis: {pillar_name} (Total: {total_value:.1f}%)",
            xaxis_title="Requirements",
            yaxis_title="Individual Completeness (%)",
            yaxis2_title="Cumulative Completeness (%)",
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode='x unified',
            plot_bgcolor='#f8f9fa',
            paper_bgcolor='white',
            font=dict(family="Arial, sans-serif"),
            margin=dict(t=100, b=100, l=80, r=80),
            height=600,
            yaxis=dict(range=[0, 100]),
            yaxis2=dict(range=[0, max(cumulative) * 1.2 + 20])
        )

        # Add critical gap annotations
        critical_indices = [i for i, v in enumerate(values) if v < 30]
        for idx in critical_indices[:3]:  # Annotate top 3
            fig.add_annotation(
                x=requirements[idx],
                y=values[idx],
                text="Critical Gap",
                showarrow=True,
                arrowhead=2,
                arrowcolor=COLOR_SCHEMES['completeness']['critical'],
                font=dict(color=COLOR_SCHEMES['completeness']['critical'], size=10)
            )

        fig.write_html(save_path)
        logger.info(f"Enhanced waterfall plot saved to {save_path}")
    except Exception as e:
        logger.error(f"Failed to create waterfall plot {pillar_name}: {e}")


def create_radar_plot(radar_data: Dict, save_path: str,
                      velocity_data: Optional[Dict] = None,
                      comparison_data: Optional[Dict] = None):
    """
    Generate enhanced radar plot.
    MODIFIED: Scales velocity data to fit the 0-100 axis and uses hover text.
    """
    if not radar_data:
        logger.warning("No data for radar plot")
        return

    categories = list(radar_data.keys())
    values = list(radar_data.values())

    # Shorten labels
    labels = [f"P{i + 1}: {cat.split(':')[1].split('(')[0].strip()}" for i, cat in enumerate(categories)]

    fig = go.Figure()

    # --- Trace 1: Current Completeness ---
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=labels + [labels[0]],
        fill='toself',
        fillcolor='rgba(40, 167, 69, 0.3)',
        line=dict(color=COLOR_SCHEMES['completeness']['excellent'], width=2),
        name='Completeness (%)',
        hovertemplate="%{theta}<br>Completeness: %{r:.1f}%<extra></extra>"
    ))

    # --- Trace 2: Comparison Data ---
    if comparison_data:
        comp_values = [comparison_data.get(cat, 0) for cat in categories]
        fig.add_trace(go.Scatterpolar(
            r=comp_values + [comp_values[0]],
            theta=labels + [labels[0]],
            line=dict(color=COLOR_SCHEMES['comparison'], width=2, dash='dash'),
            name='Previous Assessment',
            hovertemplate="%{theta}<br>Previous: %{r:.1f}%<extra></extra>"
        ))

    # --- Trace 3: Velocity Data (Scaled) ---
    if velocity_data:
        original_vel_values = [velocity_data.get(cat, 0) for cat in categories]

        # --- Scaling Logic ---
        min_vel = min(original_vel_values)
        max_vel = max(original_vel_values)
        vel_range = max_vel - min_vel

        scaled_vel_values = []
        if vel_range == 0:  # Avoid division by zero if all velocities are the same
            scaled_vel_values = [50.0] * len(original_vel_values)  # Map to midpoint
        else:
            for v in original_vel_values:
                # Scale v from [min_vel, max_vel] to [0, 100]
                scaled_v = ((v - min_vel) / vel_range) * 100
                scaled_vel_values.append(scaled_v)
        # --- End Scaling Logic ---

        fig.add_trace(go.Scatterpolar(
            r=scaled_vel_values,  # Use scaled values for radius
            theta=labels,
            name='Velocity (Scaled 0-100)',
            line=dict(color=COLOR_SCHEMES['velocity'], width=3),
            marker=dict(size=8),
            mode='lines+markers',
            customdata=original_vel_values,  # Store original values for hover
            hovertemplate="%{theta}<br>Velocity: %{customdata:+.1f} papers/yr<br>(Scaled Value: %{r:.1f})<extra></extra>"
        ))

    # --- Update Layout (Removed radialaxis2) ---
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],  # Single axis from 0 to 100
                tickmode='array',
                tickvals=[0, 25, 50, 75, 100],
                ticktext=['0%', '25%', '50%', '75%', '100%'],
                gridcolor='lightgray',
                gridwidth=1
            ),
            # REMOVED radialaxis2 dictionary
            angularaxis=dict(
                tickfont=dict(size=10),
                rotation=90,
                direction='clockwise'
            ),
            bgcolor='#f8f9fa'
        ),
        showlegend=True,
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.1),
        title="Research Completeness & Velocity Overview",
        paper_bgcolor='white',
        font=dict(family="Arial, sans-serif"),
        margin=dict(t=100, b=50, l=50, r=150),
        height=700,
        width=900
    )

    # Add summary statistics (remains the same)
    mean_completeness = np.mean(values)
    fig.add_annotation(
        text=(
                f"<b>Summary Statistics</b><br>" +
                f"Mean: {mean_completeness:.1f}%<br>" +
                f"Std Dev: {np.std(values):.1f}%<br>" +
                f"Min: {min(values):.1f}% | Max: {max(values):.1f}%"
        ),
        xref="paper", yref="paper",
        x=0.02, y=0.98, showarrow=False,
        bgcolor="white", bordercolor="#333", borderwidth=1,
        font=dict(size=10), align="left"
    )

    # Add velocity scaling info if velocity was plotted
    if velocity_data:
        fig.add_annotation(
            text=(
                    f"<b>Velocity Scaling</b><br>" +
                    f"Min Vel ({min_vel:+.1f}) maps to 0<br>" +
                    f"Zero Vel (0.0) maps near 50<br>" +  # Approximate mapping
                    f"Max Vel ({max_vel:+.1f}) maps to 100"
            ),
            xref="paper", yref="paper",
            x=0.02, y=0.15,  # Position lower left
            showarrow=False,
            bgcolor="rgba(230, 230, 230, 0.7)",
            bordercolor="#888", borderwidth=1,
            font=dict(size=9, color="#333"), align="left"
        )

    fig.write_html(save_path)
    logger.info(f"Enhanced radar plot saved to {save_path}")


def create_network_plot(graph: nx.Graph, save_path: str,
                        highlight_nodes: List[str] = None,
                        layout_type: str = 'spring'):
    """
    Create interactive network visualization of paper relationships
    """
    if graph.number_of_nodes() == 0:
        logger.warning("Empty graph for network plot")
        return

    try:
        if layout_type == 'spring':
            pos = nx.spring_layout(graph, k=0.5, iterations=50)
        elif layout_type == 'circular':
            pos = nx.circular_layout(graph)
        else:
            pos = nx.kamada_kawai_layout(graph)

        centrality = nx.degree_centrality(graph)
        if not centrality:
            centrality = {node: 0.1 for node in graph.nodes()}

        min_cent = min(centrality.values())
        max_cent = max(centrality.values())

        node_x, node_y, node_text, node_color, node_size = [], [], [], [], []

        for node in graph.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_data = graph.nodes[node]
            hover_text = (
                    f"<b>{node_data.get('TITLE', node)}</b><br>" +
                    f"File: {node}<br>" +
                    f"Domain: {node_data.get('CORE_DOMAIN', 'N/A')}<br>" +
                    f"Relevance: {node_data.get('SUBDOMAIN_RELEVANCE_TO_RESEARCH_SCORE', 0)}%"
            )
            node_text.append(hover_text)

            importance = centrality.get(node, 0)

            if highlight_nodes and node in highlight_nodes:
                node_color.append(COLOR_SCHEMES['completeness']['critical'])
                node_size.append(30)
            else:
                node_color.append(importance)
                # Scale size
                if max_cent > min_cent:
                    norm_size = 10 + 20 * (importance - min_cent) / (max_cent - min_cent)
                else:
                    norm_size = 10
                node_size.append(norm_size)

        edge_x = [pos[edge[0]][0] for edge in graph.edges()] + [pos[edge[1]][0] for edge in graph.edges()]
        edge_y = [pos[edge[0]][1] for edge in graph.edges()] + [pos[edge[1]][1] for edge in graph.edges()]

        # Create edge trace
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines'
        )

        # Create node trace
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers',
            hoverinfo='text',
            hovertext=node_text,
            marker=dict(
                showscale=True,
                colorscale='Viridis',
                size=node_size,
                color=node_color,
                colorbar=dict(
                    thickness=15,
                    title='Node Centrality',
                    xanchor='left',
                    title_side='right'
                ),
                line=dict(width=2, color='white')
            )
        )

        fig = go.Figure(data=[edge_trace, node_trace])
        fig.update_layout(
            title='Research Paper Network',
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor='#f8f9fa',
            paper_bgcolor='white',
            height=800
        )

        # Add network statistics
        fig.add_annotation(
            text=(
                    f"<b>Network Statistics</b><br>" +
                    f"Papers: {graph.number_of_nodes()}<br>" +
                    f"Connections: {graph.number_of_edges()}<br>" +
                    f"Density: {nx.density(graph):.3f}"
            ),
            xref="paper", yref="paper",
            x=0.02, y=0.98, showarrow=False,
            bgcolor="white", bordercolor="#333", borderwidth=1,
            font=dict(size=10), align="left"
        )

        fig.write_html(save_path)
        logger.info(f"Network plot saved to {save_path}")
    except Exception as e:
        logger.error(f"Failed to create network plot: {e}")


def create_trend_plot(trend_data: Dict, save_path: str):
    """
    Create trend visualization.
    MODIFIED: Parses Orchestrator's full trend_data dict and plots
    two separate line charts for "Absolute Count" and "Relative Focus".
    """
    if not trend_data:
        logger.warning("No trend data available for trend plot")
        return

    try:
        df_data = []
        for year, pillars in trend_data.items():
            for pillar_name, metrics in pillars.items():
                df_data.append({
                    'Year': int(year),
                    'Pillar': pillar_name.split(':')[0],
                    'Absolute Count': metrics.get('absolute_count', 0),
                    'Relative Focus (%)': metrics.get('relative_focus_percent', 0)
                })

        df = pd.DataFrame(df_data)
        if df.empty:
            logger.warning("Trend data was empty after parsing.")
            return

        # Create two subplots, one for each metric
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            subplot_titles=('Research Trends: Absolute Paper Count', 'Research Trends: Relative Focus (%)')
        )

        pillars = df['Pillar'].unique()
        colors = px.colors.qualitative.Plotly

        for i, pillar in enumerate(pillars):
            pillar_data = df[df['Pillar'] == pillar]
            color = colors[i % len(colors)]

            # Plot Absolute Count
            fig.add_trace(go.Scatter(
                x=pillar_data['Year'],
                y=pillar_data['Absolute Count'],
                name=pillar,
                mode='lines+markers',
                line=dict(color=color),
                legendgroup=pillar
            ), row=1, col=1)

            # Plot Relative Focus
            fig.add_trace(go.Scatter(
                x=pillar_data['Year'],
                y=pillar_data['Relative Focus (%)'],
                name=pillar,
                mode='lines+markers',
                line=dict(color=color),
                legendgroup=pillar,
                showlegend=False # Show legend only once
            ), row=2, col=1)

        fig.update_layout(
            hovermode='x unified',
            xaxis=dict(dtick=1),
            xaxis2=dict(title='Publication Year', dtick=1),
            yaxis1=dict(title='Absolute Count'),
            yaxis2=dict(title='Relative Focus (%)', ticksuffix='%'),
            height=800,
            plot_bgcolor='#f8f9fa',
            paper_bgcolor='white'
        )

        fig.write_html(save_path)
        logger.info(f"Trend plot saved to {save_path}")
    except Exception as e:
        logger.error(f"Failed to create trend plot: {e}")


def create_heatmap_matrix(pillar_data: Dict, save_path: str):
    """
    Create a heatmap matrix showing requirement completeness across pillars
    """
    try:
        pillars = []
        requirements = set()
        req_map = {} # Map short req names to full names

        for pillar_name, data in pillar_data.items():
            pillars.append(pillar_name)
            for req_key in data.get('analysis', {}).keys():
                req_short = req_key.split(':')[0]
                requirements.add(req_short)
                req_map[req_short] = req_key

        requirements = sorted(list(requirements))
        if not requirements or not pillars:
            logger.warning("No data for heatmap plot.")
            return

        matrix = []
        hover_text = []

        for req in requirements:
            row = []
            row_text = []
            for pillar_name in pillars:
                analysis = pillar_data[pillar_name].get('analysis', {})
                completeness = 0
                gaps = "N/A"

                # Find matching requirement
                found = False
                for req_key, sub_reqs in analysis.items():
                    if req_key.split(':')[0] == req:
                        scores = [sub.get('completeness_percent', 0) for sub in sub_reqs.values()]
                        completeness = np.mean(scores) if scores else 0

                        gap_list = [
                            f"- {sub_key.split(':')[0]}: {sub.get('gap_analysis', 'N/A')}"
                            for sub_key, sub in sub_reqs.items()
                            if sub.get('completeness_percent', 100) < 90
                        ]
                        gaps = "<br>".join(gap_list) if gap_list else "Complete"
                        found = True
                        break

                row.append(completeness)
                row_text.append(f"<b>{req_map[req]}</b><br>Pillar: {pillar_name.split(':')[0]}<br>Completeness: {completeness:.1f}%<br>Gaps:<br>{gaps}<extra></extra>")

            matrix.append(row)
            hover_text.append(row_text)

        fig = go.Figure(data=go.Heatmap(
            z=matrix,
            x=[p.split(':')[0] for p in pillars],
            y=requirements,
            colorscale='RdYlGn',
            zmin=0,
            zmax=100,
            text=[[f"{val:.0f}%" for val in row] for row in matrix],
            texttemplate="%{text}",
            textfont={"size": 10},
            colorbar=dict(title="Completeness (%)"),
            hoverinfo='text',
            hovertemplate = hover_text
        ))

        fig.update_layout(
            title="Requirement Completeness Matrix",
            xaxis_title="Research Pillars",
            yaxis_title="Requirements",
            height=max(600, len(requirements) * 50),
            width=max(800, len(pillars) * 150),
            xaxis=dict(side='top')
        )

        fig.write_html(save_path)
        logger.info(f"Heatmap matrix saved to {save_path}")
    except Exception as e:
        logger.error(f"Failed to create heatmap matrix: {e}")


# --- TEMPORAL COHERENCE VISUALIZATION FUNCTIONS (Task Card #19) ---

def plot_evidence_evolution(temporal_analysis: Dict, output_file: str):
    """
    Create heatmap showing evidence emergence over time.
    
    Args:
        temporal_analysis: Dictionary from analyze_evidence_evolution
        output_file: Path to save the output image
    
    Rows: Sub-requirements
    Columns: Years
    Cell values: Number of papers
    """
    import matplotlib.pyplot as plt
    import seaborn as sns
    
    if not temporal_analysis:
        logger.warning("No temporal analysis data to plot")
        return
    
    try:
        # Build matrix: rows = sub-requirements, cols = years
        sub_reqs = list(temporal_analysis.keys())
        all_years = sorted(set(
            year 
            for data in temporal_analysis.values() 
            for year in data["evidence_count_by_year"].keys()
        ))
        
        if not all_years:
            logger.warning("No years found in temporal analysis data")
            return
        
        matrix = np.zeros((len(sub_reqs), len(all_years)))
        
        for i, sub_req in enumerate(sub_reqs):
            for j, year in enumerate(all_years):
                count = temporal_analysis[sub_req]["evidence_count_by_year"].get(year, 0)
                matrix[i, j] = count
        
        # Plot heatmap
        plt.figure(figsize=(16, 12))
        sns.heatmap(
            matrix,
            xticklabels=all_years,
            yticklabels=sub_reqs,
            cmap="YlOrRd",
            annot=True,
            fmt=".0f",
            cbar_kws={"label": "Number of Papers"}
        )
        plt.title("Evidence Evolution: Papers per Sub-Requirement by Year")
        plt.xlabel("Publication Year")
        plt.ylabel("Sub-Requirement")
        plt.tight_layout()
        plt.savefig(output_file, dpi=300)
        plt.close()
        logger.info(f"Evidence evolution heatmap saved to {output_file}")
    except Exception as e:
        logger.error(f"Failed to create evidence evolution plot: {e}")


def plot_maturity_distribution(temporal_analysis: Dict, output_file: str):
    """
    Plot distribution of maturity levels across sub-requirements.
    
    Args:
        temporal_analysis: Dictionary from analyze_evidence_evolution
        output_file: Path to save the output image
    """
    import matplotlib.pyplot as plt
    
    if not temporal_analysis:
        logger.warning("No temporal analysis data to plot")
        return
    
    try:
        maturity_counts = {}
        for data in temporal_analysis.values():
            level = data["maturity_level"]
            maturity_counts[level] = maturity_counts.get(level, 0) + 1
        
        levels = ["emerging", "growing", "established", "mature"]
        counts = [maturity_counts.get(level, 0) for level in levels]
        colors = ['#ff9999', '#ffcc99', '#99cc99', '#66b2ff']
        
        plt.figure(figsize=(10, 6))
        bars = plt.bar(levels, counts, color=colors)
        plt.xlabel("Maturity Level")
        plt.ylabel("Number of Sub-Requirements")
        plt.title("Evidence Maturity Distribution")
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                plt.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}',
                        ha='center', va='bottom')
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300)
        plt.close()
        logger.info(f"Maturity distribution plot saved to {output_file}")
    except Exception as e:
        logger.error(f"Failed to create maturity distribution plot: {e}")

# --- END TEMPORAL COHERENCE VISUALIZATION FUNCTIONS ---


# Export all functions
__all__ = [
    'create_waterfall_plot',
    'create_radar_plot',
    'create_network_plot',
    'create_trend_plot',
    'create_heatmap_matrix',
    'get_color_by_score',
    'plot_evidence_evolution',
    'plot_maturity_distribution'
]