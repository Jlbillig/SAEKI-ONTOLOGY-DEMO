from typing import Optional
from pydantic import BaseModel, ConfigDict


class FactoryEvent(BaseModel):
    """All fields the simulator emits or the semantic mapper consumes.

    `extra="ignore"` keeps backwards compatibility for old clients but
    every field the system actually uses is now declared.
    """
    model_config = ConfigDict(extra="ignore")

    event_id: str
    event_type: str
    timestamp: str

    # Identity
    machine_id: Optional[str] = None
    part_id: Optional[str] = None
    tool_id: Optional[str] = None
    material_batch_id: Optional[str] = None
    operator_id: Optional[str] = None
    work_order_id: Optional[str] = None
    production_run_id: Optional[str] = None
    shift_id: Optional[str] = None
    work_cell_id: Optional[str] = None

    # Process
    operation: Optional[str] = None
    program_version: Optional[str] = None

    # Telemetry
    spindle_speed_rpm: Optional[float] = None
    feed_rate_mm_min: Optional[float] = None
    vibration_mm_s: Optional[float] = None
    temperature_c: Optional[float] = None
    cycle_time_sec: Optional[float] = None
    axis_load_x_pct: Optional[float] = None
    axis_load_y_pct: Optional[float] = None
    axis_load_z_pct: Optional[float] = None

    # Status
    status: Optional[str] = None
    inspection_status: Optional[str] = None

    # Deviation
    deviation_type: Optional[str] = None
    deviation_measurement_label: Optional[str] = None
    deviation_measured_value: Optional[float] = None
    deviation_unit: Optional[str] = None
    deviation_limit: Optional[float] = None
    deviation_limit_label: Optional[str] = None
