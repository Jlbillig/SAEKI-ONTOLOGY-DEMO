import random
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from rdflib import Graph, RDF

from .semantic_mapper import event_to_graph, uri, FT
from .models import FactoryEvent

app = FastAPI(title="FactoryTrace API", version="0.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

graph = Graph()
recent_events: List[Dict[str, Any]] = []
live_state: Dict[str, Any] = {"running": False, "thread": None, "scenario": None}
tool_operation_counts: Dict[str, int] = {}
timeline_snapshots: List[Dict[str, Any]] = []


# ---------------------------------------------------------------------------
# Graph helpers
# ---------------------------------------------------------------------------

def load_ontology() -> None:
    ontology_path = Path("ontology/factory_trace_ontology.ttl")
    if ontology_path.exists():
        graph.parse(ontology_path, format="turtle")


def reset_graph() -> None:
    graph.remove((None, None, None))
    recent_events.clear()
    tool_operation_counts.clear()
    timeline_snapshots.clear()
    load_ontology()


def insert_event(event: Dict[str, Any]) -> Dict[str, Any]:
    event_graph = event_to_graph(event)
    for triple in event_graph:
        graph.add(triple)
    recent_events.insert(0, event)
    del recent_events[200:]

    # Track tool operation counts for tool life state
    if event.get("event_type") in {"operation_complete"} and event.get("tool_id"):
        tid = event["tool_id"]
        tool_operation_counts[tid] = tool_operation_counts.get(tid, 0) + 1

    # Snapshot timeline every 20 events
    if len(recent_events) % 20 == 0 or event.get("event_type") == "inspection_result":
        failed_count = sum(
            1 for e in recent_events
            if e.get("event_type") == "inspection_result"
            and e.get("inspection_status") == "fail"
        )
        timeline_snapshots.append({
            "ts": event.get("timestamp", ""),
            "triples": len(graph),
            "events": len(recent_events),
            "failures": failed_count,
        })
        del timeline_snapshots[200:]

    return {"event_id": event["event_id"], "triples_inserted": len(event_graph)}


def query_select(query: str) -> List[Dict[str, Any]]:
    results = graph.query(query)
    rows = []
    for row in results:
        item = {}
        for key, value in row.asdict().items():
            item[str(key)] = str(value)
        rows.append(item)
    return rows


def query_construct(query: str) -> str:
    result_graph = graph.query(query)
    out = Graph()
    for triple in result_graph:
        out.add(triple)
    return out.serialize(format="turtle")


def ts(start: datetime, minutes: float) -> str:
    return (start + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# Scenario generators
# ---------------------------------------------------------------------------

MACHINES = ["CNC-01", "CNC-02", "CNC-03", "CNC-04"]
TOOLS = ["TOOL-07", "TOOL-11", "TOOL-14", "TOOL-19"]
BATCHES = ["BATCH-A", "BATCH-B", "BATCH-C", "BATCH-D", "BATCH-E"]
OPERATORS = ["OP-01", "OP-02", "OP-03"]
OPERATIONS = ["milling", "drilling"]
DEVIATION_TYPES = [
    "surface_finish_out_of_tolerance",
    "dimensional_drift",
    "bore_diameter_out_of_tolerance",
    "edge_chatter_detected",
    "thermal_distortion_suspected",
]


def build_scenario() -> Dict[str, Any]:
    """
    Pick one of four distinct failure scenario shapes at random.
    Each produces a different graph topology when investigated.
    """
    scenario_type = random.choice([
        "machine_fault",       # One machine causes failures across multiple tools/batches
        "tool_wear",           # One tool causes failures across multiple machines
        "bad_batch",           # One material batch causes failures across multiple machines/tools
        "dual_cluster",        # Two simultaneous independent failure clusters
    ])

    run_number = random.randint(1000, 9999)
    run = f"RUN-2026-{run_number:04d}"
    work_order = f"WO-2026-{run_number:04d}"
    shift = random.choice(["SHIFT-A", "SHIFT-B", "SHIFT-C"])

    if scenario_type == "machine_fault":
        failure_machine = random.choice(MACHINES)
        failure_tool = random.choice(TOOLS)
        failure_batch = random.choice(BATCHES)
        failure_deviation = random.choice(DEVIATION_TYPES)
        window_start = random.randint(4, 18)
        window_end = window_start + random.randint(3, 6)
        clusters = [{
            "machine": failure_machine,
            "tool": failure_tool,
            "batch": failure_batch,
            "deviation": failure_deviation,
            "window_start": window_start,
            "window_end": window_end,
        }]

    elif scenario_type == "tool_wear":
        # Same tool, different machines — tool wear spreading failures
        failure_tool = random.choice(TOOLS)
        failure_deviation = random.choice(DEVIATION_TYPES)
        window_start = random.randint(4, 15)
        window_end = window_start + random.randint(4, 8)
        clusters = [{
            "machine": random.choice(MACHINES),
            "tool": failure_tool,
            "batch": random.choice(BATCHES),
            "deviation": failure_deviation,
            "window_start": window_start,
            "window_end": window_end,
        }]

    elif scenario_type == "bad_batch":
        # Same batch, different machines and tools
        failure_batch = random.choice(BATCHES)
        failure_deviation = random.choice(DEVIATION_TYPES)
        window_start = random.randint(6, 16)
        window_end = window_start + random.randint(4, 7)
        clusters = [{
            "machine": random.choice(MACHINES),
            "tool": random.choice(TOOLS),
            "batch": failure_batch,
            "deviation": failure_deviation,
            "window_start": window_start,
            "window_end": window_end,
        }]

    else:  # dual_cluster
        # Two independent failure clusters with different causes
        w1_start = random.randint(3, 12)
        w2_start = random.randint(16, 22)
        clusters = [
            {
                "machine": random.choice(MACHINES),
                "tool": random.choice(TOOLS),
                "batch": random.choice(BATCHES),
                "deviation": random.choice(DEVIATION_TYPES),
                "window_start": w1_start,
                "window_end": w1_start + random.randint(2, 4),
            },
            {
                "machine": random.choice(MACHINES),
                "tool": random.choice(TOOLS),
                "batch": random.choice(BATCHES),
                "deviation": random.choice(DEVIATION_TYPES),
                "window_start": w2_start,
                "window_end": w2_start + random.randint(2, 4),
            },
        ]

    return {
        "type": scenario_type,
        "run_id": run,
        "work_order": work_order,
        "shift": shift,
        "run_number": run_number,
        "clusters": clusters,
        "part_count": 30,
    }


def in_cluster(i: int, clusters: List[Dict]) -> Optional[Dict]:
    for c in clusters:
        if c["window_start"] <= i <= c["window_end"]:
            return c
    return None


DEVIATION_SPECS = {
    "surface_finish_out_of_tolerance": {
        "label": "Surface roughness Ra",
        "unit": "µm",
        "limit": 1.6,
        "limit_label": "limit 1.6 µm Ra",
        "fail_range": (2.1, 4.8),
    },
    "dimensional_drift": {
        "label": "Dimensional deviation",
        "unit": "mm",
        "limit": 0.05,
        "limit_label": "limit ±0.05 mm",
        "fail_range": (0.06, 0.14),
    },
    "bore_diameter_out_of_tolerance": {
        "label": "Bore diameter error",
        "unit": "mm",
        "limit": 0.03,
        "limit_label": "limit +0.03 mm",
        "fail_range": (0.04, 0.12),
    },
    "edge_chatter_detected": {
        "label": "Surface waviness",
        "unit": "µm",
        "limit": 5.0,
        "limit_label": "limit 5.0 µm",
        "fail_range": (6.5, 18.0),
    },
    "thermal_distortion_suspected": {
        "label": "Thermal expansion error",
        "unit": "mm",
        "limit": 0.03,
        "limit_label": "limit 0.03 mm",
        "fail_range": (0.04, 0.09),
    },
}


def generate_deviation_measurement(deviation_type: str) -> dict:
    spec = DEVIATION_SPECS.get(deviation_type)
    if not spec:
        return {}
    lo, hi = spec["fail_range"]
    measured = round(random.uniform(lo, hi), 3)
    return {
        "deviation_measurement_label": spec["label"],
        "deviation_measured_value": measured,
        "deviation_unit": spec["unit"],
        "deviation_limit": spec["limit"],
        "deviation_limit_label": spec["limit_label"],
    }


def generate_part_events(
    i: int,
    scenario: Dict[str, Any],
    counter: int,
    start: datetime,
) -> List[Dict[str, Any]]:
    """Generate the burst of events for one part."""
    run = scenario["run_id"]
    work_order = scenario["work_order"]
    shift = scenario["shift"]
    clusters = scenario["clusters"]

    cluster = in_cluster(i, clusters)
    part = f"PART-{scenario['run_number']:04d}-{i:03d}"

    if cluster:
        machine = cluster["machine"]
        tool = cluster["tool"]
        batch = cluster["batch"]
        deviation = cluster["deviation"]
    else:
        machine = random.choice(MACHINES)
        tool = random.choice(TOOLS)
        batch = random.choice(BATCHES)
        deviation = None

    operator = random.choice(OPERATORS)
    operation = random.choice(OPERATIONS)
    op_min = i * random.choice([4, 5, 6])
    program_version = f"PGM-{scenario['run_number']:04d}-{operation[:4].upper()}-v{random.choice([1,1,1,2])}"
    events = []

    # Production start
    events.append({
        "event_id": f"EVT-{counter:06d}",
        "event_type": "production_start",
        "timestamp": ts(start, op_min),
        "machine_id": machine, "part_id": part, "tool_id": tool,
        "material_batch_id": batch, "operator_id": operator,
        "work_order_id": work_order, "production_run_id": run,
        "shift_id": shift, "operation": operation,
        "program_version": program_version,
        "status": "started",
    })
    counter += 1

    # Telemetry
    if cluster:
        vibration = round(random.uniform(5.2, 8.1), 2)
        temperature = round(random.uniform(79, 95), 2)
        axis_z = round(random.uniform(72, 91), 2)
    else:
        vibration = round(random.uniform(1.1, 3.4), 2)
        temperature = round(random.uniform(58, 77), 2)
        axis_z = round(random.uniform(40, 68), 2)

    events.append({
        "event_id": f"EVT-{counter:06d}",
        "event_type": "telemetry",
        "timestamp": ts(start, op_min + 1),
        "machine_id": machine, "part_id": part, "tool_id": tool,
        "material_batch_id": batch, "operator_id": operator,
        "work_order_id": work_order, "production_run_id": run,
        "shift_id": shift, "operation": operation,
        "spindle_speed_rpm": random.choice([6800, 7200, 8500, 9100, 9600]),
        "feed_rate_mm_min": random.choice([320, 360, 420, 510, 560]),
        "vibration_mm_s": vibration, "temperature_c": temperature,
        "cycle_time_sec": random.choice([112, 118, 124, 132, 141]),
        "axis_load_x_pct": round(random.uniform(38, 66), 2),
        "axis_load_y_pct": round(random.uniform(41, 69), 2),
        "axis_load_z_pct": axis_z, "status": "running",
    })
    counter += 1

    # Alarm if anomaly
    if cluster:
        events.append({
            "event_id": f"EVT-{counter:06d}",
            "event_type": "alarm",
            "timestamp": ts(start, op_min + 1.5),
            "machine_id": machine, "part_id": part, "tool_id": tool,
            "production_run_id": run, "shift_id": shift, "status": "alarm",
        })
        counter += 1

    # Operation complete
    events.append({
        "event_id": f"EVT-{counter:06d}",
        "event_type": "operation_complete",
        "timestamp": ts(start, op_min + 2),
        "machine_id": machine, "part_id": part, "tool_id": tool,
        "material_batch_id": batch, "work_order_id": work_order,
        "production_run_id": run, "shift_id": shift,
        "operation": operation, "status": "completed",
    })
    counter += 1

    # Inspection
    if cluster:
        inspection_status = "fail" if random.random() < 0.85 else "pass"
    else:
        inspection_status = "fail" if random.random() < 0.03 else "pass"

    events.append({
        "event_id": f"EVT-{counter:06d}",
        "event_type": "inspection_result",
        "timestamp": ts(start, op_min + 3),
        "machine_id": "INSPECTION-01", "part_id": part,
        "production_run_id": run, "shift_id": shift,
        "inspection_status": inspection_status,
        "deviation_type": deviation if inspection_status == "fail" else None,
        **(generate_deviation_measurement(deviation) if inspection_status == "fail" and deviation else {}),
    })
    counter += 1

    # Maintenance after last cluster part
    for c in clusters:
        if i == c["window_end"]:
            events.append({
                "event_id": f"EVT-{counter:06d}",
                "event_type": "maintenance",
                "timestamp": ts(start, op_min + 4),
                "machine_id": c["machine"], "tool_id": c["tool"],
                "production_run_id": run, "shift_id": shift,
                "status": "completed",
            })
            counter += 1

    return events


# ---------------------------------------------------------------------------
# Live simulation thread
# ---------------------------------------------------------------------------

def live_runner():
    while live_state["running"]:
        scenario = build_scenario()
        live_state["scenario"] = scenario
        start = datetime.now(timezone.utc)
        counter = random.randint(10000, 999999)

        for i in range(1, scenario["part_count"] + 1):
            if not live_state["running"]:
                break
            events = generate_part_events(i, scenario, counter, start)
            counter += len(events)
            # Burst: emit each event in the part's group quickly
            for event in events:
                insert_event(event)
                time.sleep(0.12)
            # Pause between parts to feel like a real cycle time
            time.sleep(random.uniform(2.5, 4.0))

        # Short pause between runs before starting the next scenario
        if live_state["running"]:
            time.sleep(5)


# ---------------------------------------------------------------------------
# Named SPARQL queries
# ---------------------------------------------------------------------------

NAMED_QUERIES = {
    "most_failure_prone_tool": {
        "label": "Most failure-prone tool",
        "description": "Which tools appear most often in failed inspection results?",
        "sparql": """
PREFIX ft: <https://example.org/factory-trace#>
SELECT ?toolId (COUNT(?part) AS ?failureCount)
WHERE {
  ?part a ft:Part ;
        ft:hasInspectionResult ?inspection .
  ?inspection ft:inspectionStatus "fail" .
  ?operation ft:actsOnPart ?part ;
             ft:usesTool ?tool .
  ?tool ft:toolId ?toolId .
}
GROUP BY ?toolId
ORDER BY DESC(?failureCount)
""",
    },
    "batch_risk": {
        "label": "Material batch risk",
        "description": "Which material batches are associated with the most failures?",
        "sparql": """
PREFIX ft: <https://example.org/factory-trace#>
SELECT ?batchId (COUNT(?part) AS ?failureCount)
WHERE {
  ?part a ft:Part ;
        ft:hasInspectionResult ?inspection ;
        ft:processedMaterialBatch ?batch .
  ?inspection ft:inspectionStatus "fail" .
  ?batch ft:batchId ?batchId .
}
GROUP BY ?batchId
ORDER BY DESC(?failureCount)
""",
    },
    "machine_anomaly_history": {
        "label": "Machine anomaly history",
        "description": "Which machines have the most alarm events recorded?",
        "sparql": """
PREFIX ft: <https://example.org/factory-trace#>
SELECT ?machineId (COUNT(?alarm) AS ?alarmCount)
WHERE {
  ?alarm a ft:AlarmEvent ;
         ft:associatedWithMachine ?machine .
  ?machine ft:machineId ?machineId .
}
GROUP BY ?machineId
ORDER BY DESC(?alarmCount)
""",
    },
    "parts_at_risk": {
        "label": "Parts at risk (anomaly, not yet failed)",
        "description": "Parts that had anomaly telemetry but have not yet failed inspection.",
        "sparql": """
PREFIX ft: <https://example.org/factory-trace#>
SELECT DISTINCT ?partId ?machineId ?toolId
WHERE {
  ?alarm a ft:AlarmEvent ;
         ft:associatedWithPart ?part ;
         ft:associatedWithMachine ?machine .
  ?part ft:partId ?partId .
  ?machine ft:machineId ?machineId .
  ?operation ft:actsOnPart ?part ;
             ft:usesTool ?tool .
  ?tool ft:toolId ?toolId .
  FILTER NOT EXISTS {
    ?part ft:hasInspectionResult ?insp .
    ?insp ft:inspectionStatus "fail" .
  }
}
ORDER BY ?partId
LIMIT 20
""",
    },
}


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.on_event("startup")
def startup():
    reset_graph()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "graph_engine": "RDFLib embedded graph",
        "triples": len(graph),
        "recent_events": len(recent_events),
        "live_running": live_state["running"],
        "live_scenario": live_state["scenario"]["type"] if live_state["scenario"] else None,
    }


@app.post("/events")
def ingest_event(event: FactoryEvent):
    result = insert_event(event.model_dump(exclude_none=True))
    return {"status": "accepted", **result}


@app.get("/events/recent")
def get_recent_events():
    return recent_events


@app.post("/live/start")
def live_start():
    if live_state["running"]:
        return {"status": "already_running"}
    reset_graph()
    live_state["running"] = True
    t = threading.Thread(target=live_runner, daemon=True)
    live_state["thread"] = t
    t.start()
    return {"status": "started"}


@app.post("/live/stop")
def live_stop():
    live_state["running"] = False
    live_state["scenario"] = None
    return {"status": "stopped"}


@app.post("/demo/reset")
def reset_demo():
    live_state["running"] = False
    live_state["scenario"] = None
    reset_graph()
    return {"status": "reset", "triples": len(graph)}


@app.post("/demo/seed")
def seed_demo():
    live_state["running"] = False
    live_state["scenario"] = None
    reset_graph()

    # Deterministic seed scenario
    random.seed(42)
    start = datetime(2026, 5, 11, 8, 0, tzinfo=timezone.utc)
    scenario = {
        "type": "machine_fault",
        "run_id": "RUN-2026-001",
        "work_order": "WO-2026-001",
        "shift": "SHIFT-A",
        "run_number": 1000,
        "part_count": 30,
        "clusters": [{
            "machine": "CNC-02",
            "tool": "TOOL-11",
            "batch": "BATCH-B",
            "deviation": "surface_finish_out_of_tolerance",
            "window_start": 15,
            "window_end": 19,
        }],
    }
    random.seed(42)
    triples = 0
    counter = 1
    for i in range(1, 31):
        events = generate_part_events(i, scenario, counter, start)
        counter += len(events)
        for event in events:
            result = insert_event(event)
            triples += result["triples_inserted"]

    return {
        "status": "seeded",
        "scenario": "CNC-02 / TOOL-11 vibration anomaly. PART-1000-015 through PART-1000-019 failed inspection.",
        "events_inserted": len(recent_events),
        "triples_inserted": triples,
        "primary_failed_part": "PART-1000-015",
        "investigation_url": "/parts/PART-1000-015/investigation",
    }


@app.get("/queries/failed-parts")
def failed_parts():
    q = Path("queries/failed_parts_by_machine.sparql").read_text()
    return query_select(q)


@app.get("/queries/named/{query_id}")
def run_named_query(query_id: str):
    if query_id not in NAMED_QUERIES:
        raise HTTPException(status_code=404, detail=f"Unknown query: {query_id}")
    q = NAMED_QUERIES[query_id]
    rows = query_select(q["sparql"])
    return {
        "query_id": query_id,
        "label": q["label"],
        "description": q["description"],
        "sparql": q["sparql"],
        "results": rows,
    }


@app.get("/queries/named")
def list_named_queries():
    return [
        {"query_id": k, "label": v["label"], "description": v["description"]}
        for k, v in NAMED_QUERIES.items()
    ]


@app.get("/parts/{part_id}/investigation")
def investigate_part(part_id: str):
    q = Path("queries/part_investigation.sparql").read_text().replace("$PART_ID", part_id)
    rows = query_select(q)

    if not rows:
        raise HTTPException(status_code=404, detail=f"No investigation data found for {part_id}")

    primary = rows[0]

    affected_query = Path("queries/affected_parts.sparql").read_text().replace("$PART_ID", part_id)
    affected_rows = query_select(affected_query)

    affected = sorted({
        r["affectedPartId"]
        for r in affected_rows
        if r.get("affectedPartId") and r.get("affectedPartId") != part_id
    })

    vibration = float(primary.get("vibration", 0) or 0)
    temperature = float(primary.get("temperature", 0) or 0)

    flags = []
    if vibration > 5.0:
        flags.append("high_vibration")
    if temperature > 80.0:
        flags.append("high_temperature")

    explanation = (
        f"{part_id} failed inspection after being processed on {primary.get('machineId')} "
        f"with {primary.get('toolId')} from material batch {primary.get('batchId')}. "
        f"Telemetry shows vibration={primary.get('vibration')} mm/s and "
        f"temperature={primary.get('temperature')} C. "
        f"{len(affected)} other failed part(s) share the same machine, tool, and material batch."
    )

    # Write RootCauseHypothesis into the live graph
    hyp = uri("RootCauseHypothesis", f"RCH_{part_id}")
    graph.add((hyp, RDF.type, FT.RootCauseHypothesis))
    graph.add((hyp, FT.associatedWithPart, uri("Part", part_id)))
    if primary.get("machineId"):
        graph.add((hyp, FT.associatedWithMachine, uri("Machine", primary["machineId"])))
    if primary.get("toolId"):
        graph.add((hyp, FT.associatedWithTool, uri("Tool", primary["toolId"])))

    # Find the raw inspection event to get deviation measurement
    deviation_measurement = None
    for e in recent_events:
        if (e.get("event_type") == "inspection_result"
                and e.get("part_id") == part_id
                and e.get("deviation_measured_value") is not None):
            deviation_measurement = {
                "label": e.get("deviation_measurement_label"),
                "measured": e.get("deviation_measured_value"),
                "unit": e.get("deviation_unit"),
                "limit": e.get("deviation_limit"),
                "limit_label": e.get("deviation_limit_label"),
            }
            break

    # Tool life state
    tool_ops = tool_operation_counts.get(primary.get("toolId", ""), 0)

    return {
        "part_id": part_id,
        "inspection_status": primary.get("inspectionStatus"),
        "deviation_type": primary.get("deviationType"),
        "deviation_measurement": deviation_measurement,
        "machine_id": primary.get("machineId"),
        "tool_id": primary.get("toolId"),
        "tool_operations_before_failure": tool_ops,
        "material_batch_id": primary.get("batchId"),
        "vibration_mm_s": primary.get("vibration"),
        "temperature_c": primary.get("temperature"),
        "telemetry_flags": flags,
        "potentially_affected_parts": affected,
        "explanation": explanation,
        "sparql_evidence": {
            "part_investigation_query": q,
            "affected_parts_query": affected_query,
        },
    }


@app.get("/parts/{part_id}/similar-failures")
def similar_failures(part_id: str):
    """
    Cross-machine reasoning: find failures with the same deviation type
    and material batch on DIFFERENT machines. This is what no MES does
    automatically — it requires semantic cross-system reasoning.
    """
    # First get the deviation type and batch for this part
    context_q = f"""
PREFIX ft: <https://example.org/factory-trace#>
SELECT ?deviationType ?batchId ?machineId
WHERE {{
  ?part ft:partId "{part_id}" ;
        ft:hasInspectionResult ?inspection ;
        ft:processedMaterialBatch ?batch .
  ?inspection ft:inspectionStatus "fail" ;
              ft:deviationType ?deviationType .
  ?batch ft:batchId ?batchId .
  ?operation ft:actsOnPart ?part ;
             ft:performedByMachine ?machine .
  ?machine ft:machineId ?machineId .
}}
LIMIT 1
"""
    ctx = query_select(context_q)
    if not ctx:
        raise HTTPException(status_code=404, detail=f"No failure data for {part_id}")

    deviation_type = ctx[0]["deviationType"]
    batch_id = ctx[0]["batchId"]
    source_machine = ctx[0]["machineId"]

    similar_q = f"""
PREFIX ft: <https://example.org/factory-trace#>
SELECT DISTINCT ?partId ?machineId ?toolId ?batchId ?deviationType
WHERE {{
  ?part a ft:Part ;
        ft:partId ?partId ;
        ft:hasInspectionResult ?inspection ;
        ft:processedMaterialBatch ?batch .
  ?inspection ft:inspectionStatus "fail" ;
              ft:deviationType ?deviationType .
  ?batch ft:batchId ?batchId .
  ?operation ft:actsOnPart ?part ;
             ft:performedByMachine ?machine ;
             ft:usesTool ?tool .
  ?machine ft:machineId ?machineId .
  ?tool ft:toolId ?toolId .
  FILTER(?partId != "{part_id}")
  FILTER(?deviationType = "{deviation_type}" || ?batchId = "{batch_id}")
}}
ORDER BY ?machineId ?partId
LIMIT 20
"""
    rows = query_select(similar_q)

    cross_machine = [r for r in rows if r.get("machineId") != source_machine]
    same_machine = [r for r in rows if r.get("machineId") == source_machine]

    return {
        "source_part": part_id,
        "source_machine": source_machine,
        "deviation_type": deviation_type,
        "batch_id": batch_id,
        "cross_machine_failures": cross_machine,
        "same_machine_failures": same_machine,
        "insight": (
            f"Found {len(cross_machine)} failure(s) with the same deviation type or batch "
            f"on different machines. This pattern suggests the root cause may be "
            f"{'material batch ' + batch_id if cross_machine else 'machine-specific'}."
        ) if rows else "No similar failures found in graph.",
    }


@app.get("/graph/timeline")
def graph_timeline():
    return {
        "snapshots": timeline_snapshots[-50:],
    }


@app.get("/graph/stats")
def graph_stats():
    classes = [
        ("TelemetryEvent", "ft:TelemetryEvent"),
        ("Part", "ft:Part"),
        ("QualityDeviation", "ft:QualityDeviation"),
        ("MillingOperation", "ft:MillingOperation"),
        ("DrillingOperation", "ft:DrillingOperation"),
        ("AlarmEvent", "ft:AlarmEvent"),
        ("AnomalyState", "ft:AnomalyState"),
        ("MaintenanceOperation", "ft:MaintenanceOperation"),
        ("InspectionResult", "ft:InspectionResult"),
        ("CNCMachine", "ft:CNCMachine"),
        ("MaterialBatch", "ft:MaterialBatch"),
        ("ProductionRun", "ft:ProductionRun"),
        ("WorkOrder", "ft:WorkOrder"),
        ("RootCauseHypothesis", "ft:RootCauseHypothesis"),
    ]
    counts = {}
    for label, cls in classes:
        q = f"PREFIX ft: <https://example.org/factory-trace#> SELECT (COUNT(?s) AS ?count) WHERE {{ ?s a {cls} . }}"
        rows = query_select(q)
        counts[label] = int(rows[0]["count"]) if rows else 0

    failed_q = """
    PREFIX ft: <https://example.org/factory-trace#>
    SELECT (COUNT(?p) AS ?count) WHERE {
        ?p a ft:Part ; ft:hasInspectionResult ?r .
        ?r ft:inspectionStatus "fail" .
    }
    """
    failed_rows = query_select(failed_q)
    counts["FailedParts"] = int(failed_rows[0]["count"]) if failed_rows else 0

    return {"total_triples": len(graph), "node_counts": counts}


@app.get("/graph/export")
def export_graph():
    q = "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }"
    return {"turtle": query_construct(q)}
