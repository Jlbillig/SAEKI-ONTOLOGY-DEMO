# FactoryTrace: Business Value Analysis

**Semantic Manufacturing Intelligence for CNC Quality Traceability**
*Prepared as part of the FactoryTrace portfolio project*

---

## Context

This document assesses the monetary and operational value that a semantic
traceability layer — of the kind demonstrated by FactoryTrace — can deliver
to a precision CNC manufacturing operation. It is grounded in published
industry benchmarks and is intended to support a business case conversation,
not to serve as a financial audit.

All figures are drawn from publicly available manufacturing industry research
and are cited where relevant. Conservative estimates are used throughout.

---

## Ten Ways This Creates Business Value

---

### 1. Faster Root-Cause Investigation Reduces Machine Idle Time

When a batch of parts fails inspection, a machine typically sits idle while
engineers manually trace the cause — cross-referencing telemetry logs,
tool change records, material certificates, and inspection reports that live
in separate systems.

Industry research places unplanned manufacturing downtime costs between
**$10,000 and $25,000 per hour** for mid-scale operations, and up to
**$50,000 per minute** in high-throughput environments like automotive.
Even conservative estimates put a 5-axis CNC machine at **$125–$250 per
operating hour** including depreciation, labor, and overhead.

A semantic traceability system that compresses a 2-hour manual investigation
into a 10-minute automated query saves at minimum **1.5–2 hours of machine
idle time per quality event.** Across a production floor running multiple
machines with multiple quality events per month, this compounds quickly.

**Indicative saving per event: $250–$500 in direct machine time.**

---

### 2. Early Detection of Affected Parts Reduces Scrap and Rework Cost

The "potentially affected parts" query in FactoryTrace identifies parts that
share the same machine, tool, and material batch as a failed part — before
those parts are shipped or assembled. This is containment intelligence.

Industry benchmarks from APQC show that scrap and rework costs average
**0.6% of annual revenue for top performers and 2.2% for bottom performers.**
The American Society for Quality places total cost of poor quality (COPQ)
at **5–35% of annual revenue** for manufacturers without mature quality
systems.

Catching 5 at-risk parts before they enter the supply chain rather than
discovering them as customer returns eliminates:
- Rework labor
- Premium freight for replacements
- Customer credit or warranty costs
- Reputational damage with defense or aerospace customers where
  non-conformance paperwork is mandatory

**For a company with €10M annual revenue, moving from 2.2% to 0.6% scrap
and rework rate represents €160,000 in annual savings.**

---

### 3. Reduced LLM Token Consumption for AI Agent Queries

SAEKI's stated goal is AI agents that understand manufacturing logic.
The quality of those agents depends directly on how efficiently relevant
context is retrieved and fed into the model.

Naive approaches — loading raw telemetry logs, inspection PDFs, or
unstructured event streams into an LLM context window — are extremely
token-expensive. A single shift's telemetry log can exceed 20,000 tokens.

Published research demonstrates that graph-based retrieval reduces token
consumption by **80–97% compared to naive vector RAG approaches**
(ACL 2025 workshop; TERAG framework). A targeted SPARQL query against
a knowledge graph returns precisely the triples needed to answer a question
— no irrelevant context, no repeated data.

For an AI agent running hundreds of manufacturing queries per day, this
translates directly into API cost reduction. At current LLM pricing,
an 80% token reduction on 1,000 daily queries at average context length
represents **thousands of euros per month in avoided inference cost**
at scale.

**The ontology is not just an architecture choice — it is a cost control
mechanism for AI operations.**

---

### 4. Tool Wear Pattern Recognition Extends Tool Life

The "most failure-prone tool" semantic query surfaces which cutting tools
appear most frequently in failed inspection results across production runs.
This is pattern recognition that a flat database can provide, but only if
someone knows to write the query.

In a semantic system, this insight is always one button press away and
updates in real time as new failures arrive. An operator or engineer who
sees that TOOL-11 has appeared in 14 of the last 20 failures can replace
it proactively rather than waiting for another batch of scrap.

