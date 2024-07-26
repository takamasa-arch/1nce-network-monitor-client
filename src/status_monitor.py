import json
from datetime import datetime, timezone, timedelta
from ping3 import ping
import os
from zoneinfo import ZoneInfo  # タイムゾーンを扱うモジュール
import subprocess
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='/var/log/mqtt_to_cloudwatch/main.log')

def save_data(data, data_dir):
    timestamp = data['ts']
    filename = os.path.join(data_dir, f"{timestamp}.json")
    with open(filename, 'w') as f:
        json.dump(data, f)

def delete_old_data(data_dir, days=7):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith('.json')]
    for file in files:
        timestamp = datetime.fromisoformat(file.replace(data_dir + '/', '').replace('.json', ''))
        if timestamp < cutoff:
            os.remove(file)

def connect_gsm():
    try:
        subprocess.run(['sudo', 'nmcli', 'con', 'up', 'id', 'myGSMConnection'], check=True)
        logging.info("Connected to GSM network")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to connect: {e}")
        return False

def disconnect_gsm():
    try:
        subprocess.run(['sudo', 'nmcli', 'con', 'down', 'id', 'myGSMConnection'], check=True)
        logging.info("Disconnected from GSM network")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to disconnect: {e}")

def check_status():
    from main import GOOGLE_SERVER, BROKER_ADDRESS, LOG_DIR, MQTT_DIR

    # タイムゾーンを東京に設定
    tokyo_tz = ZoneInfo("Asia/Tokyo")
    timestamp = datetime.now(timezone.utc).astimezone(tokyo_tz).isoformat()

    # GSM接続の確立
    lu_status = 1 if connect_gsm() else 0

    # 接続が失敗した場合、残りのステータスはすべて0
    if lu_status == 0:
        pg_status = 0
        po_status = 0
    else:
        # Googleサーバーへのpingの結果を取得
        ping_result = ping(GOOGLE_SERVER)
        pg_status = 1 if ping_result else 0

        # OpenVPN Clientサーバーへのpingの結果を取得
        ping_result = ping(BROKER_ADDRESS)
        po_status = 1 if ping_result else 0

    data = {
        "ts": timestamp,
        "lu": lu_status,  # Location update: 1 for success, 0 for failure
        "pg": pg_status,  # Ping Google server: 1 for success, 0 for failure
        "po": po_status   # Ping OpenVPN server: 1 for success, 0 for failure
    }

    # ログとして保存
    save_data(data, LOG_DIR)

    # MQTT用のデータとして保存
    save_data(data, MQTT_DIR)

    # 古いデータの削除
    delete_old_data(LOG_DIR)
    delete_old_data(MQTT_DIR)

    # GSM接続の切断
    if lu_status == 1:
        disconnect_gsm()
