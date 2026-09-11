"""
Minimal MAX30102 (heart-rate / SpO2 sensor) driver for Raspberry Pi.
Talks to the chip over I2C using smbus2.

This only implements what we need: init the sensor, and pull raw
RED/IR samples out of its internal FIFO. The actual heart-rate /
SpO2 math lives in hrcalc.py.
"""

import time
from smbus2 import SMBus

I2C_BUS = 1
MAX30102_ADDRESS = 0x57

REG_INTR_STATUS_1 = 0x00
REG_INTR_ENABLE_1 = 0x02
REG_INTR_ENABLE_2 = 0x03
REG_FIFO_WR_PTR = 0x04
REG_OVF_COUNTER = 0x05
REG_FIFO_RD_PTR = 0x06
REG_FIFO_DATA = 0x07
REG_FIFO_CONFIG = 0x08
REG_MODE_CONFIG = 0x09
REG_SPO2_CONFIG = 0x0A
REG_LED1_PA = 0x0C  # Red LED
REG_LED2_PA = 0x0D  # IR LED
REG_PART_ID = 0xFF


class MAX30102:
    def __init__(self, bus_num=I2C_BUS, address=MAX30102_ADDRESS):
        self.address = address
        self.bus = SMBus(bus_num)
        self._setup()

    def _write(self, reg, value):
        self.bus.write_byte_data(self.address, reg, value)

    def _read(self, reg):
        return self.bus.read_byte_data(self.address, reg)

    def _setup(self):
        # Reset
        self._write(REG_MODE_CONFIG, 0x40)
        time.sleep(0.1)

        self._write(REG_INTR_ENABLE_1, 0xC0)
        self._write(REG_INTR_ENABLE_2, 0x00)
        self._write(REG_FIFO_WR_PTR, 0x00)
        self._write(REG_OVF_COUNTER, 0x00)
        self._write(REG_FIFO_RD_PTR, 0x00)

        # FIFO: sample averaging = 4, rollover enabled, almost-full = 17
        self._write(REG_FIFO_CONFIG, 0x4F)
        # Mode: SpO2 mode (Red + IR)
        self._write(REG_MODE_CONFIG, 0x03)
        # SpO2 config: ADC range, 100 samples/sec, 18-bit resolution
        self._write(REG_SPO2_CONFIG, 0x27)

        # LED current (~7mA each). Increase if fingertip signal is weak.
        self._write(REG_LED1_PA, 0x24)
        self._write(REG_LED2_PA, 0x24)

    def read_fifo(self):
        """Read one RED/IR sample pair from the FIFO."""
        self._read(REG_INTR_STATUS_1)  # clear interrupt flags

        data = self.bus.read_i2c_block_data(self.address, REG_FIFO_DATA, 6)

        red = ((data[0] & 0x03) << 16) | (data[1] << 8) | data[2]
        ir = ((data[3] & 0x03) << 16) | (data[4] << 8) | data[5]
        return red, ir

    def shutdown(self):
        self._write(REG_MODE_CONFIG, 0x80)

    def close(self):
        self.bus.close()
