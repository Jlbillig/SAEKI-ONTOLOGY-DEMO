# FactoryTrace

FactoryTrace is a dockerized semantic manufacturing intelligence prototype for one mission-critical process:

**CNC quality deviation traceability and root-cause investigation.**

The system simulates CNC production events, maps those events into RDF, stores them in an Apache Jena Fuseki knowledge graph, and exposes a small API and dashboard for investigating failed parts.

The goal is to demonstrate how semantic infrastructure can connect machine telemetry, tools, parts, material batches, operations, and inspection results into an operational graph that supports traceability.

## Scenario

A controlled production run contains one failure window:

- `CNC-02` runs with `TOOL-11`
- vibration and temperature rise above normal operating thresholds
- parts `PART-1015` through `PART-1019` fail inspection
- the system traces the failure cluster through the common machine, tool, material batch, and telemetry anomaly

## Architecture

```text
Synthetic CNC Event Simulator
        ↓ HTTP JSON events
FastAPI Ingestion API
        ↓ semantic mapping
RDF triples
        ↓ SPARQL update
Apache Jena Fuseki
        ↓ SPARQL query
Investigation API
        ↓ JSON
React Dashboard
```



## Quick start

```bash
docker compose up --build
```

Then open:

```text
Frontend: http://localhost:5173
```

To run the simulator manually after the stack is up:

```bash
docker compose run --rm simulator
```

## API highlights

```text
GET  /health
POST /events
GET  /events/recent
GET  /parts/PART-1017/investigation
GET  /queries/failed-parts
GET  /graph/stats
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

This makes the semantic layer inspectable without running the full dashboard.

The main endpoint is:

```text
GET /parts/PART-1017/investigation
```

It returns the failed part, inspection result, machine, tool, material batch, anomaly flags, related failed parts, and a report.

## CNC simulation

The simulator generates deterministic synthetic events. It does not  use live machine data. The fields are chosen to resemble common CNC operational concepts:

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

```text
ontology/factory_trace_ontology.ttl
```

A CSV controlled vocabulary is in:

```text
data/ontology_terms.csv
```

