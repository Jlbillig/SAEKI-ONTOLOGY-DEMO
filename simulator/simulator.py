import os
import time

def normalize_backend_url(url: str) -> str:
    return url.rstrip("/").removesuffix("/events")

import random
from datetime import datetime, timedelta, timezone
import requests

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000").rstrip("/")
random.seed(42)

MACHINES = ["CNC-01", "CNC-02", "CNC-03"]
TOOLS = ["TOOL-07", "TOOL-11", "TOOL-14"]
BATCHES = ["BATCH-A", "BATCH-B"]
RUN = "RUN-2026-001"
WORK_ORDER = "WO-2026-001"
SHIFT = "SHIFT-A"
START = datetime(2026, 5, 11, 8, 0, tzinfo=timezone.utc)

def ts(minutes):
    return (START + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")

def post(event):
    r = requests.post(f"{BACKEND_URL}/events", json=event, timeout=10)
    r.raise_for_status()
    return r.json()

def generate_events():
    counter = 1
    for i in range(1, 31):
        part = f"PART-{1000+i}"
        in_failure_window = 15 <= i <= 19
        near_window = 12 <= i <= 20
        machine = "CNC-02" if near_window else random.choice(MACHINES)
        tool = "TOOL-11" if near_window else random.choice(TOOLS)
        batch = "BATCH-B" if 10 <= i <= 22 else random.choice(BATCHES)
        op_min = i * 6

        yield {
            "event_id": f"EVT-{counter:05d}", "event_type": "production_start", "timestamp": ts(op_min),
            "machine_id": machine, "part_id": part, "tool_id": tool, "material_batch_id": batch,
            "operator_id": random.choice(["OP-01", "OP-02"]), "work_order_id": WORK_ORDER,
            "production_run_id": RUN, "shift_id": SHIFT, "operation": "milling", "status": "started"
        }; counter += 1

        vibration = round(random.uniform(1.3, 3.1), 2)
        temperature = round(random.uniform(61, 76), 2)
        axis_z = round(random.uniform(42, 66), 2)
        if machine == "CNC-02" and 14 <= i <= 19:
            vibration = round(random.uniform(5.6, 7.3), 2)
            temperature = round(random.uniform(80, 92), 2)
            axis_z = round(random.uniform(74, 88), 2)

        yield {
            "event_id": f"EVT-{counter:05d}", "event_type": "telemetry", "timestamp": ts(op_min+2),
            "machine_id": machine, "part_id": part, "tool_id": tool, "material_batch_id": batch,
            "operator_id": random.choice(["OP-01", "OP-02"]), "work_order_id": WORK_ORDER,
            "production_run_id": RUN, "shift_id": SHIFT, "operation": "milling",
            "spindle_speed_rpm": random.choice([7200, 8500, 9100]), "feed_rate_mm_min": random.choice([360, 420, 510]),
            "vibration_mm_s": vibration, "temperature_c": temperature, "cycle_time_sec": random.choice([118, 124, 132, 141]),
            "axis_load_x_pct": round(random.uniform(40, 64), 2), "axis_load_y_pct": round(random.uniform(43, 67), 2),
            "axis_load_z_pct": axis_z, "status": "running"
        }; counter += 1

        yield {
            "event_id": f"EVT-{counter:05d}", "event_type": "operation_complete", "timestamp": ts(op_min+4),
            "machine_id": machine, "part_id": part, "tool_id": tool, "material_batch_id": batch,
            "work_order_id": WORK_ORDER, "production_run_id": RUN, "shift_id": SHIFT, "operation": "milling", "status": "completed"
        }; counter += 1

        status = "fail" if in_failure_window else "pass"
        yield {
            "event_id": f"EVT-{counter:05d}", "event_type": "inspection_result", "timestamp": ts(op_min+6),
            "machine_id": "INSPECTION-01", "part_id": part, "production_run_id": RUN, "shift_id": SHIFT,
            "inspection_status": status,
            "deviation_type": "surface_finish_out_of_tolerance" if status == "fail" else None
        }; counter += 1

if __name__ == "__main__":
    for attempt in range(30):
        try:
            requests.get(f"{BACKEND_URL}/health", timeout=5).raise_for_status()
            break
        except Exception:
            time.sleep(2)
    sent = 0
    for event in generate_events():
        post(event)
        sent += 1
        time.sleep(0.02)
    print(f"Sent {sent} deterministic CNC events to {BACKEND_URL}")
