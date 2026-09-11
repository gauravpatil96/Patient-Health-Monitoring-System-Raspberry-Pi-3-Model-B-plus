"""
DS18B20 temperature sensor reader.
Uses the Linux kernel's built-in 1-Wire driver (w1-gpio / w1-therm),
so no extra Python library is required.

Wiring (typical): DATA -> GPIO4 (pin 7), with a 4.7k pull-up resistor
between DATA and 3.3V.

Requires, in /boot/firmware/config.txt (or /boot/config.txt on older OS):
    dtoverlay=w1-gpio
then a reboot.
"""

import glob
import time

BASE_DIR = "/sys/bus/w1/devices/"
DEVICE_FOLDER_GLOB = BASE_DIR + "28-*"


def _find_device_file():
    folders = glob.glob(DEVICE_FOLDER_GLOB)
    if not folders:
        return None
    return folders[0] + "/w1_slave"


def read_temp_c(retries=3):
    """Returns temperature in Celsius, or None if the sensor isn't found/ready."""
    device_file = _find_device_file()
    if device_file is None:
        return None

    for _ in range(retries):
        try:
            with open(device_file, "r") as f:
                lines = f.readlines()
        except OSError:
            return None

        if lines[0].strip()[-3:] != "YES":
            time.sleep(0.2)
            continue

        equals_pos = lines[1].find("t=")
        if equals_pos != -1:
            temp_string = lines[1][equals_pos + 2:]
            return round(int(temp_string) / 1000.0, 1)

    return None
