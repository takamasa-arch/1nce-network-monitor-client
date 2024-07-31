from src.status_monitor import check_status
from src.mqtt_client import send_mqtt_data, send_mqtt_radio_data
import time
from datetime import datetime, timezone
import os
import logging

# ログディレクトリのパス
LOG_DIR_PATH = '/var/log/mqtt_to_cloudwatch/'

# ログディレクトリが存在しない場合に作成
if not os.path.exists(LOG_DIR_PATH):
    os.makedirs(LOG_DIR_PATH, exist_ok=True)

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='/var/log/mqtt_to_cloudwatch/main.log')

# グローバル変数
BROKER_ADDRESS = "VPN_IP_ADDRESS"  # MQTT BrokerのIPに置き換えてください
PORT = 1883
ICCID = "89882280xxxxxxxxx"  # 実際のICCIDに置き換えてください
TOPIC = f"devices/{ICCID}/data"
TOPIC_RADIO = f"devices/{ICCID}/radio"
GOOGLE_SERVER = '8.8.8.8'
LOG_DIR = 'data/log'
MQTT_DIR = 'data/mqtt_data'
RADIO_LOG_DIR = 'data/radio_log'
MQTT_RADIO_DIR = 'data/mqtt_radio_data'

def main():
    try:
        # データ保存用ディレクトリの作成
        os.makedirs(LOG_DIR, exist_ok=True)
        os.makedirs(MQTT_DIR, exist_ok=True)
        os.makedirs(RADIO_LOG_DIR, exist_ok=True)
        os.makedirs(MQTT_RADIO_DIR, exist_ok=True)

        ping_interval = 60  # 1分おき
        send_interval = 300  # 5分おき
        last_send_time = datetime.now(timezone.utc)

        while True:
            current_time = datetime.now(timezone.utc)

            # 1分ごとにステータスチェック
            try:
                check_status()
            except Exception as e:
                logging.error(f"Error in check_status: {e}")

            # 5分ごとにMQTTでデータ送信
            if (current_time - last_send_time).total_seconds() >= send_interval:
                try:
                    if send_mqtt_data() and send_mqtt_radio_data():
                        last_send_time = current_time
                except Exception as e:
                    logging.error(f"Error in sending MQTT data: {e}")

            time.sleep(ping_interval)

    except Exception as e:
        logging.critical(f"Critical error in main loop: {e}")
        raise

if __name__ == "__main__":
    main()
