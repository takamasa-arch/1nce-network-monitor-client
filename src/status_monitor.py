import json
from datetime import datetime, timezone, timedelta
from ping3 import ping, errors
import os
import time
from zoneinfo import ZoneInfo
import subprocess
import logging
from logging.handlers import TimedRotatingFileHandler
from config import LOG_DIR, MQTT_DIR, RADIO_LOG_DIR, MQTT_RADIO_DIR, GOOGLE_SERVER, BROKER_ADDRESS

# Save data function
def save_data(data, data_dir, prefix):
    timestamp = data['ts']
    filename = os.path.join(data_dir, f"{prefix}_{timestamp}.json")
    with open(filename, 'w') as f:
        json.dump(data, f)

# Delete old data function
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

# Send AT command function
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

# Parse CPSI response function
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

# Get signal strength using mmcli
def get_signal_strength():
    try:
        # コマンドを1行で渡すように変更
        command = "sudo mmcli -m 0 --signal-get"
        result = subprocess.run(
            command, capture_output=True, text=True, shell=True, check=True
        )
        output = result.stdout.strip()
        logging.info(f"Signal strength retrieved: {output}")

        # Refresh rate が0秒であれば signal-setup コマンドを実行
        if 'refresh rate: 0 seconds' in output:
            try:
                command_setup = "sudo mmcli -m 0 --signal-setup=30"
                subprocess.run(command_setup, shell=True, check=True)
                logging.info("Signal setup command executed successfully")
            except subprocess.CalledProcessError as e:
                logging.error(f"Signal setup command failed: {e}")
                return None  # signal-setupが失敗した場合にはNoneを返す

        # Parse the mmcli output
        signal_data = {}
        for line in output.splitlines():
            if 'rssi:' in line:
                signal_data['rssi'] = float(line.split(':')[1].replace('dBm', '').strip())
            elif 'rsrq:' in line:
                signal_data['rsrq'] = float(line.split(':')[1].replace('dB', '').strip())
            elif 'rsrp:' in line:
                signal_data['rsrp'] = float(line.split(':')[1].replace('dBm', '').strip())
            elif 's/n:' in line:
                signal_data['snr'] = float(line.split(':')[1].replace('dB', '').strip())

        return signal_data

    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to get signal strength: {e}")
        return None


# Connect GSM function
def connect_gsm():
    try:
        response = send_at_command('AT+CFUN=1\r\n')

        time.sleep(10)  # 10秒の待機時間を追加

        response = send_at_command('AT+CPIN?\r\n')
        if response and "+CPIN: READY" in response:
            logging.info("SIM is ready")
        else:
            logging.error(f"SIM is not ready: {response}")
            return False

        response = send_at_command('AT+CGACT?\r\n')
        if response and "+CGACT: 1,1" in response:
            logging.info("PDP context is active")
            return True
        else:
            logging.error(f"Failed to activate PDP context: {response}")
            return False

    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to connect: {e}")
        return False

# Disconnect GSM function
def disconnect_gsm():
    try:
        response = send_at_command('AT+CFUN=0\r\n')
        if response and "OK" in response:
            logging.info("GSM connection deactivated")
        else:
            logging.error(f"Failed to deactivate GSM connection: {response}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to disconnect: {e}")

# Check network status function
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
            latency_pg = ping(GOOGLE_SERVER, timeout=5)
            pg_status = 1 if latency_pg else 0
            logging.info(f"Ping Google server status: {'Success' if pg_status else 'Failure'}, latency: {latency_pg} ms")
        except Exception as e:
            pg_status = 0
            latency_pg = None
            logging.error(f"Ping to Google server failed: {e}")

        try:
            latency_po = ping(BROKER_ADDRESS, timeout=5)
            po_status = 1 if latency_po else 0
            logging.info(f"Ping OpenVPN server status: {'Success' if po_status else 'Failure'}, latency: {latency_po} ms")
        except Exception as e:
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

# Check radio status function
def radio_status(radio_log_dir, mqtt_radio_dir, latency_pg, latency_po):
    tokyo_tz = ZoneInfo("Asia/Tokyo")
    timestamp = datetime.now(timezone.utc).astimezone(tokyo_tz).strftime('%Y-%m-%d-%H-%M-%S')

    logging.info("Starting radio status check")

    # Retrieve signal strength data
    signal_data = get_signal_strength()

    if signal_data:
        data = {
            "ts": timestamp,
            **signal_data,
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
