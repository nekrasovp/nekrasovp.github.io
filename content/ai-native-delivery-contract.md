Title: AI-Native Delivery Contract Template
Author: Pavel Nekrasov
Date: 2026-07-15 12:00:00+02:00
Slug: ai-native-delivery-contract
URL: ai-native-delivery-contract.html
Save_as: ai-native-delivery-contract.html
Lang: en
Status: hidden
Summary: A lightweight, machine-reviewable contract connecting product intent, implementation, verification, release, and human accountability.
Canonical: https://nekrasovp.ru/ai-native-delivery-contract.html
Site005_Material: true
Site005_Role: companion
Site005_Companion_Route: /ai-native-sdlc-engineering-accountability.html
Site005_Companion_Title: Read the accountability model
Site005_Companion_Description: How bounded agent roles and explicit state-transition contracts improve delivery without delegating ownership.

**Purpose:** a lightweight, machine-reviewable contract connecting product intent,
implementation, verification, and release. Use the smallest subset proportional to the
risk of the change.

This template is designed for a story, feature, migration, or bounded platform change.
It is not a replacement for a PRD or ADR. Link those artifacts when they exist and use
this packet to make the current delivery decision explicit.

## Contract header

| Field | Value |
| --- | --- |
| Contract ID | stable id |
| Version | version or last-updated timestamp |
| Status | discovery / review / ready / implementation / verification / released / outcome-checked |
| Outcome owner | one named person |
| Technical owner | one named person |
| Delivery team | team |
| Risk class | low / medium / high / critical |
| Target window | date or release train |
| Linked PRD / ADR / incident | links |

## 1. Intent and outcome

### Problem or signal

What triggered the work? Link the customer signal, operational problem, incident,
regulatory need, or product hypothesis.

~~~text
<problem statement>
~~~

### Outcome hypothesis

~~~text
If we <change>, then <observable outcome> for <actor/system> will improve,
as measured by <signal> within <time boundary>.
~~~

### Non-goals

- &lt;explicitly excluded outcome or scope&gt;

## 2. Functional contract

### Required behavior

1. &lt;observable behavior&gt;
2. &lt;observable behavior&gt;

### Failure behavior

| Condition | Expected behavior | User/operator signal |
| --- | --- | --- |
| &lt;dependency unavailable&gt; | &lt;fail closed / retry / degrade&gt; | &lt;response, event, alert&gt; |
| &lt;invalid input&gt; | &lt;reject or normalize&gt; | &lt;response&gt; |

### Acceptance examples

~~~gherkin
Given <initial state>
When <action>
Then <observable result>
And <required evidence>
~~~

Include at least one success case, one permission or validation failure, and one
dependency-failure case when relevant.

## 3. Non-functional contract

Complete only relevant rows. Replace vague words such as "fast" or "secure" with a
boundary or a linked standard.

| Dimension | Constraint | Verification |
| --- | --- | --- |
| Latency | &lt;percentile and budget&gt; | &lt;test/dashboard&gt; |
| Capacity | &lt;expected and peak load&gt; | &lt;load evidence&gt; |
| Availability | &lt;required behavior during failure&gt; | &lt;fault test/runbook&gt; |
| Security | &lt;identity, authorization, data boundary&gt; | &lt;review/scans/tests&gt; |
| Privacy | &lt;data classification and retention&gt; | &lt;review/evidence&gt; |
| Compatibility | &lt;API/event/schema requirement&gt; | &lt;contract test&gt; |
| Operability | &lt;logs, metrics, traces, alerts&gt; | &lt;dashboard/query/runbook&gt; |

## 4. Interfaces and dependencies

| Dependency or interface | Owner | Contract/version | Change required | Failure mode |
| --- | --- | --- | --- | --- |
| &lt;service, event, schema, vendor&gt; | &lt;owner&gt; | &lt;link/version&gt; | yes/no | &lt;effect&gt; |

