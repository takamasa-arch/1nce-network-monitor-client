#!/bin/bash

# Function to display usage instructions
usage() {
  echo "Usage: $0 <BROKER_IP> <ICCID>"
  exit 1
}

# Check for required arguments
if [ "$#" -lt 2 ]; then
  usage
fi

BROKER_IP=$1
ICCID=$2
HOME_DIR=$(pwd)  # スクリプトを実行した場所を使用
CURRENT_USER=$(whoami)  # 現在のユーザーを取得

# Install picocom if it's not already installed
sudo apt update
sudo apt install -y picocom

# Check if the virtual environment directory exists
if [ -d "$HOME_DIR/venv" ]; then
    echo "Virtual environment already exists. Activating it..."
    source $HOME_DIR/venv/bin/activate
else
    echo "Creating a new virtual environment..."
    python3 -m venv $HOME_DIR/venv
    source $HOME_DIR/venv/bin/activate
fi

# Install necessary Python packages if not already installed
REQUIRED_PACKAGES=("paho-mqtt" "ping3")
for PACKAGE in "${REQUIRED_PACKAGES[@]}"; do
    if pip show "$PACKAGE" > /dev/null 2>&1; then
        echo "$PACKAGE is already installed."
    else
        echo "Installing $PACKAGE..."
        pip install "$PACKAGE"
    fi
done

# Create or overwrite the config.py file
cat <<EOL > $HOME_DIR/config.py
# Configuration for 1NCE Network Monitor

# MQTT Broker details
BROKER_ADDRESS = "$BROKER_IP"
PORT = 1883

# Device ICCID
ICCID = "$ICCID"

# Topics
TOPIC = f"devices/{ICCID}/data"
TOPIC_RADIO = f"devices/{ICCID}/radio"

# Servers to ping
GOOGLE_SERVER = '8.8.8.8'

# Directories for logs and data
LOG_DIR_PATH = '$HOME_DIR/log'
LOG_DIR = '$HOME_DIR/data/network_log'
MQTT_DIR = '$HOME_DIR/data/mqtt_network_data'
RADIO_LOG_DIR = '$HOME_DIR/data/radio_log'
MQTT_RADIO_DIR = '$HOME_DIR/data/mqtt_radio_data'
EOL

# Create systemd service file
sudo bash -c "cat <<EOL > /etc/systemd/system/1nce_network_monitor.service
[Unit]
Description=1NCE Network Monitor
After=network.target

[Service]
ExecStart=$HOME_DIR/venv/bin/python3 $HOME_DIR/main.py
WorkingDirectory=$HOME_DIR
StandardOutput=file:$HOME_DIR/log/main.log
StandardError=file:$HOME_DIR/log/main.log
Restart=always
User=$CURRENT_USER

[Install]
WantedBy=multi-user.target
EOL"

# Reload systemd, enable, and start the service
sudo systemctl daemon-reload
sudo systemctl enable 1nce_network_monitor.service
sudo systemctl start 1nce_network_monitor.service

echo "Installation and setup complete. The 1NCE Network Monitor service is now running."
