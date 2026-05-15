# FactoryTrace

FactoryTrace is a dockerized semantic manufacturing intelligence prototype for one mission-critical process:

**CNC quality deviation traceability and root-cause investigation.**

The system simulates CNC production events, maps those events into RDF using an embedded RDFLib graph, and exposes a small FastAPI service and React dashboard for investigating failed parts via SPARQL.

The goal is to demonstrate how semantic infrastructure can connect machine telemetry, tools, parts, material batches, operations, and inspection results into an operational graph that supports traceability.

## Scenario

The deterministic demo scenario (`POST /demo/seed`) creates one controlled production run with a single failure window:

- `CNC-02` runs with `TOOL-11` on material `BATCH-B`
- vibration and temperature rise above normal operating thresholds
- parts `PART-1000-015` through `PART-1000-019` fail inspection
- the system traces the failure cluster through the shared machine, tool, material batch, and telemetry anomaly

A live mode (`POST /live/start`) generates a continuous stream of scenarios that rotate between four failure shapes — machine fault, tool wear, bad batch, and dual cluster — each producing a different graph topology when investigated.

## Architecture

```
Event simulator (in-process)
        ↓ events
FastAPI ingestion (with semantic mapper)
        ↓ RDF triples
RDFLib embedded in-memory graph
        ↓ SPARQL query
Investigation API
        ↓ JSON
React Dashboard
```

The RDF graph lives inside the FastAPI process as an embedded `rdflib.Graph`. There is no external triple store in this demo. `backend/app/sparql.py` contains a Fuseki client that is included for reference but is not wired into the runtime; swapping to a real Fuseki backend would mean replacing the in-process graph calls with calls into that module.

## Quick start

```bash
docker compose up --build
```

Then open:

```
Frontend: http://localhost:5173
Backend:  http://localhost:8000
API docs: http://localhost:8000/docs
```

The simulator runs inside the backend process. To populate the graph:

```bash
# Deterministic scripted scenario (5 failed parts, identical every run)
curl -X POST http://localhost:8000/demo/seed

# Continuous live simulation (rotates through scenario shapes)
curl -X POST http://localhost:8000/live/start
curl -X POST http://localhost:8000/live/stop

# Wipe the graph
curl -X POST http://localhost:8000/demo/reset
```

## API highlights

```
GET  /health
POST /events
GET  /events/recent
POST /demo/seed
POST /demo/reset
POST /live/start
POST /live/stop
GET  /parts/{part_id}/investigation
GET  /parts/{part_id}/similar-failures
GET  /queries/failed-parts
GET  /queries/named
GET  /queries/named/{query_id}
GET  /graph/stats
GET  /graph/timeline
GET  /graph/export
```

`/graph/stats` returns a breakdown of the live RDF graph by node type:

```json
{
  "total_triples": 1847,
  "node_counts": {
    "TelemetryEvent": 30,
    "Part": 30,
    "QualityDeviation": 5,
    "MillingOperation": 30,
    "InspectionResult": 30,
    "CNCMachine": 3,
    "MaterialBatch": 2,
    "ProductionRun": 1,
    "WorkOrder": 1,
    "FailedParts": 5
  }
}
```

The main investigation endpoint is:

```
GET /parts/PART-1000-015/investigation
```

It returns the failed part, inspection result, machine, tool, material batch, anomaly flags, related failed parts, the SPARQL evidence used, and a natural-language explanation.

## CNC simulation

The simulator generates deterministic synthetic events. It does not use live machine data. The fields are chosen to resemble common CNC operational concepts:

- spindle speed
- feed rate
- vibration
- temperature
- cycle time
- axis load
- tool id
- machine id
- part id
- material batch id
- inspection result

This makes the project reproducible and reviewable while demonstrating the operational logic of a CNC traceability system.

## Ontology terms

The ontology is in:

```
ontology/factory_trace_ontology.ttl
```

A CSV controlled vocabulary is in:

```
data/ontology_terms.csv
```

An R2RML mapping describing how a relational MES/ERP schema would lift into this ontology is in:

```
ontology/r2rml_mapping.ttl
```

The R2RML mapping is reference documentation for a hypothetical SAEKI deployment — it is not executed at runtime.
