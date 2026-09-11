"""
Simplified heart-rate and SpO2 estimation from MAX30102 raw samples.

NOTE: This is an educational / hobbyist-grade algorithm (peak counting +
ratio-of-ratios), NOT a medical-grade implementation. Don't use it for
real diagnosis. It works reasonably well with a still fingertip placed
flat on the sensor.
"""

import time
from collections import deque

# How many samples to keep for each calculation window
WINDOW_SIZE = 100


class VitalsEstimator:
    def __init__(self, sample_rate_hz=25):
        self.sample_rate = sample_rate_hz
        self.ir_buffer = deque(maxlen=WINDOW_SIZE)
        self.red_buffer = deque(maxlen=WINDOW_SIZE)
        self.last_beat_time = None
        self.bpm_history = deque(maxlen=5)

    def add_sample(self, red, ir):
        self.ir_buffer.append(ir)
        self.red_buffer.append(red)
        self._detect_beat(ir)

    def _detect_beat(self, ir_value):
        """Very simple threshold-crossing beat detector on the IR signal."""
        if len(self.ir_buffer) < 10:
            return

        recent = list(self.ir_buffer)[-10:]
        avg = sum(recent) / len(recent)
        threshold = avg * 1.02  # crude adaptive threshold

        now = time.time()
        if ir_value > threshold and (
            self.last_beat_time is None or now - self.last_beat_time > 0.3
        ):
            if self.last_beat_time is not None:
                interval = now - self.last_beat_time
                bpm = 60.0 / interval
                if 30 < bpm < 220:  # sane physiological range
                    self.bpm_history.append(bpm)
            self.last_beat_time = now

    def finger_detected(self):
        if not self.ir_buffer:
            return False
        return (sum(self.ir_buffer) / len(self.ir_buffer)) > 50000

    def get_heart_rate(self):
        if not self.bpm_history:
            return None
        return round(sum(self.bpm_history) / len(self.bpm_history))

    def get_spo2(self):
        """Ratio-of-ratios approximation. Returns None if signal is weak."""
        if len(self.ir_buffer) < WINDOW_SIZE or not self.finger_detected():
            return None

        ir = list(self.ir_buffer)
        red = list(self.red_buffer)

        ir_dc = sum(ir) / len(ir)
        red_dc = sum(red) / len(red)
        ir_ac = max(ir) - min(ir)
        red_ac = max(red) - min(red)

        if ir_dc == 0 or red_dc == 0 or ir_ac == 0:
            return None

        r_ratio = (red_ac / red_dc) / (ir_ac / ir_dc)
        # Common empirical approximation used in hobbyist MAX30102 projects
        spo2 = 104.0 - 17.0 * r_ratio
        spo2 = max(70.0, min(100.0, spo2))
        return round(spo2, 1)
