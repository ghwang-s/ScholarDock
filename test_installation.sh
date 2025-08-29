#!/bin/bash

# ScholarDock Installation Test Script
# This script simulates the complete installation and running process

echo "========================================"
echo "  ScholarDock Installation Test"
echo "========================================"

# Check if conda is available
if ! command -v conda &> /dev/null
then
    echo "❌ Conda is not installed. Please install Miniconda or Anaconda first."
    exit 1
fi

echo "✅ Conda is available"

# Create test environment
echo "🔧 Creating test environment 'scholar_test'..."
conda create -n scholar_test python=3.9 -y

if [ $? -ne 0 ]; then
    echo "❌ Failed to create conda environment"
    exit 1
fi

echo "✅ Test environment created"

# Activate environment
echo "🔧 Activating test environment..."
eval "$(conda shell.bash hook)"
conda activate scholar_test

if [ $? -ne 0 ]; then
    echo "❌ Failed to activate conda environment"
    exit 1
fi

echo "✅ Test environment activated"

# Test backend dependencies installation
echo "🔧 Installing backend dependencies..."
cd backend
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install backend dependencies"
    conda deactivate
    exit 1
fi

echo "✅ Backend dependencies installed"

# Test frontend dependencies installation
echo "🔧 Installing frontend dependencies..."
cd ../frontend
npm install

if [ $? -ne 0 ]; then
    echo "❌ Failed to install frontend dependencies"
    conda deactivate
    exit 1
fi

echo "✅ Frontend dependencies installed"

# Test database directory creation
echo "🔧 Creating data directory..."
cd ..
mkdir -p data

if [ $? -ne 0 ]; then
    echo "❌ Failed to create data directory"
    conda deactivate
    exit 1
fi

echo "✅ Data directory created"

# Test environment variables
echo "🔧 Setting up environment variables..."
echo "EMAIL_ADDRESS=test@example.com" > .env
echo "EMAIL_PASSWORD=testpassword" >> .env

echo "✅ Environment variables configured"

# Summary
echo ""
echo "========================================"
echo "  Installation Test Summary"
echo "========================================"
echo "✅ Conda environment creation: SUCCESS"
echo "✅ Backend dependencies installation: SUCCESS"
echo "✅ Frontend dependencies installation: SUCCESS"
echo "✅ Data directory creation: SUCCESS"
echo "✅ Environment configuration: SUCCESS"
echo ""
echo "🎉 All installation tests passed!"
echo ""
echo "To run the application:"
echo "1. conda activate scholar_test"
echo "2. ./run.sh"
echo ""
echo "To clean up:"
echo "conda env remove -n scholar_test"
echo ""

# Deactivate environment
conda deactivate

echo "✅ Test environment deactivated"