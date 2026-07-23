Title: Technical Debt Portfolio Register
Author: Pavel Nekrasov
Date: 2026-07-15 12:00:00+02:00
Slug: technical-debt-portfolio-register
URL: technical-debt-portfolio-register.html
Save_as: technical-debt-portfolio-register.html
Lang: en
Status: hidden
Summary: A reusable technical-debt register, decision record, exposure assessment, and recurring review checklist.
Canonical: https://nekrasovp.ru/technical-debt-portfolio-register.html
Site005_Material: true
Site005_Role: companion
Site005_Companion_Route: /technical-debt-as-a-portfolio.html
Site005_Companion_Title: Read the operating model
Site005_Companion_Description: Why technical debt works better as a portfolio of owned risks and options than as a flat backlog.

Use this register for technical conditions that create recurring cost, increase failure exposure, or constrain a valuable future option. Keep approved delivery tasks in the normal product backlog.

## Portfolio view

| ID | Condition | Category | Exposure | Reach | Carrying cost | Treatment | Owner | Trigger | Review date | State |
|---|---|---|---:|---|---|---|---|---|---|---|
| TD-001 | Example: incompatible request identifiers prevent reliable cross-service incident reconstruction | Operability | 16/25 | Platform | High | Reduce | Platform owner | Before the next product-area rollout | YYYY-MM-DD | Assessing |

Suggested states:

- `Observed` — the condition has been captured but evidence is incomplete.
- `Assessing` — consequence, exposure, and treatment are being evaluated.
- `Accepted` — exposure is understood and has an explicit trigger and review date.
- `Planned` — a treatment has been approved and delivery work exists.
- `Treating` — repayment, reduction, containment, or retirement is in progress.
- `Monitoring` — treatment is complete; outcome signals are being observed.
- `Closed` — exposure has been removed or reduced to the accepted level.

## Debt decision record

### ID and short name

`TD-___ — concise condition`

### Current condition

What is true today? Describe the constraint without committing to a preferred solution.

### Consequence

What recurring cost, failure exposure, or blocked option does it create?

### Evidence

List incidents, lead-time data, repeated manual work, support load, audit gaps, onboarding friction, or concrete examples. State the measurement boundary and identify estimates.

### Scope and expected lifetime

- Critical user or business flows:
- Services or components:
- Teams and owners:
- Expected remaining lifetime of the affected capability:

### Category

Select one primary category and any secondary categories:

- Delivery friction
- Reliability and performance
- Security and compliance
- Architecture and changeability
- Operability
- Knowledge and ownership

### Exposure assessment

| Dimension | Score | Rationale |
|---|---:|---|
| Impact | 1–5 | |
| Likelihood or frequency | 1–5 | |
| Initial exposure (`impact × likelihood`) | 1–25 | |
| Reach | Local / product area / platform | |
| Carrying cost | Low / medium / high | |
| Option value | Low / medium / high | Which future decision is constrained? |

The numeric signal structures discussion; it does not replace judgment.

### Decision owner

Who owns the next decision? This person does not need to implement all resulting work.

### Treatment decision

Choose one:

- `Repay` — remove the condition.
- `Reduce` — lower probability, reach, or carrying cost.
- `Contain` — limit blast radius or isolate the condition.
- `Accept` — keep it deliberately until a defined trigger.
- `Retire` — remove the affected capability.

Explain why this treatment is preferable to the alternatives.

### Outcome hypothesis

What observable system behavior should change if the treatment works?

Possible signals:

- lead time in the affected area;
- repeated manual steps;
- incident investigation time or missing diagnostic context;
- change failures and rollbacks;
- active exceptions;
- ownership concentration;
- onboarding time;
- conformance to a platform contract;
- product work delayed by the constraint.

### Trigger and review date

- Trigger that invalidates the current decision:
- Next review date:
- Evidence required at the next review:

### Delivery links

Link epics, stories, ADRs, RFCs, incident records, dashboards, and rollout evidence only after the treatment has been selected.

## Monthly review checklist

- Remove duplicates and conditions that no longer exist.
- Confirm evidence, owner, treatment, trigger, and review date for material entries.
- Escalate repeated local conditions into a product-area or platform decision.
- Revisit accepted debt whose trigger has fired.
- Move approved implementation into the normal delivery system.
- Check whether completed treatments changed the intended outcome signals.

## Quarterly portfolio questions

1. Where is exposure increasing despite local work?
2. Which conditions create recurring cost across multiple teams?
3. Which product bets depend on a technical option that is being lost?
4. Which accepted risks have reached their trigger?
5. Which capabilities should be retired instead of repaired?
6. Are platform standards reducing repeated debt or merely centralizing it?
7. Does investment match the highest exposure, or only the most visible requests?
