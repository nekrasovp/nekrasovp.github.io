Title: AI-Native SDLC Without Losing Engineering Accountability
Author: Pavel Nekrasov
Date: 2026-07-15 12:00:00+02:00
Slug: ai-native-sdlc-engineering-accountability
URL: ai-native-sdlc-engineering-accountability.html
Save_as: ai-native-sdlc-engineering-accountability.html
Lang: en
Status: hidden
Summary: An operating model for using agents at delivery transitions while keeping ownership, evidence, exceptions, and release authority explicit.
Canonical: https://nekrasovp.ru/ai-native-sdlc-engineering-accountability.html
Site005_Material: true
Site005_Role: essay
Site005_Companion_Route: /ai-native-delivery-contract.html
Site005_Companion_Title: Use the AI-native delivery contract
Site005_Companion_Description: A reusable packet for intent, requirements, NFRs, evidence, rollout, rollback, and human-agent decision boundaries.

Coding assistants create an unusual kind of success. Code appears faster, tests are
easier to start, and routine edits stop consuming an engineer's entire afternoon. Then
the delivery system around the code becomes the bottleneck.

Product questions arrive half-answered. Review queues grow. Jira says that work is in
one state while the repository and deployment environment say something else. A change
looks complete until somebody discovers that the non-functional requirements were
never written down. The team has increased the rate at which it can produce candidate
solutions without increasing the rate at which it can make trustworthy decisions.

That is not an AI failure. It is a workflow design failure.

I use **AI-native SDLC** to mean something more demanding than giving every developer a
coding assistant. It means redesigning the delivery system so that both people and
agents can understand its contracts, perform bounded work, produce evidence, and stop
at explicit decision boundaries. The goal is not to remove accountability. The goal is
to make accountability visible enough that automation can support it.

This article describes the operating model I have found useful while introducing
agents into engineering and product workflows: automate ambiguity detection and
coordination, keep authority with named people, and treat every important state
transition as a contract.

## Faster code is not the same as faster delivery

A software delivery system is a chain of queues and decisions. Code generation is only
one part of it. Before implementation, a team has to understand the problem, choose a
scope, expose constraints, agree on interfaces, and decide what evidence will count as
done. After implementation, it has to review, integrate, release, observe, and verify
the outcome.

An agent makes the implementation queue move faster. If the surrounding queues remain
unchanged, work simply accumulates elsewhere:

- reviewers receive larger volumes of changes with weaker context;
- analysts and product managers answer questions after implementation has started;
- engineers repeat discovery because source documents disagree;
- managers reconcile Jira, documents, merge requests, and release state manually;
- QA becomes the first place where missing requirements are made explicit.

The common response is to automate more individual tasks. Generate the ticket. Generate
the design. Generate the code. Generate the tests. Generate the review. That can produce
more output while making the end-to-end system less legible.

The better first question is: **what must be true before work is allowed to change
state?**

## Map the delivery system before automating it

Start with the lifecycle the organization actually runs, not the one described in a
process presentation. Pick several recently delivered changes and reconstruct their
path from initial signal to production. For every transition, record four things:

1. What information was required?
2. Who had authority to accept the transition?
3. What evidence was created?
4. Where did the work return when the evidence was insufficient?

The resulting map is usually more valuable than an initial list of agent use cases.
It reveals hidden approval work, duplicate status updates, recurring document gaps, and
places where ownership exists only in people's memory.

A practical lifecycle can be represented as a sequence of contracts:

<figure class="article-diagram" aria-label="Delivery lifecycle with bounded agent and human roles">
<div class="article-flow"><span>Signal</span><b aria-hidden="true"></b><span>Intent</span><b aria-hidden="true"></b><span>Delivery contract</span><b aria-hidden="true"></b><span>Implementation</span><b aria-hidden="true"></b><span>Evidence</span><b aria-hidden="true"></b><span>Release</span><b aria-hidden="true"></b><span>Outcome check</span></div>
<figcaption>Agents inspect, propose, execute bounded steps, and assemble evidence. Named people own intent, exceptions, review, and release authority.</figcaption>
</figure>

The important detail is the direction of authority. Agents can inspect, propose,
execute reversible steps, and assemble evidence. Named people own outcomes, approve
exceptions, and authorize high-impact transitions.

