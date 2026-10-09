#!/bin/bash
echo "🚀 Starting Tower Defense..."

# Try to detect conda base path and source it
if command -v conda &> /dev/null; then
    source $(conda info --base)/etc/profile.d/conda.sh
elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/miniconda3/etc/profile.d/conda.sh"
elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/anaconda3/etc/profile.d/conda.sh"
fi

conda activate tower_defense
if [ $? -ne 0 ]; then
    echo "❌ Failed to activate environment. Have you run ./install.sh?"
    exit 1
fi

python main.py
exit
