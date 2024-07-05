from src.status_monitor import check_status
from src.mqtt_client import send_mqtt_data
import time
from datetime import datetime, timezone

# グローバル変数
BROKER_ADDRESS = "57.181.202.135" # MQTT BrokerのIPに置き換えてください
PORT = 1883
ICCID = "8988228066605205172"  # 実際のICCIDに置き換えてください
TOPIC = f"devices/{ICCID}/data"
GOOGLE_SERVER = '8.8.8.8'
LOG_DIR = 'data/log'
MQTT_DIR = 'data/mqtt_data'

def main():
    # データ保存用ディレクトリの作成
    import os
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(MQTT_DIR, exist_ok=True)

    ping_interval = 60  # 1分おき
    send_interval = 300  # 5分おき
    last_send_time = datetime.now(timezone.utc)

    while True:
        current_time = datetime.now(timezone.utc)

        # 1分ごとにステータスチェック
        check_status()

        # 5分ごとにMQTTでデータ送信
        if (current_time - last_send_time).total_seconds() >= send_interval:
            if send_mqtt_data():
                last_send_time = current_time

        time.sleep(ping_interval)

if __name__ == "__main__":
    main()
