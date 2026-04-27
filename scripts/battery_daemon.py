#!/usr/bin/env python3
import time
import json
import os
from datetime import datetime
from ina219 import INA219

SHUNT_OHMS = 0.1
MAX_EXPECTED_AMPS = 0.6
BATTERY_CAPACITY_MAH = 3400
OUTPUT_FILE = "/tmp/battery_status.json"
HISTORY_FILE = "/tmp/battery_history.json"
SAMPLE_INTERVAL = 5
SAMPLES_TO_AVERAGE = 180
CHARGING_SAMPLES = 3
HISTORY_INTERVAL = 300
LOW_BATTERY_THRESHOLD = 5

ina = INA219(SHUNT_OHMS, MAX_EXPECTED_AMPS, address=0x43, busnum=1)
ina.configure()

current_buffer = []
charging_buffer = []
last_history_write = 0

while True:
    try:
        voltage = ina.voltage()
        current = ina.current()
        power = ina.power()

        current_buffer.append(current)
        charging_buffer.append(current)

        if len(current_buffer) > SAMPLES_TO_AVERAGE:
            current_buffer.pop(0)
        if len(charging_buffer) > CHARGING_SAMPLES:
            charging_buffer.pop(0)

        avg_current = sum(current_buffer) / len(current_buffer)
        recent_current = sum(charging_buffer) / len(charging_buffer)
        percent = max(0, min(100, (voltage - 3.0) / (4.2 - 3.0) * 100))
        remaining_mah = (percent / 100) * BATTERY_CAPACITY_MAH

        if recent_current > 0:
            eta = "Charging"
            charging = True
        elif avg_current < 0:
            hours_remaining = remaining_mah / abs(avg_current)
            hours = int(abs(hours_remaining))
            minutes = int((abs(hours_remaining) - hours) * 60)
            eta = f"{hours}h {minutes}m remaining"
            charging = False
        else:
            eta = "Unknown"
            charging = False

        status = {
            "voltage": round(voltage, 2),
            "current": round(recent_current, 2),
            "power": round(power, 2),
            "percent": round(percent, 1),
            "eta": eta,
            "charging": charging
        }

        with open(OUTPUT_FILE, "w") as f:
            json.dump(status, f)

        now = time.time()
        if now - last_history_write >= HISTORY_INTERVAL:
            last_history_write = now
            try:
                with open(HISTORY_FILE, "r") as f:
                    history = json.load(f)
            except:
                history = []
            history.append({
                "time": datetime.now().strftime("%H:%M"),
                "percent": round(percent, 1)
            })
            if len(history) > 288:
                history = history[-288:]
            with open(HISTORY_FILE, "w") as f:
                json.dump(history, f)

        if percent <= LOW_BATTERY_THRESHOLD and not charging:
            os.system("sudo shutdown -h now")

    except Exception as e:
        pass

    time.sleep(SAMPLE_INTERVAL)