Cutting tool costs vary widely, but the hidden cost is not the tool — it
is the scrap parts produced by a worn tool before anyone notices. Catching
tool degradation one batch earlier on a run of aerospace components can
prevent the scrapping of parts worth **tens of thousands of euros in
material and machine time.**

---

### 5. Material Batch Risk Tracking Prevents Cascading Failures

The "material batch risk" query identifies which material batches correlate
with the highest failure rates. This is critical in precision manufacturing
where batch-to-batch variation in aluminum alloy, titanium, or composite
stock can cause systematic failures that look like machine or tooling
problems until someone connects the dots.

Without semantic traceability, this connection is made slowly — or not at
all, because the data lives in purchasing systems, not on the shop floor.
A semantic layer that links `ft:MaterialBatch` to `ft:QualityDeviation`
makes this connection automatic.

Early identification of a bad batch prevents it from being used across
multiple machines and work orders, containing the damage to one production
run rather than spreading it across several.

---

### 6. Audit and Compliance Documentation is Generated Automatically

Defense and aerospace manufacturing carries strict traceability requirements.
AS9100 (aerospace quality), ITAR, and NATO supply chain standards all require
that a manufacturer can demonstrate — with documented evidence — which
machine made which part, with which tool, from which material, under what
conditions, and what the inspection result was.

Producing this documentation manually is labor-intensive and error-prone.
A knowledge graph that captures this chain automatically for every part
produced generates audit-ready traceability as a byproduct of normal
operations — not as a separate documentation effort.

The `/parts/{id}/investigation` endpoint in FactoryTrace is, in essence,
a compliance report generator. The SPARQL evidence panel shows exactly
which data was used and how the conclusion was reached — a defensible,
queryable audit trail.

**Reducing compliance documentation labor by even 10 hours per month
at engineer-level rates (€60–100/hr) saves €7,200–€12,000 per year.**

---

### 7. The Semantic Layer is the Interface for Future AI Agents

The current FactoryTrace system is a demonstration, but its architecture
is directly extensible to the autonomous agent scenario SAEKI is building
toward. An AI agent that needs to answer "should I approve this batch for
shipment?" needs access to:

- Inspection results for all parts in the batch
- Telemetry anomalies during their production
- Historical failure rates for the machine and tool used
- Any open maintenance events on the machine

All of this is already in the graph. The semantic layer does not need to
be rebuilt when the AI agent layer is added — it is the foundation the
agent reasons over. Building it correctly now avoids an expensive
re-architecture later.

This is the core argument for investing in ontology engineering before
the AI agents are built, not after.

---

### 8. Shift Handover Intelligence Reduces Human Error

Manufacturing quality incidents frequently occur at shift boundaries, when
context about an in-progress anomaly is lost between operators. The outgoing
operator knows that CNC-02 has been running hot; the incoming operator does
not.

A live semantic graph that surfaces active anomaly states, recent alarm
events, and parts currently in production with elevated telemetry flags
gives the incoming shift a structured handover brief that does not depend
on a verbal conversation happening correctly.

Human error accounts for approximately **23% of unplanned downtime** in
manufacturing. A system that reduces context loss at shift handover addresses
a meaningful slice of that figure.

---

### 9. Predictive Maintenance Signals are Embedded in the Graph

The `ft:AnomalyState` and `ft:AlarmEvent` nodes written during telemetry
ingestion are, effectively, early warning signals for machine degradation.
A machine that generates 3 alarm events in a shift is behaving differently
from one that generates zero.

Querying the graph for machines with increasing alarm frequency over time
is a basic predictive maintenance signal that does not require a separate
ML model — it is a SPARQL query over data that is already being collected.

The "machine anomaly history" query in FactoryTrace demonstrates this
directly. Extending it to trend analysis over multiple production runs
would give maintenance engineers actionable lead time before a machine
fails completely.

---

