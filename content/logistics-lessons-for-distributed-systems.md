Title: What Running Logistics Operations Taught Me About Distributed Systems
Author: Pavel Nekrasov
Date: 2026-07-15 12:00:00+02:00
Slug: logistics-lessons-for-distributed-systems
URL: logistics-lessons-for-distributed-systems.html
Save_as: logistics-lessons-for-distributed-systems.html
Lang: en
Status: hidden
Summary: Seven operating lessons connecting queues, handoffs, retries, buffers, observability, and incident response across logistics and software.
Canonical: https://nekrasovp.ru/logistics-lessons-for-distributed-systems.html
Site005_Material: true
Site005_Role: essay
Site005_Companion_Route: /logistics-distributed-systems-case-study.html
Site005_Companion_Title: Open the side-by-side case study
Site005_Companion_Description: The same causal failure pattern mapped across remote industrial supply and a multi-service software workflow.

Before I became a software engineer, I spent years operating logistics and trading
businesses. I built sales and warehouse processes, managed financial models, coordinated
suppliers and outsourced facilities, and ran a last-mile company in Moscow that grew to
more than fifty employees at its peak. I also worked on supply chains for remote
industrial regions where a missing part was not a minor inconvenience: the next
replacement opportunity could be separated by thousands of kilometres and a long
transport window.

That background changed how I design software.

It is tempting to say that "logistics is a distributed system" and stop there. The
analogy sounds clever but is too broad to help. A warehouse is not a database, a truck
is not a message broker, and physical goods cannot be rolled back with a deployment
command.

The analogy becomes useful when it changes an operating decision. Logistics and
distributed software both force us to manage work that moves through queues, capacity
that is finite, handoffs between independent owners, incomplete information, retries
that create side effects, and failures that propagate. The useful question is not
whether two systems look similar. It is whether the same causal pattern helps us expose
risk before the system is under pressure.

Here are seven lessons I carried from physical operations into software architecture.

## 1. A queue is a promise, not a storage location

In logistics, an order waiting in a warehouse is not merely inventory. It is a promise
that capacity will appear later: picking capacity, vehicle space, a transport window,
customs processing, or receiving capacity at the destination.

A software queue makes the same promise. A message accepted by a broker implies that a
consumer will eventually have the capacity and information required to process it.

Both systems can look healthy while that promise is breaking. The warehouse still
contains the goods. The broker still contains the messages. Nothing has been lost, so a
simple availability check remains green. Meanwhile the age of the oldest order grows,
the destination deadline approaches, or downstream work becomes impossible.

This changes what I want to observe. Queue depth is not enough. I also want:

- age of the oldest item;
- arrival rate and completion rate;
- capacity by processing stage;
- time spent blocked on an external dependency;
- items that repeatedly return to the queue;
- the business deadline attached to each class of work.

The same queue length can mean routine buffering in one system and an approaching
failure in another. Time and obligation give the number meaning.

It also changes how I think about backpressure. When the destination cannot receive
more goods, continuing to dispatch vehicles creates congestion elsewhere. When a
downstream service is degraded, continuing to accept unlimited work turns a local
problem into a system-wide recovery event. Admission control is part of reliability,
not an admission of failure.

## 2. Handoffs need contracts and named owners

A complex delivery chain contains more handoffs than the customer sees: request,
specification, procurement, consolidation, warehousing, long-haul transport, local
delivery, acceptance, and sometimes installation or service.

Most disputes appear at the boundaries. Was the part number correct? Who was responsible
for packaging? When did custody transfer? Which document proves acceptance? What happens
if the receiver is unavailable?

Microservice systems have the same weakness. Teams often invest heavily inside services
while leaving the interface between them informal. A producer emits an event that is
technically valid but semantically incomplete. A consumer interprets a retry as a new
command. An API promises a status without defining when that status becomes final.

A useful handoff contract contains more than a schema:

- the owner on each side;
- the meaning of the transferred state;
- ordering and duplication expectations;
- timeouts and service boundaries;
- failure and cancellation behavior;
- evidence that the handoff completed;
- escalation when the receiver cannot accept it.

A schema tells us that a field is a string. An operating contract tells us whether the
receiver may process the same instruction twice and who acts when confirmation never
arrives.

