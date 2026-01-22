#!/bin/bash
# Setup script for audio testing suite
# Creates virtual environment and installs dependencies

set -e  # Exit on error

echo "=================================================="
echo "Audio Test Suite - Setup"
echo "=================================================="

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "✗ Python 3 not found. Please install Python 3.8+"
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "\nCreating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "\n✓ Virtual environment already exists"
fi

# Activate virtual environment and install dependencies
echo "\nInstalling dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "\n=================================================="
echo "✓ Setup complete!"
echo "=================================================="
echo "\nTo use the test suite:"
echo "  1. Activate the virtual environment:"
echo "     source venv/bin/activate"
echo ""
echo "  2. Run setup check:"
echo "     python setup_check.py"
echo ""
echo "  3. Run tests:"
echo "     python test_audio.py"
echo ""
