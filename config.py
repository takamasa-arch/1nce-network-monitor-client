# config.py

import os

LOG_DIR_PATH = os.path.expanduser('log')

BROKER_ADDRESS = "VPN_IP_ADDRESS"  # MQTT BrokerのIPに置き換えてください
PORT = 1883
ICCID = "89882280xxxxxxxxx"  # 実際のICCIDに置き換えてください
TOPIC = f"devices/{ICCID}/data"
TOPIC_RADIO = f"devices/{ICCID}/radio"
GOOGLE_SERVER = '8.8.8.8'
LOG_DIR = 'data/network_log'
MQTT_DIR = 'data/mqtt_network_data'
RADIO_LOG_DIR = 'data/radio_log'
MQTT_RADIO_DIR = 'data/mqtt_radio_data'
