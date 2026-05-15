# Architecture

FactoryTrace is intentionally small, but the boundaries are meant to resemble a real industrial system.

## Components

### Simulator

The simulator emits deterministic CNC-style JSON events. It creates a coherent failure scenario rather than random noise. It runs inside the backend process and is driven by the `/demo/seed`, `/live/start`, and `/live/stop` endpoints. Events flow directly into the semantic mapper without going over the network.

### Backend

The backend is a FastAPI service. It accepts events via `/events`, validates them with Pydantic, maps them to RDF triples using RDFLib, and inserts them into an embedded in-memory graph. SPARQL queries run against that same graph.

### Graph store

For this demo the graph is an embedded `rdflib.Graph` in the backend process. A `backend/app/sparql.py` module exists with a Fuseki client (`query_select`, `query_construct`, `fuseki_update_insert`) intended for swapping to an external Apache Jena Fuseki triple store in a production deployment, but it is not wired into the current runtime.

### Frontend

The frontend is a React + Vite dashboard. It calls the backend investigation endpoints and presents the root-cause trace as facts, related-part chips, and an SVG node-link diagram.

## Why deterministic simulation matters

The point is not to pretend that synthetic telemetry is real CNC telemetry. The point is to show a reproducible operational scenario:

1. a machine/tool/batch combination enters an abnormal window,
2. downstream parts fail inspection,
3. semantic traceability identifies shared causal context.

## Concurrency

The live simulator runs in a background thread that writes events into the shared graph while HTTP handlers read from it. All access to the graph, the recent-events buffer, the tool-operation counter, and the timeline snapshots is guarded by a single `threading.RLock`. RDFLib's default in-memory store is not documented as safe for concurrent read-during-write, so this lock is required, not optional.

## Security posture

This is a demo, not a hardened service. CORS is restricted to localhost dev origins. Part IDs and other identifiers that get interpolated into SPARQL strings are sanitised against a strict character class before query execution. SPARQL injection would still be possible if a future code path widened that allow-list — production code should use parameterised SPARQL with `initBindings` instead of string interpolation.
