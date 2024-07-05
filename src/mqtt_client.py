import paho.mqtt.client as mqtt
import json
import os
import logging
from datetime import datetime, timezone, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_recent_data(data_dir, minutes=5):
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith('.json')]
    recent_files = [f for f in files if datetime.fromisoformat(f.replace(data_dir + '/', '').replace('.json', '')) >= cutoff]
    recent_files.sort()
    data_list = []
    for file in recent_files:
        with open(file, 'r') as f:
            data = json.load(f)
            data_list.append(data)
    return data_list, recent_files

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info(f"Connected successfully with result code {rc}")
    else:
        logging.error(f"Failed to connect with result code {rc}")

def on_message(client, userdata, msg):
    logging.info(f"Message received from topic {msg.topic}: {msg.payload.decode('utf-8')}")

def send_mqtt_data():
    from main import BROKER_ADDRESS, PORT, TOPIC, MQTT_DIR

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER_ADDRESS, PORT, 60)
        client.loop_start()
    except Exception as e:
        logging.error(f"Failed to connect to MQTT broker: {e}")
        return False

    # ローカルに保存された過去5分間のデータを読み込む
    data_list, recent_files = load_recent_data(MQTT_DIR, minutes=5)
    for data in data_list:
        message = json.dumps(data)
        try:
            client.publish(TOPIC, message, qos=2)
            logging.info(f"Sent message: {message}")
        except Exception as e:
            logging.error(f"Failed to publish message: {e}")
            return False

    # 送信が成功したファイルを削除
    for file in recent_files:
        os.remove(file)

    return True