This is also why ownership matters so much in architecture. "Platform," "backend," or
"the vendor" is not an owner. A named team or person must own the decision at the
boundary, especially during an incident.

## 3. Retries are new operations with old intent

When a shipment is delayed or appears lost, sending a replacement can protect the
customer outcome. It can also create two valid shipments moving toward the same
destination. If the original reappears, the system has not rolled back. It has doubled
the physical action.

Software retries are often treated as harmless infrastructure behavior. They are not.
A repeated request can create a second payment, send another notification, reserve the
same capacity twice, or apply a state change after the caller has stopped waiting.

The logistics habit is to separate **intent identity** from **execution attempt**. The
customer intent may be one required delivery. The system may make several transport
attempts. Every attempt needs its own state, but all attempts remain linked to the same
intent so that reconciliation is possible.

In software, that becomes an idempotency key, a command identifier, a deduplication
record, or a state machine that recognizes completed intent. It also requires an answer
to a harder question: if a repeated action cannot be prevented, how will it be
compensated?

Compensation is not rollback. Returning an extra shipment, issuing a refund, or
releasing a duplicate reservation is another operation with its own cost and failure
modes. Designing the compensation path before the incident is much cheaper than
inventing it during one.

## 4. Buffers buy resilience and hide problems

Inventory is a buffer against uncertain demand and unreliable lead time. It can keep an
operation running when a supplier or transport lane fails. It also consumes capital,
space, and attention, and it can hide poor forecasting or an unstable supplier.

Software has buffers everywhere: queues, caches, connection pools, retry budgets,
autoscaling headroom, replicas, and feature flags. They improve resilience by absorbing
variation. They also delay the moment when an underlying mismatch becomes visible.

The design question is not "should we have a buffer?" It is:

- which variation is the buffer intended to absorb?
- for how long?
- what does it cost while unused?
- what signal says the buffer is being consumed?
- what happens when it is exhausted?
- who is authorized to change it?

A larger queue may postpone rejected requests while making recovery take hours. More
inventory may protect an industrial operation while increasing the cost of obsolete
parts. The buffer must be sized against an explicit failure scenario and business
consequence.

This is one reason capacity planning should include recovery, not only normal load. A
system that processes one thousand items per minute and receives one thousand items per
minute has no capacity to drain a backlog after an outage. The nominal throughput is
sufficient; the recovery throughput is zero.

## 5. Local optimization can damage end-to-end flow

Every logistics function has a metric it can optimize. Procurement can minimize unit
price. A warehouse can maximize utilization. Transport can wait for a full vehicle.
Finance can minimize working capital. Each decision can look rational locally while the
customer's delivery becomes slower and more expensive.

Software organizations reproduce this pattern. One team maximizes feature throughput,
another protects review quality, a platform team standardizes every service, and an
operations team minimizes change. Local metrics improve while lead time and reliability
get worse.

The correction is to measure the flow across boundaries. For a physical supply chain,
that may be the time and cost from confirmed need to accepted delivery. For software, it
may be the time from accepted intent to verified production outcome.

This does not make local metrics useless. Warehouse accuracy and test coverage still
matter. It makes them subordinate to the system outcome.

A practical architecture review therefore asks not only whether a component is
well-designed, but also:

- which queue will this change create or move?
- which team receives new operational work?
- which dependency becomes part of the critical path?
- what happens to end-to-end recovery time?
- does a local simplification create a remote exception process?

Architecture is an operating model expressed in technical boundaries. If the operating
effect is invisible, the design is incomplete.

## 6. Observability is a chain of custody

When a delivery crosses several organizations and modes of transport, "shipped" is
almost useless as a status. Useful visibility comes from checkpoints: accepted,
packed, transferred, departed, arrived, received, inspected. Each checkpoint has a time,
location, owner, and evidence.

Distributed tracing serves a similar purpose. A request identifier or trace lets an
operator follow work across services and see where it waited, changed, retried, or
failed. Structured logs and business events add the meaning that infrastructure metrics
cannot provide alone.

The strongest lesson from logistics is that visibility must be designed into the
handoff. Reconstructing it later from phone calls, free-form notes, or unrelated logs is
slow and unreliable.

For a critical software workflow, I want every boundary to preserve:

