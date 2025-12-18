#!/bin/bash
# Example workflow for generating PNL charts from batch optimization results

set -e  # Exit on error

echo "=========================================="
echo "PNL Chart Generation Workflow Example"
echo "=========================================="
echo ""

# Step 1: Analyze batch results and generate best configs
echo "Step 1: Analyzing batch optimization results..."
echo "----------------------------------------"
python3 post-processing/analyze_batch_results.py \
    --results-dir batch-analysis \
    --output-dir results \
    --objectives balanced final_pnl win_rate max_drawdown \
    --min-trades 10

echo ""
echo "✅ Best configs generated in results/"
echo ""

# Step 2: Generate PNL charts for each objective
echo "Step 2: Generating PNL charts..."
echo "----------------------------------------"

# Process balanced configs (recommended)
echo "Processing balanced optimization..."
python3 post-processing/generate_config_pnl.py \
    --config-file results/best_configs_balanced.json \
    --orders-dir optimization/orders \
    --output-dir plots/pnl_curves/balanced

# Process final_pnl configs
echo ""
echo "Processing final_pnl optimization..."
python3 post-processing/generate_config_pnl.py \
    --config-file results/best_configs_final_pnl.json \
    --orders-dir optimization/orders \
    --output-dir plots/pnl_curves/final_pnl

# Process win_rate configs
echo ""
echo "Processing win_rate optimization..."
python3 post-processing/generate_config_pnl.py \
    --config-file results/best_configs_win_rate.json \
    --orders-dir optimization/orders \
    --output-dir plots/pnl_curves/win_rate

# Process max_drawdown configs
echo ""
echo "Processing max_drawdown optimization..."
python3 post-processing/generate_config_pnl.py \
    --config-file results/best_configs_max_drawdown.json \
    --orders-dir optimization/orders \
    --output-dir plots/pnl_curves/max_drawdown

echo ""
echo "=========================================="
echo "✅ Workflow Complete!"
echo "=========================================="
echo ""
echo "Results:"
echo "  - Best configs: results/best_configs_*.json"
echo "  - PNL charts: plots/pnl_curves/*/"
echo "  - Summaries: plots/pnl_curves/*/pnl_generation_summary_*.json"
echo ""
echo "Quick view commands:"
echo "  open plots/pnl_curves/balanced/portfolio_balanced_pnl.png"
echo "  cat results/portfolio_summary.txt"
echo ""
