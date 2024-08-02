import json
from datetime import datetime, timezone, timedelta
from ping3 import ping
import os
from zoneinfo import ZoneInfo  # タイムゾーンを扱うモジュール
import subprocess
import logging
from logging.handlers import TimedRotatingFileHandler
from config import LOG_DIR_PATH, LOG_DIR, MQTT_DIR, RADIO_LOG_DIR, MQTT_RADIO_DIR, GOOGLE_SERVER, BROKER_ADDRESS

# ログディレクトリが存在しない場合に作成
if not os.path.exists(LOG_DIR_PATH):
    os.makedirs(LOG_DIR_PATH, exist_ok=True)

# ログ設定 (ログローテーションを7日間に設定)
log_file = os.path.join(LOG_DIR_PATH, 'main.log')
handler = TimedRotatingFileHandler(log_file, when='midnight', interval=1, backupCount=7)
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.basicConfig(level=logging.INFO, handlers=[handler])

def save_data(data, data_dir, prefix):
    timestamp = data['ts']
    filename = os.path.join(data_dir, f"{prefix}_{timestamp}.json")
    with open(filename, 'w') as f:
        json.dump(data, f)

def delete_old_data(data_dir, days=7):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith('.json')]
    for file in files:
        try:
            # ファイル名からプレフィックスを除去し、タイムスタンプ部分を抽出
            timestamp_str = file.split('_')[-1].replace('.json', '')
            # タイムスタンプを datetime オブジェクトに変換
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d-%H-%M-%S').replace(tzinfo=timezone.utc)
            if timestamp < cutoff:
                os.remove(file)
                logging.info(f"Deleted old file: {file}")
        except ValueError as e:
            logging.error(f"Failed to parse date from filename: {file}, error: {e}")

def send_at_command(command):
    try:
        result = subprocess.run(
            f'echo -ne "{command}" | picocom -qrx 1000 /dev/tty4GPI',
            capture_output=True, text=True, shell=True, check=True
        )
        logging.info(f"AT command sent: {command.strip()}")
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
                        logging.info(f"Parsed CPSI response: {response.strip()}")
                        return {
                            "RSRQ": parts[10].strip(),
                            "RSRP": parts[11].strip(),
                            "RSSI": parts[12].strip(),
                            "SNR": parts[13].strip()
                        }
    except Exception as e:
        logging.error(f"Failed to parse CPSI response: {e}")
    return None

def connect_gsm():
    try:
        # GSM接続の確立
        response = send_at_command('AT+CFUN=1\r\n')
        if response and "OK" in response:
            logging.info("GSM connection activated")
        else:
            logging.error(f"Failed to activate GSM connection: {response}")
            return False

        # SIMの準備を確認
        response = send_at_command('AT+CPIN?\r\n')
        if response and "+CPIN: READY" in response:
            logging.info("SIM is ready")
        else:
            logging.error(f"SIM is not ready: {response}")
            return False

        # PDPコンテキストのアクティブ状態を確認
        response = send_at_command('AT+CGATT?\r\n')
        if response and "+CGATT: 1" in response:
            logging.info("PDP context is active")
        else:
            logging.error(f"PDP context is not active: {response}")
            # PDPコンテキストをアクティブにしようと試みる
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
        # GSM接続の切断
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
    timestamp = datetime.now(timezone.utc).astimezone(tokyo_tz).strftime('%Y-%m-%d-%H-%M-%S')  # タイムスタンプをファイル名に使用できる形式に変換

    logging.info("Starting network status check")

    # GSM接続の確立
    lu_status = 1 if connect_gsm() else 0

    # 接続が失敗した場合、残りのステータスはすべて0
    if lu_status == 0:
        pg_status = 0
        po_status = 0
        latency_pg = None
        latency_po = None
        logging.error("GSM connection failed, setting all status flags to 0")
    else:
        # Googleサーバーへのpingの結果を取得
        pg_status = 1 if latency_pg else 0
        logging.info(f"Ping Google server status: {'Success' if pg_status else 'Failure'}, latency: {latency_pg} ms")

        # OpenVPN Clientサーバーへのpingの結果を取得
        po_status = 1 if latency_po else 0
        logging.info(f"Ping OpenVPN server status: {'Success' if po_status else 'Failure'}, latency: {latency_po} ms")

    data = {
        "ts": timestamp,
        "lu": lu_status,  # Location update: 1 for success, 0 for failure
        "pg": pg_status,  # Ping Google server: 1 for success, 0 for failure
        "po": po_status,   # Ping OpenVPN server: 1 for success, 0 for failure
    }

    # ステータスデータとして保存
    save_data(data, LOG_DIR, 'status')
    logging.info("Network status data saved")

    # MQTT用のデータとして保存
    save_data(data, MQTT_DIR, 'status')
    logging.info("MQTT status data saved")

    # ラジオステータスを取得
    radio_status(RADIO_LOG_DIR, MQTT_RADIO_DIR)

    # 古いデータの削除
    delete_old_data(LOG_DIR)
    delete_old_data(MQTT_DIR)

    logging.info("Completed network status check")
    return lu_status  # GSM接続状態を返す

def radio_status(radio_log_dir, mqtt_radio_dir):
    # タイムゾーンを東京に設定
    tokyo_tz = ZoneInfo("Asia/Tokyo")
    timestamp = datetime.now(timezone.utc).astimezone(tokyo_tz).strftime('%Y-%m-%d-%H-%M-%S')  # タイムスタンプをファイル名に使用できる形式に変換

    logging.info("Starting radio status check")

    # ATコマンドの応答を取得
    at_response = send_at_command('AT+CPSI?\r\n')
    parsed_response = parse_cpsi_response(at_response)

    # GoogleとOpenVPNへのPingの結果を取得
    latency_pg = ping(GOOGLE_SERVER)
    latency_po = ping(BROKER_ADDRESS)

    if parsed_response:
        data = {
            "ts": timestamp,
            **parsed_response,  # parsed_responseの内容を直接含める
            "latency_pg": latency_pg if latency_pg else None,  # Google server latency
            "latency_po": latency_po if latency_po else None  # OpenVPN server latency
        }

        # ラジオステータスとして保存
        save_data(data, radio_log_dir, 'radio_status')
        logging.info("Radio status data saved")

        # MQTT用のデータとして保存
        save_data(data, mqtt_radio_dir, 'radio_status')
        logging.info("MQTT radio status data saved")

        # 古いデータの削除
        delete_old_data(radio_log_dir)
        delete_old_data(mqtt_radio_dir)

    else:
        logging.error("Failed to parse radio status response")

    logging.info("Completed radio status check")
