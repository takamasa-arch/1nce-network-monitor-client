# 1NCE Network Monitor

This repository contains a Python-based MQTT network monitoring system that periodically pings Google and OpenVPN servers, saves the results locally, and sends the data to an MQTT broker every 5 minutes. The system is divided into three main components:

1. `main.py`: Defines global variables and the main execution loop.
2. `status_monitor.py`: Checks the network status every minute and saves the results locally.
3. `mqtt_client.py`: Loads the recent data and sends it to the MQTT broker every 5 minutes.

## Directory Structure

.
├── main.py
├── src/
│   ├── status_monitor.py
│   └── mqtt_client.py
└── log/
│   └── main.log
└── data/
    ├── network_log
    ├── mqtt_network_data
    ├── radio_log
    └── mqtt_radio_data


## Getting Started

### Prerequisites

- Python 3.8 or later
- `paho-mqtt` library
- `ping3` library

Setting Up a Virtual Environment

Install python3-venv if it's not already installed:
```sh
sudo apt install python3-venv
```

Create a virtual environment:
```sh
python3 -m venv venv
```

Activate the virtual environment:
```sh
source venv/bin/activate
```

Install the required libraries using pip:
```sh
pip install paho-mqtt ping3
```

## Running the Application

1. Clone the repository:

```sh
git clone https://github.com/your-repository/mqtt-network-monitor.git
cd mqtt-network-monitor
```

2. Update the global variables in main.py with your specific configuration:
```python
BROKER_ADDRESS = "your_broker_address"
PORT = 1883
ICCID = "your_iccid"
GOOGLE_SERVER = '8.8.8.8'
LOG_DIR = 'data/log'
MQTT_DIR = 'data/mqtt_data'
```

3. Create a systemd service file to run the main script as a daemon. For example, create a file named mqtt_network_monitor.service in the /etc/systemd/system/ directory with the following content:

```ini
[Unit]
Description=1NCE Network Monitor
After=network.target

[Service]
ExecStart=/path/to/your/venv/bin/python3 /path/to/your/repository/main.py
WorkingDirectory=/path/to/your/repository
StandardOutput=file:/path/to/your/repository/log/main.log
StandardError=file:/path/to/your/repository/log/main.log
Restart=always
User=ubuntu

[Install]
WantedBy=multi-user.target
```

Replace /path/to/your/repository with the actual path to your cloned repository.

Reload and enable systemd to apply the new service:
```sh
sudo systemctl daemon-reload
sudo systemctl enable 1nce_network_monitor.service
sudo systemctl start 1nce_network_monitor.service
```

## File Descriptions
main.py
- Defines global variables and configurations.
- Contains the main execution loop that:
  - Checks network status every minute.
  - Sends data to the MQTT broker every 5 minutes.

status_monitor.py
- Contains functions to check the network status and save the results locally.
- Functions:
  - save_data(data, data_dir): Saves data to the specified directory.
  - delete_old_data(data_dir, days=7): Deletes data older than the specified number of days.
  - check_status(): Checks the network status by pinging Google and OpenVPN servers, and saves the results.
mqtt_client.py
- Contains functions to send data to the MQTT broker.
- Functions:
  - load_recent_data(data_dir, minutes=5): Loads recent data from the specified directory.
  - on_connect(client, userdata, flags, rc): Callback function for MQTT connection.
  - on_message(client, userdata, msg): Callback function for MQTT message reception.
  - send_mqtt_data(): Sends data to the MQTT broker and deletes the sent files from the local storage.
Logging
- Logs are saved in the /var/log/mqtt_to_cloudwatch directory. Ensure that the directory exists and has the appropriate permissions:

user and owner name should be changed with your environment

## Additional Information
- Ensure your AWS credentials are configured correctly for the boto3 library to send logs to CloudWatch.
- Modify the logging configuration as needed for your environment.
