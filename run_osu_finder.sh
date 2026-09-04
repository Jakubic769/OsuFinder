#!/bin/bash

# Change to the directory where the script is located
cd "$(dirname "$0")" || exit

# Install dependencies
python -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo
    echo "Failed to install dependencies."
    read -p "Press any key to continue..." -n1 -s
    echo
    exit 1
fi

# Run the main script
python osu_finder.py
if [ $? -ne 0 ]; then
    read -p "Press any key to continue..." -n1 -s
    echo
fi
