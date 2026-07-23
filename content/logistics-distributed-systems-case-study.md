Title: Logistics and Distributed Systems: One Causal Pattern
Author: Pavel Nekrasov
Date: 2026-07-15 12:00:00+02:00
Slug: logistics-distributed-systems-case-study
URL: logistics-distributed-systems-case-study.html
Save_as: logistics-distributed-systems-case-study.html
Lang: en
Status: hidden
Summary: A sanitized side-by-side case showing how incomplete boundary contracts create late, expensive failures in physical and software systems.
Canonical: https://nekrasovp.ru/logistics-distributed-systems-case-study.html
Site005_Material: true
Site005_Role: companion
Site005_Companion_Route: /logistics-lessons-for-distributed-systems.html
Site005_Companion_Title: Read the full essay
Site005_Companion_Description: Seven lessons from logistics operations that change practical distributed-systems decisions.

**Purpose:** show where the logistics analogy changes an engineering decision rather
than serving as a metaphor.

## Scenario boundary

The physical scenario is a deliberately sanitized composite based on remote industrial
supply work. It names no customer, supplier, price, route plan, regulated item, or
contract term.

The software scenario is generic and names no employer, product, service, or internal
architecture.

## Shared causal model

<figure class="article-diagram" aria-label="Shared causal model for physical and software delivery">
<div class="article-flow"><span>Intent</span><b aria-hidden="true"></b><span>Boundary contract</span><b aria-hidden="true"></b><span>Local execution</span><b aria-hidden="true"></b><span>Handoff</span><b aria-hidden="true"></b><span>End-to-end verification</span><b aria-hidden="true"></b><span>Outcome</span></div>
<figcaption>Unresolved ambiguity enters at the contract; checkpoint evidence observes the handoff; a prepared fallback protects the outcome.</figcaption>
</figure>

The pattern:

1. Intent is underspecified.
2. A local owner accepts a plausible interpretation.
3. Every local step executes correctly against that interpretation.
4. The mismatch crosses multiple boundaries.
5. End-to-end verification discovers it late.
6. Recovery is more expensive than early clarification.

## Side-by-side case

| Stage | Remote industrial supply | Multi-service software delivery |
| --- | --- | --- |
| Intent | An operation needs a replacement assembly before a constrained delivery window. | A product flow needs a new state transition before a release window. |
| Ambiguity | The request contains a familiar description but lacks one compatibility attribute. | The story describes the happy path but leaves failure and retry semantics undefined. |
| Local contract | Procurement selects an item that matches the recorded specification. | Each service team implements a locally reasonable interpretation. |
| Local execution | Supplier, warehouse, and carrier perform their steps correctly. | Code, unit tests, and individual service contracts pass. |
| Handoff | The item moves through consolidation and long-haul transport. | The change moves through events, APIs, integration, and deployment. |
| Late discovery | The destination discovers that the item does not fit the installed system. | End-to-end testing or production reveals inconsistent state across services. |
| Immediate effect | The required equipment remains unavailable despite a completed delivery. | The user flow fails despite individually healthy services. |
| Recovery | Identify an alternative, secure capacity, repeat transport, and reconcile the original item. | Patch contracts and services, migrate or compensate state, redeploy, and reconcile in-flight work. |
| Root cause | An incomplete boundary contract was treated as sufficient. | An incomplete delivery contract was treated as ready. |

## Controls mapped to the same failure

### 1. Contract review before execution

**Physical system**

- Confirm equipment identity, compatibility attributes, destination constraints, and
  acceptance evidence before procurement.
- Assign one owner to accept ambiguity or stop the order.

**Software system**

- Confirm functional behavior, NFRs, interface semantics, retries, timeouts, and failure
  behavior before implementation.
- Assign outcome and technical owners; unresolved assumptions block readiness or become
  explicit exceptions.

### 2. Chain-of-custody evidence

**Physical system**

- Preserve order identity, item identity, custody checkpoints, timestamps, and acceptance
  documents across supplier, warehouse, carrier, and receiver.

**Software system**

- Preserve intent ID, attempt ID, trace context, state transitions, timestamps, and
  decision evidence across services and workflow tools.

### 3. Retry and duplication control

**Physical system**

- Link any replacement shipment to the original intent.
- Track both attempts and define what happens if both arrive.

**Software system**

- Use idempotency or command identity.
- Define deduplication, compensation, and reconciliation for repeated attempts.

### 4. Prepared fallback

**Physical system**

- Pre-identify alternative sources, compatible substitutes, critical spares, escalation
  contacts, and available transport options.

**Software system**

- Prepare rollback, degraded mode, manual queue, feature flag, fallback dependency, and
  the authority to activate them.

### 5. End-to-end outcome metric

**Physical system**

- Measure accepted, usable delivery by the required window—not supplier dispatch or
  warehouse throughput alone.

**Software system**

- Measure verified user or operational outcome—not merged code, deployment success, or
  service-local availability alone.

## Decision record example

### Risk

Late discovery of a cross-boundary contract mismatch.

### Leading signals

- missing compatibility or failure attributes;
- repeated clarification after work is already in progress;
- high return rate at acceptance or integration;
- local success with end-to-end failure;
- work items whose state differs between operational systems.

### Preventive decision

Require a proportional delivery contract for high-cost or hard-to-reverse work. A named
owner either resolves missing information or records a time-bound risk exception.

### Detective decision

Add checkpoints that preserve stable intent identity and evidence at each custody or
service boundary. Monitor oldest-item age and transition failures, not only volume.

### Recovery decision

Prepare at least one viable fallback and define who may activate it. Treat compensation
and reconciliation as first-class operations, not an improvised rollback.

## Reusable architecture-review questions

| Question | Physical interpretation | Software interpretation |
| --- | --- | --- |
| What promise is created at intake? | Delivery and acceptance obligation | Processing and outcome obligation |
| Where can work wait? | Supplier, warehouse, vehicle, destination | backlog, broker, worker, dependency, review |
| How old can it safely become? | Delivery window and operational need | SLA, user expectation, data validity |
| Where does ownership transfer? | Custody and acceptance checkpoints | API, event, deployment, team boundary |
| What identifies intent vs attempt? | Order vs shipment attempt | command/idempotency key vs retry |
| What buffer protects the system? | inventory, spare capacity, route option | queue, cache, replica, headroom |
| What does the buffer hide? | forecast, supplier, or capacity failure | demand, consumer, dependency, or recovery mismatch |
| What is the end-to-end outcome? | usable item accepted where needed | verified user or operational effect |
| What is the prepared alternative? | substitute, supplier, route, spare | rollback, degrade, fallback, manual path |
| Who chooses the alternative? | named operational owner | named technical/release owner |

## Use and limitations

Use this artifact to facilitate architecture reviews, incident retrospectives, or
product discovery for systems with expensive handoffs. Do not use it to claim that all
software patterns have direct physical equivalents.

The useful transfer is the causal reasoning:

- make promises explicit;
- separate intent from attempts;
- observe work across boundaries;
- size buffers against a scenario;
- optimize the whole flow;
- prepare recovery before the failure.
