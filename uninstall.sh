#!/bin/bash

# Define the home directory (where the repository was cloned)
HOME_DIR=$(pwd)  # スクリプトを実行した場所を使用

# Stop and disable the systemd service
sudo systemctl stop 1nce_network_monitor.service
sudo systemctl disable 1nce_network_monitor.service

# Remove the systemd service file
sudo rm /etc/systemd/system/1nce_network_monitor.service
sudo systemctl daemon-reload

# Remove the virtual environment
if [ -d "$HOME_DIR/venv" ]; then
    rm -rf $HOME_DIR/venv
    echo "Virtual environment removed."
else
    echo "No virtual environment found."
fi

# Remove config.py and log/data directories
if [ -f "$HOME_DIR/config.py" ]; then
    rm $HOME_DIR/config.py
    echo "config.py removed."
else
    echo "No config.py found."
fi

if [ -d "$HOME_DIR/log" ]; then
    rm -rf $HOME_DIR/log
    echo "Log directory removed."
else
    echo "No log directory found."
fi

if [ -d "$HOME_DIR/data" ]; then
    rm -rf $HOME_DIR/data
    echo "Data directory removed."
else
    echo "No data directory found."
fi

echo "Uninstallation complete. The 1NCE Network Monitor has been removed."
