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
- `python3-venv` library <- will be installed
- `paho-mqtt` library <- will be installed
- `ping3` library <- will be installed

## Installation

1. Clone the repository:

```sh
git clone https://github.com/takamasa-arch/1nce-network-monitor-client.git
cd 1nce-network-monitor-client
chmod +x install.sh
chmod +x uninstall.sh
```

2. Run the installation script with your MQTT broker's IP address and the device ICCID:
```sh
./install.sh <BROKER_IP> <ICCID>
```

## Uninstallation
To uninstall the 1NCE Network Monitor, run the following script:
```sh
./uninstall.sh <BROKER_IP> <ICCID>
```

## File Descriptions
### main.py
- Defines global variables and configurations.
- Contains the main execution loop that:
  - Checks network status every minute.
  - Sends data to the MQTT broker every 5 minutes.

### status_monitor.py
- Contains functions to check the network status and save the results locally.
- Functions:
  - save_data(data, data_dir): Saves data to the specified directory.
  - delete_old_data(data_dir, days=7): Deletes data older than the specified number of days.
  - check_status(): Checks the network status by pinging Google and OpenVPN servers, and saves the results.

### mqtt_client.py
- Contains functions to send data to the MQTT broker.
- Functions:
  - load_recent_data(data_dir, minutes=5): Loads recent data from the specified directory.
  - on_connect(client, userdata, flags, rc): Callback function for MQTT connection.
  - on_message(client, userdata, msg): Callback function for MQTT message reception.
  - send_mqtt_data(): Sends data to the MQTT broker and deletes the sent files from the local storage.

## Logging
- Logs are saved in the log/main.log file. Ensure that the directory exists and has the appropriate permissions.
- Network status data is saved in the data/network_log directory.
- Radio status data is saved in the data/radio_log directory.
- All logs and data are managed with a 7-day rotation to ensure that only the most recent data and logs are kept.

## Additional Information
- Ensure your AWS credentials are configured correctly for the boto3 library to send logs to CloudWatch.
- Modify the logging configuration as needed for your environment.