- a stable correlation or intent identifier;
- the current attempt identifier;
- previous and next state;
- timestamp and responsible component;
- failure category;
- evidence or reason for an exceptional transition.

This is not logging everything. It is preserving enough chain of custody to answer:
where is the work, what is it waiting for, who owns the next action, and can it safely
continue?

## 7. Incident response is prepared optionality

A remote delivery can fail because of weather, a vehicle, a supplier, documentation, a
warehouse, or the receiving side. The operational response depends on options prepared
before the failure: alternative suppliers, spare capacity, replacement parts, a
different route, escalation contacts, or a decision about what can wait.

Software resilience is also prepared optionality. A rollback that has never been tested
is not an option. A replica in the same failure domain is not meaningful redundancy. A
runbook without authority and contact paths is documentation, not response capability.

For each critical path, I want to know:

1. What failures are plausible?
2. How will we detect each one before the customer does?
3. Which actions are reversible?
4. Which alternative path is already prepared?
5. Who can choose that path?
6. What resource limits the recovery?
7. How will we reconcile state afterward?

The answer may be a fallback service, degraded mode, manual queue, cached data, feature
flag, spare capacity, or an explicit decision to stop accepting work. Reliability does
not require pretending that every path is always available. It requires making failure
behavior deliberate.

## One causal pattern, two systems

Consider a simplified remote industrial supply case and a multi-service software
workflow.

In the physical chain, an incorrect part specification reaches procurement. The supplier
ships a valid item matching the wrong specification. The error is discovered at the
remote destination, where replacement lead time is long. The visible failure occurs at
delivery, but the causal failure happened at the first contract boundary.

In the software chain, an ambiguous requirement reaches implementation. Each service
behaves according to a locally reasonable interpretation. Integration or production
reveals that the end-to-end behavior is wrong. Again, the visible failure occurs late,
while the causal failure began at the contract boundary.

<figure class="article-diagram" aria-label="Causal chain from ambiguous intent to expensive recovery">
<div class="article-flow"><span>Ambiguous intent</span><b aria-hidden="true"></b><span>Locally accepted specification</span><b aria-hidden="true"></b><span>Correct local execution</span><b aria-hidden="true"></b><span>Cross-boundary handoff</span><b aria-hidden="true"></b><span>Late mismatch discovery</span><b aria-hidden="true"></b><span>Expensive recovery</span></div>
<figcaption>Early contract review prevents the mismatch; chain-of-custody evidence shortens discovery; prepared alternatives limit recovery cost.</figcaption>
</figure>

The response is not to make every specification enormous. It is to spend detail where
the cost of late discovery is high, validate the handoff before execution, preserve
evidence across the chain, and prepare a recovery option proportional to the risk.

The companion case study, [logistics and distributed-systems case study](/logistics-distributed-systems-case-study.html), applies the
same causal model side by side.

## Where the analogy ends

Physical and software systems are not interchangeable.

Software can often be copied at negligible marginal cost; physical goods cannot.
Software state can sometimes be replayed; time, fuel, and damaged equipment cannot.
Network latency is measured in milliseconds while a remote transport window may be
measured in weeks. Human institutions, regulation, weather, and geography dominate
physical operations in ways a service diagram can hide.

These differences make the analogy more useful, not less. They prevent us from importing
patterns mechanically. The point is to ask better questions about queues, contracts,
capacity, evidence, and recovery.

## The operating questions I now bring to architecture

My logistics experience left me with a compact checklist:

- What promise did the system make when it accepted this work?
- Which queue contains the work now, and how old can it safely become?
- Where does ownership transfer?
- Can an execution attempt be repeated without repeating the intent?
- Which buffer protects us, and which problem might it hide?
- Which local metric could damage the end-to-end outcome?
- Can we trace chain of custody across every boundary?
- Which recovery options exist before the incident begins?

These questions are useful whether the moving object is a truck part, an event, a
payment command, or a deployment.

The main lesson is not that logistics resembles distributed software. It is that both
are operational systems whose correctness emerges across boundaries. A component can do
everything right and the system can still fail. Good architecture therefore begins
with the promises between components: who owns them, how they are observed, what happens
when they are repeated, and how the organization recovers when the world refuses to
follow the happy path.
