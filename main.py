from src.status_monitor import check_status, disconnect_gsm, send_at_command
from src.mqtt_client import send_mqtt_data, send_mqtt_radio_data
from config import LOG_DIR_PATH, LOG_DIR, MQTT_DIR, RADIO_LOG_DIR, MQTT_RADIO_DIR
import time
from datetime import datetime, timezone
import os
import logging
from logging.handlers import TimedRotatingFileHandler
import subprocess  # rebootを実行するために必要

# ログディレクトリが存在しない場合に作成
if not os.path.exists(LOG_DIR_PATH):
    os.makedirs(LOG_DIR_PATH, exist_ok=True)

# ログ設定 - TimedRotatingFileHandlerを使用して7日間のログを保持
log_filename = os.path.join(LOG_DIR_PATH, 'main.log')
handler = TimedRotatingFileHandler(log_filename, when="midnight", interval=1, backupCount=7)
handler.suffix = "%Y-%m-%d"  # ログファイルの名前に日付を追加

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)

def main():
    try:
        # データ保存用ディレクトリの作成
        os.makedirs(LOG_DIR, exist_ok=True)
        os.makedirs(MQTT_DIR, exist_ok=True)
        os.makedirs(RADIO_LOG_DIR, exist_ok=True)
        os.makedirs(MQTT_RADIO_DIR, exist_ok=True)

        send_interval = 300  # 5分おき
        last_send_time = datetime.now(timezone.utc)  # タイムゾーンをUTCに統一

        # signal-setupコマンドの実行
        try:
            command = "sudo mmcli -m 0 --signal-setup=30"
            subprocess.run(command, shell=True, check=True)
            logging.info("Signal setup command executed successfully")
        except subprocess.CalledProcessError as e:
            logging.error(f"Signal setup command failed: {e}")

        while True:
            start_time = time.time()  # ループの開始時刻を記録

            current_time = datetime.now(timezone.utc)  # タイムゾーンをUTCに統一

            # 1分ごとにステータスチェック
            try:
                lu_status = check_status()
                if lu_status not in [0, 1]:
                    raise ValueError(f"Unexpected lu_status value: {lu_status}")
            except Exception as e:
                logging.error(f"Error in check_status: {e}")
                lu_status = 0  # デフォルトで0に設定

            # 5分ごとにMQTTでデータ送信
            if (current_time - last_send_time).total_seconds() >= send_interval:
                try:
                    if send_mqtt_data() and send_mqtt_radio_data():
                        last_send_time = current_time
                except Exception as e:
                    logging.error(f"Error in sending MQTT data: {e}")

            # 全ての処理が終わったら、GSM接続を切断
            disconnect_gsm()

            # ATコマンドを送信し、OKが返ってこなければ再起動
            try:
                response = send_at_command('AT\r\n')
                if not response or "OK" not in response:
                    logging.error("AT command failed, rebooting system...")
                    subprocess.run("sudo reboot now", shell=True)
            except Exception as e:
                logging.error(f"Failed to send AT command or reboot: {e}")

            # 処理にかかった時間を計算
            elapsed_time = time.time() - start_time
            remaining_time = max(60 - elapsed_time, 0)  # 60秒から経過時間を引き、残り時間を計算

            time.sleep(remaining_time)  # 残り時間だけ待機

    except Exception as e:
        logging.critical(f"Critical error in main loop: {e}")
        raise

if __name__ == "__main__":
    main()