Do not automate a transition whose inputs, owner, and failure path are still disputed.
Automation will encode the dispute, not resolve it.

## Turn requirements into a delivery contract

"Machine-readable requirements" often sounds like a demand for a perfect formal
specification. That is neither necessary nor realistic for most product work. The useful
target is more modest: make the document structured enough that another engineer—or an
agent—can identify contradictions, omissions, and unverifiable statements.

For a normal story or bounded change, the delivery contract should answer:

- **Owner:** who is accountable for the outcome and who owns the technical decision?
- **Outcome:** what user, operational, or business condition should change?
- **Scope:** what is included and explicitly excluded?
- **Functional behavior:** which observable behaviors must hold?
- **Non-functional constraints:** what matters for latency, availability, security,
  privacy, capacity, compatibility, or operability?
- **Interfaces and dependencies:** which services, schemas, events, or teams are
  involved?
- **Acceptance examples:** what concrete scenarios demonstrate success and failure?
- **Evidence:** which tests, traces, dashboards, screenshots, migration checks, or
  approvals must exist?
- **Rollout and rollback:** how will exposure be controlled and how can the change be
  reversed?
- **Decision map:** where is a human decision mandatory?

This packet is the bridge between product intent and implementation. It also gives an
agent a bounded context. Without it, a model fills missing decisions with plausible
guesses. Those guesses often look polished enough to survive until integration.

The contract should be proportional to risk. A copy change does not need an architecture
document. A payment-flow change involving multiple services does. The discipline is not
"write more." It is "make the decisions that matter explicit before their absence
becomes expensive."

A reusable version of this packet accompanies this draft in
[AI-native delivery contract template](/ai-native-delivery-contract.html).

## Give agents bounded jobs at state transitions

Agents are most useful when their responsibility has a clear input, output, and stopping
condition. State transitions provide those boundaries naturally.

### 1. Intake and discovery assistance

An agent can normalize an incoming request, locate related documents and incidents,
identify likely stakeholders, and turn vague statements into questions. It should not
decide the product outcome. Its output is a discovery brief for a human owner to accept
or revise.

### 2. Definition-of-Ready review

Before a story becomes ready, an agent can compare the PRD, functional requirements,
non-functional requirements, interface descriptions, and implementation notes. It can
flag missing owners, undefined terms, contradictory states, absent failure behavior, or
acceptance criteria that cannot be tested.

The agent should return structured findings, not silently rewrite the source material.
The owner decides whether each finding is resolved, accepted as an explicit exception,
or irrelevant.

### 3. Implementation assistance

Once the contract is accepted, an implementation agent can plan changes, modify code,
run tests, and prepare documentation within a defined repository and permission scope.
The contract gives the work a stable target; repository instructions and architecture
rules constrain how it is done.

### 4. Evidence assembly and review

A separate review role can compare the proposed change with the contract, execute the
required checks, and assemble an evidence bundle. Separating proposal from evaluation
matters. An agent should not be the sole judge of its own work, just as an engineer does
not approve their own high-risk production change.

### 5. Definition-of-Done and release checks

At completion, automation can verify that required tests passed, operational signals
exist, documentation changed, rollout instructions are present, and linked work items
reflect reality. It can block or request an exception, but a named owner authorizes a
material risk acceptance.

This pattern can be summarized as **propose, evaluate, authorize**:

| Function | Typical agent role | Human accountability |
| --- | --- | --- |
| Propose | draft, plan, implement, update | owns intent and scope |
| Evaluate | check contract, run tests, find risk | reviews evidence and unresolved risk |
| Authorize | prepare transition or approval request | approves high-impact transition or exception |

The separation is more important than the number of tools or models involved.

## Keep accountability human and auditable

"Human in the loop" is too vague to be an operating rule. A human who clicks approve on
every agent action is a bottleneck; a human who receives only a final success message is
not meaningfully in control.

Accountability needs four concrete mechanisms.

First, every outcome and material technical decision has a named human owner. "The
agent did it" is never a valid ownership statement.

Second, the workflow records evidence, not just status. A transition should link to the
contract version, change set, test results, review findings, unresolved exceptions, and
rollout decision. This makes review faster and post-incident reconstruction possible.

