import json
from datetime import datetime, timezone, timedelta
from ping3 import ping
import os
from zoneinfo import ZoneInfo  # タイムゾーンを扱うモジュール
import subprocess
import logging
from config import LOG_DIR_PATH, LOG_DIR, MQTT_DIR, RADIO_LOG_DIR, MQTT_RADIO_DIR, GOOGLE_SERVER, BROKER_ADDRESS

# ログディレクトリが存在しない場合に作成
if not os.path.exists(LOG_DIR_PATH):
    os.makedirs(LOG_DIR_PATH, exist_ok=True)

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename=os.path.join(LOG_DIR_PATH, 'main.log'))

def save_data(data, data_dir, prefix):
    timestamp = data['ts'].replace(':', '-').replace('T', '_')  # 特殊文字を置換
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

def send_at_command(command):
    try:
        result = subprocess.run(['echo', '-ne', command, '|', 'picocom', '-qrx', '1000', '/dev/tty4GPI'], capture_output=True, text=True, shell=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to send AT command: {e}")
        return None

def parse_cpsi_response(response):
    try:
        if response:
            lines = response.splitlines()
            for line in lines:
                if line.startswith('+CPSI:'):
                    parts = line.split(',')
                    if len(parts) >= 13:
                        return {
                            "RSRQ": parts[10],
                            "RSRP": parts[11],
                            "RSSI": parts[12],
                            "SNR": parts[13]
                        }
    except Exception as e:
        logging.error(f"Failed to parse CPSI response: {e}")
    return None

def connect_gsm():
    try:
        # Activate the GSM connection using AT+CFUN=1
        response = send_at_command('AT+CFUN=1\r\n')
        if response and "OK" in response:
            logging.info("GSM connection activated")
        else:
            logging.error(f"Failed to activate GSM connection: {response}")
            return False

        # Check if the SIM is ready
        response = send_at_command('AT+CPIN?\r\n')
        if response and "+CPIN: READY" in response:
            logging.info("SIM is ready")
        else:
            logging.error(f"SIM is not ready: {response}")
            return False

        # Check if PDP context is active
        response = send_at_command('AT+CGATT?\r\n')
        if response and "+CGATT: 1" in response:
            logging.info("PDP context is active")
        else:
            logging.error(f"PDP context is not active: {response}")
            # Try to activate PDP context
            response = send_at_command('AT+CGATT=1\r\n')
            if response and "OK" in response:
                logging.info("PDP context activated")
                return True
            else:
                logging.error(f"Failed to activate PDP context: {response}")
                return False

        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to connect: {e}")
        return False

def disconnect_gsm():
    try:
        # Deactivate the GSM connection using AT+CFUN=0
        response = send_at_command('AT+CFUN=0\r\n')
        if response and "OK" in response:
            logging.info("GSM connection deactivated")
        else:
            logging.error(f"Failed to deactivate GSM connection: {response}")

    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to disconnect: {e}")

def check_status():

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

    # ATコマンドの応答を取得
    at_response = send_at_command('AT+CPSI?\r\n')
    parsed_response = parse_cpsi_response(at_response)

    if parsed_response:
        data = {
            "ts": timestamp,
            **parsed_response  # parsed_responseの内容を直接含める
        }

        # ラジオステータスとして保存
        save_data(data, radio_log_dir, 'radio_status')

        # MQTT用のデータとして保存
        save_data(data, mqtt_radio_dir, 'radio_status')

        # 古いデータの削除
        delete_old_data(radio_log_dir)
        delete_old_data(mqtt_radio_dir)
    else:
        logging.error("Failed to parse radio status response")
