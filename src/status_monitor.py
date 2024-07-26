import json
from datetime import datetime, timezone, timedelta
from ping3 import ping
import os
from zoneinfo import ZoneInfo  # タイムゾーンを扱うモジュール
import subprocess
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='/var/log/mqtt_to_cloudwatch/main.log')

def save_data(data, data_dir, prefix):
    timestamp = data['ts']
    filename = os.path.join(data_dir, f"{prefix}_{timestamp}.json")
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

def get_location_info():
    try:
        result = subprocess.run(['sudo', 'mmcli', '-m', '0', '--location-get'], capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to get location info: {e}")
        return None

def get_at_response():
    try:
        result = subprocess.run(['echo -ne "AT+CPSI?\r\n" | picocom -qrx 1000 /dev/tty4GPI'], capture_output=True, text=True, shell=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to get AT response: {e}")
        return None

def check_status():
    from main import GOOGLE_SERVER, BROKER_ADDRESS, LOG_DIR, MQTT_DIR, RADIO_LOG_DIR, MQTT_RADIO_DIR

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

    # ステータスデータとして保存
    save_data(data, LOG_DIR, 'status')

    # MQTT用のデータとして保存
    save_data(data, MQTT_DIR, 'status')

    # GSM接続の切断前にラジオステータスを取得
    if lu_status == 1:
        radio_status(RADIO_LOG_DIR, MQTT_RADIO_DIR)

        # GSM接続の切断
        disconnect_gsm()

    # 古いデータの削除
    delete_old_data(LOG_DIR)
    delete_old_data(MQTT_DIR)

def radio_status(radio_log_dir, mqtt_radio_dir):
    # タイムゾーンを東京に設定
    tokyo_tz = ZoneInfo("Asia/Tokyo")
    timestamp = datetime.now(timezone.utc).astimezone(tokyo_tz).isoformat()

    # 位置情報を取得
    location_info = get_location_info()

    # ATコマンドの応答を取得
    at_response = get_at_response()

    data = {
        "ts": timestamp,
        "location_info": location_info,
        "at_response": at_response
    }

    # ラジオステータスとして保存
    save_data(data, radio_log_dir, 'radio_status')

    # MQTT用のデータとして保存
    save_data(data, mqtt_radio_dir, 'radio_status')

    # 古いデータの削除
    delete_old_data(radio_log_dir)
    delete_old_data(mqtt_radio_dir)