Third, authority is risk-adaptive. Read-only discovery, document formatting, or a
reversible Jira update can run with broad autonomy. Schema migration, access-control
change, production release, or external communication requires stronger review and
explicit authorization.

Fourth, every gate has an exception path. Real delivery systems encounter incidents,
deadlines, and incomplete information. A gate with no exception path will be bypassed.
A useful exception records the owner, rationale, expiry or follow-up date, and
compensating control. It turns bypassing the process into an auditable risk decision.

## Automate coordination work, not only coding

Some of the highest-leverage automation is deliberately unglamorous. In a
cross-functional workflow, an agent can:

- create correctly linked tasks from an accepted document;
- check required sections when an epic or story changes state;
- compare requirement documents and report inconsistencies;
- keep parent and child work-item state synchronized;
- request missing review evidence in a standard format;
- generate a current delivery digest from source systems;
- detect work marked complete while required artifacts remain open.

Saving five minutes on one Jira transition does not sound strategic. Repeating that
transition across many stories and several roles changes the economics. It also prevents
the less visible cost of stale state: managers asking for updates, engineers reloading
context, and teams making plans from contradictory systems.

This is why I prefer to treat Jira and Confluence automation as delivery-system work,
not administrative convenience. The value is not the click that disappeared. It is the
shared state that stayed trustworthy.

## Measure the system, not the agent's output

Lines generated, prompts sent, and agent sessions completed are activity metrics. They
say little about delivery performance. A useful measurement set follows work across the
whole lifecycle:

- lead time from accepted intent to verified production outcome;
- time spent waiting for clarification before implementation;
- return rate at Definition of Ready and the reasons for return;
- rework caused by requirement or interface misunderstandings;
- age of stale or contradictory workflow state;
- review queue time and reviewer effort;
- onboarding time for a new engineer or external contributor;
- escaped defects and rollback frequency;
- agent findings accepted, rejected, or overridden by humans;
- exception count, age, and closure rate.

Use a baseline before expanding automation. Otherwise every improvement discussion
turns into an argument about anecdotes. Do not set a percentage target simply because a
vendor or planning document contains one. Measure the current system, choose a small
number of outcomes, and publish the boundary of the measurement.

Watch for displacement. If implementation time falls while review time and rework rise,
the system did not become faster. It moved the queue.

## Adopt in stages

An accountability-preserving rollout can progress through four stages.

### Stage 1: Assist

Agents draft, summarize, search, and suggest. People perform every transition. This
stage builds literacy and reveals where context is missing.

### Stage 2: Review in shadow mode

Agents evaluate documents and changes, but their findings do not block work. Compare
agent findings with human decisions. Tune false positives, identify blind spots, and
learn which checks are deterministic enough to automate.

### Stage 3: Automate reversible transitions

Allow agents to create tasks, update links and state, run checks, and request evidence.
Make actions idempotent and auditable. Humans handle exceptions and high-impact approval.

### Stage 4: Redesign the workflow

Only after the earlier stages produce trustworthy evidence should the organization
remove obsolete steps, combine queues, or increase autonomy. At this point the question
is no longer "where can we add an agent?" It is "which parts of this workflow should
exist now that agents and people can share the work differently?"

Not every workflow needs Stage 4. Predictable, low-volume work may be better served by a
script or a template. High-risk or poorly understood work may remain human-led. Agentic
complexity is a cost that needs a reason.

## The practical test

Before calling a delivery process AI-native, ask:

1. Can a new team member identify the current source of truth?
2. Does each state transition have explicit inputs and a named owner?
3. Can the system distinguish a missing decision from a writing problem?
4. Does every agent action have a bounded permission scope and audit trail?
5. Is proposal separated from evaluation and authorization where risk requires it?
6. Can a reviewer inspect the evidence without reconstructing the whole task?
7. Is there an explicit exception and rollback path?
8. Are improvements measured end to end rather than at the code-generation step?

If the answer is no, adding more autonomous agents will usually make the delivery system
faster at producing uncertainty.

AI-native engineering is not defined by how much work an agent performs. It is defined
by whether the organization can increase throughput while preserving a trustworthy
chain from intent to evidence to decision. The most important artifact is therefore not
the prompt or the generated code. It is the delivery contract that tells both people and
agents what they are doing, why it matters, who decides, and how everyone will know that
the result is safe enough to ship.
