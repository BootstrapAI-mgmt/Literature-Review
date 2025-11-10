"""
Standalone Plot Generator for Gap Analysis Results
Reads data from Orchestrator output files and generates visualizations.
"""

import json
import os
import ReviewPlotter as plotter # Assumes ReviewPlotter.py is in the same directory
import logging

# --- CONFIGURATION ---
OUTPUT_FOLDER = 'gap_analysis_output'
REPORT_FILE = os.path.join(OUTPUT_FOLDER, 'gap_analysis_report.json') # Main data file
PLOTS_OUTPUT_FOLDER = 'generated_plots' # Separate folder for these plots

# Setup logging (optional, but good practice)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create directories
os.makedirs(PLOTS_OUTPUT_FOLDER, exist_ok=True)

# --- MAIN PLOTTING FUNCTION ---
def generate_all_plots():
    logger.info(f"Loading analysis results from: {REPORT_FILE}")
    try:
        with open(REPORT_FILE, 'r') as f:
            all_results = json.load(f)
        logger.info(f"Successfully loaded data for {len(all_results)} pillars.")
    except FileNotFoundError:
        logger.error(f"ERROR: Report file not found at {REPORT_FILE}. Run Orchestrator first.")
        return
    except json.JSONDecodeError:
        logger.error(f"ERROR: Could not decode JSON from {REPORT_FILE}.")
        return

    # --- 1. Prepare Data for Radar Plot ---
    radar_data = {}
    velocity_data = {}
    has_velocity = False

    for pillar_name, pillar_results in all_results.items():
        radar_data[pillar_name] = pillar_results.get('completeness', 0)
        if 'research_velocity' in pillar_results:
             velocity_data[pillar_name] = pillar_results['research_velocity']
             has_velocity = True

    if not radar_data:
        logger.warning("No completeness data found in the report file.")
        return

    # --- 2. Generate Radar Plot ---
    logger.info("Generating Radar Plot...")
    radar_save_path = os.path.join(PLOTS_OUTPUT_FOLDER, "_STANDALONE_Radar_Plot.html")
    plotter.create_radar_plot(
        radar_data,
        radar_save_path,
        velocity_data=velocity_data if has_velocity else None
        # comparison_data could be loaded from another file if needed
    )

    # --- 3. Generate Waterfall Plots (Example for one pillar) ---
    # You could loop through all pillars here if desired
    logger.info("Generating Waterfall Plots...")
    for pillar_name, pillar_results in all_results.items():
         waterfall_data = pillar_results.get('waterfall_data')
         if waterfall_data:
             waterfall_save_path = os.path.join(PLOTS_OUTPUT_FOLDER, f"waterfall_{pillar_name.split(':')[0]}.html")
             plotter.create_waterfall_plot(
                 pillar_name,
                 waterfall_data,
                 waterfall_save_path
             )
         else:
             logger.warning(f"No waterfall data found for pillar: {pillar_name}")


    # --- 4. Generate Heatmap ---
    logger.info("Generating Heatmap Matrix...")
    heatmap_save_path = os.path.join(PLOTS_OUTPUT_FOLDER, "_STANDALONE_Heatmap.html")
    plotter.create_heatmap_matrix(all_results, heatmap_save_path)


    # Add calls for network plots, trend plots etc. by loading relevant data
    # (Network data might need separate loading if not in the main JSON)

    logger.info(f"All requested plots generated in: {PLOTS_OUTPUT_FOLDER}")

if __name__ == "__main__":
    generate_all_plots()