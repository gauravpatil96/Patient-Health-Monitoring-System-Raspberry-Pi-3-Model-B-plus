# Patient Health Monitoring System (Raspberry Pi 3 B+)

Reads a **DS18B20** (temperature) and a **MAX30102** (heart rate + SpO2)
and serves a live dashboard over the LAN — open the Pi's IP in a browser
and see that individual Pi's patient readings, auto-refreshing every second.

> Note: on a Pi 3 B+ (full Linux), sensor drivers are written in regular
> Python using the standard `smbus2` / 1-Wire kernel interfaces — that's
> what actually talks to GPIO/I2C hardware on this board. MicroPython's
> `machine` module targets microcontrollers (e.g. Pi Pico), not Linux-based
> Pi boards, so it isn't used here for the hardware access layer.

## 1. Wiring

**DS18B20** (temperature, 1-Wire):
- Data → GPIO4 (physical pin 7)
- VCC → 3.3V (pin 1), GND → GND (pin 6)
- 4.7kΩ resistor between Data and VCC (pull-up)

**MAX30102** (heart rate / SpO2, I2C):
- VIN → 3.3V, GND → GND
- SDA → GPIO2 / pin 3 (SDA1)
- SCL → GPIO3 / pin 5 (SCL1)

## 2. Enable interfaces

```bash
sudo raspi-config
```
Interface Options → enable **I2C**.

Then edit the boot config (`/boot/firmware/config.txt` on newer Raspberry Pi OS,
or `/boot/config.txt` on older versions) and add:
```
dtoverlay=w1-gpio
```
Reboot: `sudo reboot`

Verify:
```bash
i2cdetect -y 1        # should show a device at address 0x57
ls /sys/bus/w1/devices # should show a folder starting with 28-
```

## 3. Install dependencies

```bash
cd patient-monitor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 4. Run it

```bash
python3 app.py
```

Find the Pi's IP address:
```bash
hostname -I
```

From **any device on the same LAN** (phone, laptop), open:
```
http://<pi-ip-address>:5000/
```

Each Raspberry Pi on the network shows its own patient's readings this way —
just visit that Pi's IP.

## 5. (Optional) Run automatically on boot

Create `/etc/systemd/system/patient-monitor.service`:
```ini
[Unit]
Description=Patient Health Monitor
After=network.target

[Service]
WorkingDirectory=/home/pi/patient-monitor
ExecStart=/home/pi/patient-monitor/venv/bin/python3 app.py
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable patient-monitor
sudo systemctl start patient-monitor
```

## Notes / limitations

- The SpO2/heart-rate math (`hrcalc.py`) is a simplified, hobbyist-grade
  peak-detection + ratio-of-ratios estimate — good for a learning project,
  **not a medical device**.
- If no MAX30102 is wired up, the page still loads and shows "Sensor
  offline" instead of crashing.
- To monitor multiple patients, run this project on multiple Pis (one
  per patient) — each has its own IP and dashboard.
