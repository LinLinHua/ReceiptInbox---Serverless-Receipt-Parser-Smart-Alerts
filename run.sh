#!/bin/bash

# create output directory
echo "Creating output directory..."
mkdir -p output/figures
mkdir -p output/models

# run training script
echo "Running training script..."
cd src
python train.py > ../log.txt