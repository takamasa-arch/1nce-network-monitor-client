#!/bin/bash

# Function to display usage instructions
usage() {
  echo "Usage: $0 <BROKER_IP> <ICCID> [--skip-setup]"
  exit 1
}

# Check for required arguments
if [ "$#" -lt 2 ]; then
  usage
fi

BROKER_IP=$1
ICCID=$2
SKIP_SETUP=false

# Check for optional --skip-setup flag
if [ "$#" -eq 3 ] && [ "$3" == "--skip-setup" ]; then
  SKIP_SETUP=true
fi

HOME_DIR=$(pwd)  # スクリプトを実行した場所を使用

if [ "$SKIP_SETUP" = false ]; then
  # Install python3-venv if it's not already installed
  sudo apt update
  sudo apt install -y python3-venv

  # Create a virtual environment
  python3 -m venv $HOME_DIR/venv
  source $HOME_DIR/venv/bin/activate

  # Install the required libraries
  pip install paho-mqtt ping3
else
  # Activate the existing virtual environment
  source $HOME_DIR/venv/bin/activate
fi

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
User=$(whoami)

[Install]
WantedBy=multi-user.target
EOL"

# Reload systemd, enable, and start the service
sudo systemctl daemon-reload
sudo systemctl enable 1nce_network_monitor.service
sudo systemctl start 1nce_network_monitor.service

echo "Installation and setup complete. The 1NCE Network Monitor service is now running."
