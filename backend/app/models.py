from typing import Optional
from pydantic import BaseModel

class FactoryEvent(BaseModel):
    event_id: str
    event_type: str
    timestamp: str
    machine_id: Optional[str] = None
    part_id: Optional[str] = None
    tool_id: Optional[str] = None
    material_batch_id: Optional[str] = None
    operator_id: Optional[str] = None
    work_order_id: Optional[str] = None
    production_run_id: Optional[str] = None
    shift_id: Optional[str] = None
    operation: Optional[str] = None
    spindle_speed_rpm: Optional[float] = None
    feed_rate_mm_min: Optional[float] = None
    vibration_mm_s: Optional[float] = None
    temperature_c: Optional[float] = None
    cycle_time_sec: Optional[float] = None
    axis_load_x_pct: Optional[float] = None
    axis_load_y_pct: Optional[float] = None
    axis_load_z_pct: Optional[float] = None
    status: Optional[str] = None
    inspection_status: Optional[str] = None
    deviation_type: Optional[str] = None