State ordering, idempotency, retry, timeout, and backward-compatibility expectations
explicitly when the change crosses a service boundary.

## 5. Delivery plan

### Change set

- &lt;repository/component and intended change&gt;

### Migration or data handling

~~~text
<forward migration, compatibility window, data validation, cleanup>
~~~

### Rollout

~~~text
<feature flag, cohort, canary, sequence, observation period>
~~~

### Rollback

~~~text
<trigger, authority, steps, data implications, maximum safe rollback time>
~~~

## 6. Human-agent decision map

| Stage | Agent may | Agent must not | Human decision owner | Required evidence |
| --- | --- | --- | --- | --- |
| Discovery | &lt;search, summarize, list gaps&gt; | &lt;choose outcome&gt; | &lt;name/role&gt; | &lt;brief&gt; |
| Ready review | &lt;check fields and consistency&gt; | &lt;approve exception&gt; | &lt;name/role&gt; | &lt;findings&gt; |
| Implementation | &lt;edit, test within scope&gt; | &lt;expand scope silently&gt; | &lt;name/role&gt; | &lt;change and test log&gt; |
| Verification | &lt;run checks, assemble bundle&gt; | &lt;self-approve high risk&gt; | &lt;name/role&gt; | &lt;evidence bundle&gt; |
| Release | &lt;prepare, monitor, recommend&gt; | &lt;release beyond permission&gt; | &lt;name/role&gt; | &lt;approval and rollout state&gt; |

## 7. Evidence bundle

Required before Definition of Done:

- [ ] Contract version linked to the change.
- [ ] Functional acceptance cases executed.
- [ ] Relevant NFR checks completed.
- [ ] Interface/contract compatibility verified.
- [ ] Code and architecture ownership reviews complete.
- [ ] Security/privacy review complete or explicitly not applicable.
- [ ] Logs, metrics, traces, alerts, and dashboard links present as required.
- [ ] Migration and rollback exercised or reviewed.
- [ ] Documentation and runbook updated.
- [ ] Known exceptions recorded with owner and follow-up date.
- [ ] Release observation window and outcome check scheduled.

## 8. Exceptions and risk acceptance

| Missing condition or accepted risk | Reason | Compensating control | Owner | Expires/follow-up |
| --- | --- | --- | --- | --- |
| &lt;item&gt; | &lt;why ship now&gt; | &lt;temporary protection&gt; | &lt;one person&gt; | &lt;date&gt; |

An agent may identify or draft an exception. A named human owner accepts it.

## 9. Outcome check

Complete after the agreed observation window.

| Question | Evidence |
| --- | --- |
| Did the intended outcome change? | &lt;metric, feedback, operational signal&gt; |
| Did risk or operating cost move elsewhere? | &lt;incidents, queue time, support load&gt; |
| What should be retained as a reusable pattern? | &lt;template, rule, test, runbook&gt; |
| What follow-up work is required? | &lt;owned items&gt; |

## State-transition checks

### Discovery → Review

- [ ] Problem, outcome owner, outcome hypothesis, and non-goals exist.
- [ ] Material stakeholders and dependencies are identified.

### Review → Ready

- [ ] Functional and relevant non-functional requirements are testable.
- [ ] Interfaces, failure behavior, evidence, rollout, and rollback are explicit.
- [ ] Agent permission boundaries and mandatory human decisions are recorded.

### Implementation → Verification

- [ ] Scope changes are reflected in a new contract version.
- [ ] Proposed change and machine-generated artifacts are attributable.
- [ ] Required checks have produced inspectable evidence.

### Verification → Released

- [ ] Reviewer and release owner accepted the evidence and unresolved risk.
- [ ] Operational monitoring and rollback authority are active.

### Released → Outcome checked

- [ ] The outcome was evaluated within the declared measurement boundary.
- [ ] Exceptions and follow-up items have owners and dates.
- [ ] Reusable learning was added to the relevant standard or pattern library.
