from rdflib import Graph, Namespace, RDF, Literal, XSD

FT = Namespace("https://example.org/factory-trace#")


def uri(kind: str, value: str):
    safe = str(value).replace(" ", "_").replace("/", "_").replace("-", "_")
    return FT[f"{kind}_{safe}"]


def lit(value, datatype=None):
    return Literal(value, datatype=datatype) if datatype else Literal(value)


def event_to_graph(e: dict) -> Graph:
    g = Graph()
    g.bind("ft", FT)
    event = uri("Event", e["event_id"])
    event_type = e.get("event_type")

    # --- Event type classification ---
    if event_type == "production_start":
        g.add((event, RDF.type, FT.ProductionStartEvent))
    elif event_type == "telemetry":
        g.add((event, RDF.type, FT.TelemetryEvent))
    elif event_type == "operation_complete":
        g.add((event, RDF.type, FT.OperationCompleteEvent))
    elif event_type == "inspection_result":
        g.add((event, RDF.type, FT.InspectionResult))
    elif event_type == "alarm":
        g.add((event, RDF.type, FT.AlarmEvent))
    elif event_type == "maintenance":
        g.add((event, RDF.type, FT.MaintenanceOperation))
    else:
        g.add((event, RDF.type, FT.Event))

    g.add((event, FT.eventId, lit(e["event_id"])))
    g.add((event, FT.timestampValue, lit(e["timestamp"], XSD.dateTime)))

    part = machine = tool = batch = run = operation = None

    # --- Part ---
    if e.get("part_id"):
        part = uri("Part", e["part_id"])
        g.add((part, RDF.type, FT.Part))
        g.add((part, FT.partId, lit(e["part_id"])))
        g.add((event, FT.associatedWithPart, part))

    # --- Machine ---
    if e.get("machine_id"):
        machine = uri("Machine", e["machine_id"])
        machine_class = FT.InspectionStation if "INSPECTION" in e["machine_id"] else FT.CNCMachine
        g.add((machine, RDF.type, machine_class))
        g.add((machine, FT.machineId, lit(e["machine_id"])))
        g.add((event, FT.associatedWithMachine, machine))

    # --- Tool ---
    if e.get("tool_id"):
        tool = uri("Tool", e["tool_id"])
        g.add((tool, RDF.type, FT.CuttingTool))
        g.add((tool, FT.toolId, lit(e["tool_id"])))
        g.add((event, FT.associatedWithTool, tool))

    # --- Material batch ---
    if e.get("material_batch_id") and part is not None:
        batch = uri("MaterialBatch", e["material_batch_id"])
        g.add((batch, RDF.type, FT.MaterialBatch))
        g.add((batch, FT.batchId, lit(e["material_batch_id"])))
        g.add((part, FT.processedMaterialBatch, batch))

    # --- Production run ---
    if e.get("production_run_id"):
        run = uri("ProductionRun", e["production_run_id"])
        g.add((run, RDF.type, FT.ProductionRun))

    # --- Shift ---
    if e.get("shift_id"):
        shift = uri("Shift", e["shift_id"])
        g.add((shift, RDF.type, FT.Shift))

    # --- Operator ---
    if e.get("operator_id"):
        operator = uri("Operator", e["operator_id"])
        g.add((operator, RDF.type, FT.Operator))

    # --- Work cell ---
    if e.get("work_cell_id"):
        workcell = uri("WorkCell", e["work_cell_id"])
        g.add((workcell, RDF.type, FT.WorkCell))

    # --- Manufacturing operation (milling or drilling) ---
    if event_type in {"production_start", "telemetry", "operation_complete"} and part and machine:
        operation_id = f"{e.get('production_run_id', 'RUN')}_{e.get('part_id')}_{e.get('operation', 'operation')}"
        operation = uri("Operation", operation_id)

        op_type = e.get("operation", "milling")
        if op_type == "milling":
            g.add((operation, RDF.type, FT.MillingOperation))
        elif op_type == "drilling":
            g.add((operation, RDF.type, FT.DrillingOperation))
        else:
            g.add((operation, RDF.type, FT.ManufacturingOperation))

        g.add((operation, FT.actsOnPart, part))
        g.add((operation, FT.performedByMachine, machine))
        if tool:
            g.add((operation, FT.usesTool, tool))
        if run:
            g.add((operation, FT.partOfProductionRun, run))
        if e.get("work_order_id"):
            wo = uri("WorkOrder", e["work_order_id"])
            g.add((wo, RDF.type, FT.WorkOrder))
            g.add((wo, FT.workOrderId, lit(e["work_order_id"])))
            g.add((operation, FT.hasWorkOrder, wo))

    # --- Telemetry readings + machine state ---
    if event_type == "telemetry" and machine:
        g.add((machine, FT.hasTelemetryEvent, event))
        for key, prop in [
            ("spindle_speed_rpm", FT.spindleSpeedRPM),
            ("feed_rate_mm_min", FT.feedRateMMMin),
            ("vibration_mm_s", FT.vibrationMMs),
            ("temperature_c", FT.temperatureC),
            ("cycle_time_sec", FT.cycleTimeSec),
            ("axis_load_x_pct", FT.axisLoadXPct),
            ("axis_load_y_pct", FT.axisLoadYPct),
            ("axis_load_z_pct", FT.axisLoadZPct),
        ]:
            if e.get(key) is not None:
                g.add((event, prop, lit(e[key], XSD.decimal)))

        # Derive MachineState from telemetry values
        vibration = e.get("vibration_mm_s", 0) or 0
        temperature = e.get("temperature_c", 0) or 0
        is_anomaly = float(vibration) > 5.0 or float(temperature) > 80.0

        state_id = f"{e.get('machine_id')}_{e['event_id']}_state"
        state = uri("MachineState", state_id)
        state_class = FT.AnomalyState if is_anomaly else FT.OperationalState
        g.add((state, RDF.type, state_class))
        g.add((state, RDF.type, FT.MachineState))
        g.add((event, FT.associatedWithMachine, machine))

        # AlarmEvent if anomaly thresholds exceeded
        if is_anomaly:
            alarm_id = f"ALARM_{e['event_id']}"
            alarm = uri("Event", alarm_id)
            g.add((alarm, RDF.type, FT.AlarmEvent))
            g.add((alarm, FT.eventId, lit(alarm_id)))
            g.add((alarm, FT.timestampValue, lit(e["timestamp"], XSD.dateTime)))
            g.add((alarm, FT.associatedWithMachine, machine))
            if part:
                g.add((alarm, FT.associatedWithPart, part))

    # --- Inspection result + quality deviation ---
    if event_type == "inspection_result" and part:
        g.add((part, FT.hasInspectionResult, event))
        if e.get("inspection_status"):
            g.add((event, FT.inspectionStatus, lit(e["inspection_status"])))
        if e.get("deviation_type"):
            g.add((event, FT.deviationType, lit(e["deviation_type"])))
            dev = uri("QualityDeviation", e["event_id"])
            g.add((dev, RDF.type, FT.QualityDeviation))
            g.add((dev, FT.associatedWithPart, part))
            g.add((dev, FT.deviationType, lit(e["deviation_type"])))
            g.add((dev, FT.timestampValue, lit(e["timestamp"], XSD.dateTime)))
            if machine:
                g.add((dev, FT.associatedWithMachine, machine))

    # --- Maintenance operation ---
    if event_type == "maintenance" and machine:
        maint_id = f"MAINT_{e['event_id']}"
        maint = uri("Operation", maint_id)
        g.add((maint, RDF.type, FT.MaintenanceOperation))
        g.add((maint, FT.performedByMachine, machine))
        if tool:
            g.add((maint, FT.usesTool, tool))

    if e.get("status"):
        g.add((event, FT.eventStatus, lit(e["status"])))

    return g
