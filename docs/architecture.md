# Architecture

FactoryTrace is intentionally small, but the boundaries are meant to resemble a real industrial system.

## Components

### Simulator

The simulator emits deterministic CNC-style JSON events. It creates a coherent failure scenario rather than random noise.

### Backend

The backend receives events, validates them with Pydantic, maps them to RDF triples using RDFLib, and inserts them into Fuseki with SPARQL Update.

### Fuseki

Fuseki stores the RDF graph and answers SPARQL queries.

### Frontend

The frontend calls the backend investigation endpoints and presents the root-cause trace in a dashboard.

## Why deterministic simulation matters

The point is not to pretend that synthetic telemetry is real CNC telemetry. The point is to show a reproducible operational scenario:

1. a machine/tool/batch combination enters an abnormal window,
2. downstream parts fail inspection,
3. semantic traceability identifies shared causal context.
