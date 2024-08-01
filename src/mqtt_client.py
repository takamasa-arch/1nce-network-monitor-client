import paho.mqtt.client as mqtt
import json
import os
import logging
from datetime import datetime, timezone
from main import LOG_DIR_PATH

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename=os.path.join(LOG_DIR_PATH, 'main.log'))

def load_all_data(data_dir):
    files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith('.json')]
    files.sort()
    data_list = []
    for file in files:
        with open(file, 'r') as f:
            data = json.load(f)
            data_list.append(data)
    return data_list, files

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info(f"Connected successfully with result code {rc}")
    else:
        logging.error(f"Failed to connect with result code {rc}")

def on_message(client, userdata, msg):
    logging.info(f"Message received from topic {msg.topic}: {msg.payload.decode('utf-8')}")

def on_publish(client, userdata, mid):
    logging.info(f"Message {mid} has been published.")

def send_mqtt_data():
    from main import BROKER_ADDRESS, PORT, TOPIC, MQTT_DIR

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_publish = on_publish

    try:
        client.connect(BROKER_ADDRESS, PORT, 60)
        client.loop_start()
    except Exception as e:
        logging.error(f"Failed to connect to MQTT broker: {e}")
        return False

    # ローカルに保存されたすべてのデータを読み込む
    data_list, all_files = load_all_data(MQTT_DIR)
    publish_successful = True
    for data in data_list:
        message = json.dumps(data)
        try:
            result = client.publish(TOPIC, message, qos=1)
            result.wait_for_publish()
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logging.error(f"Failed to publish message: {message}")
                publish_successful = False
        except Exception as e:
            logging.error(f"Failed to publish message: {e}")
            publish_successful = False

    # 送信が成功したファイルを削除
    if publish_successful:
        for file in all_files:
            os.remove(file)
        logging.info("All messages have been published and files deleted.")
    else:
        logging.error("Some messages failed to publish. Files not deleted.")

    # MQTTセッションを切断
    client.loop_stop()
    client.disconnect()
    logging.info("MQTT session disconnected")

    return publish_successful

def send_mqtt_radio_data():
    from main import BROKER_ADDRESS, PORT, TOPIC_RADIO, MQTT_RADIO_DIR

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_publish = on_publish

    try:
        client.connect(BROKER_ADDRESS, PORT, 60)
        client.loop_start()
    except Exception as e:
        logging.error(f"Failed to connect to MQTT broker: {e}")
        return False

    # ローカルに保存されたすべてのラジオデータを読み込む
    data_list, all_files = load_all_data(MQTT_RADIO_DIR)
    publish_successful = True
    for data in data_list:
        message = json.dumps(data)
        try:
            result = client.publish(TOPIC_RADIO, message, qos=1)
            result.wait_for_publish()
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logging.error(f"Failed to publish radio message: {message}")
                publish_successful = False
        except Exception as e:
            logging.error(f"Failed to publish radio message: {e}")
            publish_successful = False

    # 送信が成功したファイルを削除
    if publish_successful:
        for file in all_files:
            os.remove(file)
        logging.info("All radio messages have been published and files deleted.")
    else:
        logging.error("Some radio messages failed to publish. Files not deleted.")

    # MQTTセッションを切断
    client.loop_stop()
    client.disconnect()
    logging.info("MQTT session disconnected")

    return publish_successful
