#!/bin/bash

echo "🔍 Checking for Conda..."

if ! command -v conda &> /dev/null
then
    echo "❌ Conda not found."
    echo "📦 Downloading Miniconda..."

    # Download Miniconda installer
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O Miniconda3-latest-Linux-x86_64.sh

    echo "📦 Installing Miniconda..."
    # Install silently to $HOME/miniconda3
    bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda3

    # Initialize conda for the current shell
    eval "$($HOME/miniconda3/bin/conda shell.bash hook)"

    echo "==================================="
    echo "✅ Miniconda installation finished!"
    echo "==================================="
    # Clean up installer
    rm Miniconda3-latest-Linux-x86_64.sh

    # Accept conda ToS
    conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
    conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
    conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/msys2
else
    echo "✅ Conda found."
    # Initialize if needed (e.g. if conda is installed but not activated in non-interactive shell)
    # This might be tricky, assuming user has it in path or initialized
fi

echo "📦 Creating/Updating virtual environment 'tower_defense'..."
conda create -n tower_defense python=3.12 -y

echo "🚀 Activating virtual environment..."
# Need to use source activate or conda activate depending on setup
# 'conda activate' requires 'conda init' usually.
# Let's try to source the activate script directly if we know where it is, or rely on conda command
source $(conda info --base)/etc/profile.d/conda.sh
conda activate tower_defense

echo "📦 Installing dependencies..."
pip install pygame==2.6.1

echo "==================================="
echo "🎉 Installation Complete!"
echo "==================================="
echo "To start the game."
echo ""
echo "# Give execute permission to run.sh"
echo "chmod +x run-linux.sh"
echo ""
echo "# Run the game"
echo "./run-linux.sh"
echo "==================================="
