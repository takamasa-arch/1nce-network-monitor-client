import json
from datetime import datetime, timezone, timedelta
from ping3 import ping, exceptions
import os
import time  # 追加
from zoneinfo import ZoneInfo
import subprocess
import logging
from logging.handlers import TimedRotatingFileHandler
from config import LOG_DIR, MQTT_DIR, RADIO_LOG_DIR, MQTT_RADIO_DIR, GOOGLE_SERVER, BROKER_ADDRESS


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
            timestamp_str = file.split('_')[-1].replace('.json', '')
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
        response = send_at_command('AT+CFUN=1\r\n')
        if response and "OK" in response:
            logging.info("GSM connection activated")
        else:
            logging.error(f"Failed to activate GSM connection: {response}")
            return False

        time.sleep(5)  # 5秒の待機時間を追加

        response = send_at_command('AT+CPIN?\r\n')
        if response and "+CPIN: READY" in response:
            logging.info("SIM is ready")
        else:
            logging.error(f"SIM is not ready: {response}")
            return False

        response = send_at_command('AT+CGATT?\r\n')
        if response and "+CGATT: 1" in response:
            logging.info("PDP context is active")
        else:
            logging.error(f"PDP context is not active: {response}")
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
        response = send_at_command('AT+CFUN=0\r\n')
        if response and "OK" in response:
            logging.info("GSM connection deactivated")
        else:
            logging.error(f"Failed to deactivate GSM connection: {response}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to disconnect: {e}")

def check_status():
    tokyo_tz = ZoneInfo("Asia/Tokyo")
    timestamp = datetime.now(timezone.utc).astimezone(tokyo_tz).strftime('%Y-%m-%d-%H-%M-%S')

    logging.info("Starting network status check")

    lu_status = 1 if connect_gsm() else 0

    if lu_status == 0:
        pg_status = 0
        po_status = 0
        latency_pg = None
        latency_po = None
        logging.error("GSM connection failed, setting all status flags to 0")
    else:
        try:
            latency_pg = ping(GOOGLE_SERVER)
            pg_status = 1 if latency_pg else 0
            logging.info(f"Ping Google server status: {'Success' if pg_status else 'Failure'}, latency: {latency_pg} ms")
        except exceptions.PingError as e:
            pg_status = 0
            latency_pg = None
            logging.error(f"Ping to Google server failed: {e}")

        try:
            latency_po = ping(BROKER_ADDRESS)
            po_status = 1 if latency_po else 0
            logging.info(f"Ping OpenVPN server status: {'Success' if po_status else 'Failure'}, latency: {latency_po} ms")
        except exceptions.PingError as e:
            po_status = 0
            latency_po = None
            logging.error(f"Ping to OpenVPN server failed: {e}")

    data = {
        "ts": timestamp,
        "lu": lu_status,
        "pg": pg_status,
        "po": po_status,
    }

    save_data(data, LOG_DIR, 'status')
    logging.info("Network status data saved")

    save_data(data, MQTT_DIR, 'status')
    logging.info("MQTT status data saved")

    radio_status(RADIO_LOG_DIR, MQTT_RADIO_DIR, latency_pg, latency_po)

    delete_old_data(LOG_DIR)
    delete_old_data(MQTT_DIR)

    logging.info("Completed network status check")
    return lu_status

def radio_status(radio_log_dir, mqtt_radio_dir, latency_pg, latency_po):
    tokyo_tz = ZoneInfo("Asia/Tokyo")
    timestamp = datetime.now(timezone.utc).astimezone(tokyo_tz).strftime('%Y-%m-%d-%H-%M-%S')

    logging.info("Starting radio status check")

    at_response = send_at_command('AT+CPSI?\r\n')
    parsed_response = parse_cpsi_response(at_response)

    if parsed_response:
        data = {
            "ts": timestamp,
            **parsed_response,
            "latency_pg": latency_pg if latency_pg else None,
            "latency_po": latency_po if latency_po else None
        }

        save_data(data, radio_log_dir, 'radio_status')
        logging.info("Radio status data saved")

        save_data(data, mqtt_radio_dir, 'radio_status')
        logging.info("MQTT radio status data saved")

        delete_old_data(radio_log_dir)
        delete_old_data(mqtt_radio_dir)

    else:
        logging.error("Failed to parse radio status response")

    logging.info("Completed radio status check")