### 10. Interoperability with Industrial Standards Reduces Integration Cost

The FactoryTrace ontology is aligned with the vocabulary of industrial
standards — OPC-UA, ISA-95, MTConnect — without claiming to implement
them. This alignment means that when SAEKI integrates with a customer's
existing MES or ERP system, the semantic layer already speaks a compatible
language.

The R2RML mapping document included in this repository demonstrates how
existing relational manufacturing databases can be lifted into the knowledge
graph without replacing them. This is a significant commercial advantage:
customers do not need to replace their existing systems to benefit from
the semantic layer. They connect to it.

Integration cost is one of the largest barriers to selling manufacturing
software. A system designed for interoperability from the start reduces
the professional services cost of each customer deployment.

---

## Five Honest Limitations

---

### 1. The Value is Upstream of Proof

The business case for semantic infrastructure is strong but indirect.
FactoryTrace does not directly prevent a scrap part — it provides the
intelligence that allows a human or AI agent to intervene. The value
depends on whether that intelligence is actually acted upon. A system
that generates accurate root-cause traces that nobody reads delivers
no value. Change management and workflow integration are outside the
scope of the technical system.

---

### 2. Cold Start Problem: No Historical Data, No Pattern Recognition

The most powerful queries — batch risk, tool wear trends, machine anomaly
history — require a populated graph to be meaningful. A freshly deployed
system with one week of data cannot surface meaningful patterns. The
business value scales with data volume, which means the return on investment
is low in the early months and grows over time. This is a common challenge
for data infrastructure products and should be set as an expectation with
stakeholders.

---

### 3. Ontology Maintenance is an Ongoing Engineering Cost

An ontology is not a one-time artifact. As the factory adds new machine
types, new operation types, or new quality standards, the ontology must
be updated to reflect them. If the semantic mapper is not updated in sync,
new data will be ingested incorrectly or silently dropped. This requires
a dedicated ontology engineer — or at minimum, a developer who understands
the semantic layer — to be on staff or on retainer. For a small operation,
this is a real ongoing cost that must be budgeted.

---

### 4. SPARQL is Not Accessible to Non-Technical Users

The SPARQL evidence panel in FactoryTrace is impressive to a technical
reviewer but opaque to a production manager or shop floor operator. The
current system requires a developer to write new queries as new business
questions arise. Natural language query interfaces over knowledge graphs
are an active area of research and development, but they are not solved
problems. Until they are, the system's full value is only accessible to
users with technical training.

---

### 5. This is Not a Replacement for Existing Quality Systems

FactoryTrace is a traceability and investigation layer. It does not replace
a CMM (coordinate measuring machine), a QMS (quality management system),
an ERP, or a process control system. It augments them by connecting their
data semantically. Positioning it as a replacement would be incorrect and
would create resistance from teams who depend on those existing systems.
The correct framing is: this makes your existing systems more useful by
connecting what they already know.

---

## Summary

| Area | Conservative Annual Value |
|------|--------------------------|
| Reduced machine idle time (quality investigations) | €15,000–€60,000 |
| Scrap and rework reduction (early containment) | €80,000–€160,000 |
| LLM token cost reduction (AI agent operations) | €10,000–€50,000 |
| Compliance documentation labor | €7,000–€12,000 |
| Tool life extension (proactive replacement) | €5,000–€20,000 |
| **Conservative total** | **€117,000–€302,000** |

These figures assume a mid-scale precision CNC operation with 4–8 machines,
2–3 shifts, and an active AI agent program. They are order-of-magnitude
estimates intended to frame the conversation, not to serve as a financial
forecast.

The stronger argument is strategic: semantic infrastructure built correctly
now is the foundation that AI agents reason over later. Getting the data
layer right before the agent layer is built is significantly cheaper than
retrofitting it afterward.

---

*FactoryTrace is a portfolio demonstration project. It does not claim to
implement production-grade industrial standards such as MTConnect, OPC-UA,
ISA-95, STEP, or QIF.*
