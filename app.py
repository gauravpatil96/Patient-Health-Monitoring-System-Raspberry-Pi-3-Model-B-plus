"""
Patient Health Monitoring System - Raspberry Pi 3 B+
------------------------------------------------------
Reads a DS18B20 (body/skin temperature) and a MAX30102 (heart rate + SpO2)
sensor in a background thread, and serves a live-updating webpage.

Run it, then from any device on the same LAN open:
    http://<pi-ip-address>:5000/

Find the Pi's IP with:  hostname -I
"""

import threading
import time
from datetime import datetime

from flask import Flask, jsonify, render_template

import ds18b20
from hrcalc import VitalsEstimator

try:
    from max30102 import MAX30102
    HAS_MAX30102_LIB = True
except Exception:
    HAS_MAX30102_LIB = False

app = Flask(__name__)

# Shared state, updated by the background thread, read by Flask routes.
latest = {
    "temperature_c": None,
    "heart_rate_bpm": None,
    "spo2_percent": None,
    "finger_detected": False,
    "sensor_ok": False,
    "last_updated": None,
    "patient_name": "Patient 1",
    "device_id": "PI-MONITOR-01",
}
state_lock = threading.Lock()


def sensor_loop():
    sensor = None
    estimator = VitalsEstimator()
    last_temp_read = 0

    while True:
        # --- MAX30102: heart rate / SpO2 ---
        if sensor is None and HAS_MAX30102_LIB:
            try:
                sensor = MAX30102()
                print("MAX30102 initialized.")
            except Exception as e:
                print(f"MAX30102 not available yet: {e}")
                sensor = None

        if sensor is not None:
            try:
                red, ir = sensor.read_fifo()
                estimator.add_sample(red, ir)
                sensor_ok = True
            except Exception as e:
                print(f"MAX30102 read error: {e}")
                sensor = None
                sensor_ok = False
        else:
            sensor_ok = False

        # --- DS18B20: temperature (read every ~1s, it's a slow sensor) ---
        now = time.time()
        temp_c = None
        if now - last_temp_read > 1.0:
            temp_c = ds18b20.read_temp_c()
            last_temp_read = now

        with state_lock:
            if temp_c is not None:
                latest["temperature_c"] = temp_c
            latest["heart_rate_bpm"] = estimator.get_heart_rate()
            latest["spo2_percent"] = estimator.get_spo2()
            latest["finger_detected"] = estimator.finger_detected()
            latest["sensor_ok"] = sensor_ok
            latest["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        time.sleep(0.04)  # ~25 Hz, matches MAX30102 sample rate config


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/data")
def api_data():
    with state_lock:
        return jsonify(dict(latest))


if __name__ == "__main__":
    t = threading.Thread(target=sensor_loop, daemon=True)
    t.start()
    # host="0.0.0.0" is required so other devices on the LAN can reach it
    app.run(host="0.0.0.0", port=5000, debug=False)
