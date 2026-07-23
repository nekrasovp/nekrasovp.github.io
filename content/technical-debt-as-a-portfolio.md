Title: Technical Debt as a Portfolio: A Practical Operating Model
Author: Pavel Nekrasov
Date: 2026-07-15 12:00:00+02:00
Slug: technical-debt-as-a-portfolio
URL: technical-debt-as-a-portfolio.html
Save_as: technical-debt-as-a-portfolio.html
Lang: en
Status: hidden
Summary: A lightweight system for turning technical debt from an unbounded backlog into explicit risks, owned decisions, and recurring engineering investments.
Canonical: https://nekrasovp.ru/technical-debt-as-a-portfolio.html
Site005_Material: true
Site005_Role: essay
Site005_Companion_Route: /technical-debt-portfolio-register.html
Site005_Companion_Title: Use the technical-debt portfolio register
Site005_Companion_Description: A copyable register, decision record, exposure assessment, and review checklist.

Technical debt is usually managed as a list.

Someone notices a weak service boundary, an obsolete dependency, a fragile deployment, or a test suite that nobody trusts. A ticket is created. It joins hundreds of other tickets under a label called `tech-debt`. Product work remains urgent, the list grows, and the team gradually stops believing that the backlog represents a plan.

The problem is not that the team failed to document its debt. The problem is that an inventory is being asked to perform the work of an investment system.

In the product environments where I have been responsible for architecture and technical-debt planning, the service landscape grew from dozens of services toward roughly one hundred. At that scale, “clean up the code” is not a strategy. Different forms of debt have different carrying costs, failure modes, owners, and repayment options. Some debt should be repaid immediately. Some should be contained. Some is a rational trade that should remain in the system until the product proves that repayment is worthwhile.

That makes technical debt closer to a portfolio than to a single loan.

This article describes the operating model I use to make that portfolio visible and actionable without turning engineers into accountants.

## Debt is a decision, not an insult

Calling every imperfect implementation “technical debt” makes the term useless.

A system can be inelegant and still be fit for purpose. A deliberate shortcut can be the correct way to validate a market. A component can use an old technology without creating meaningful business risk. Conversely, a cleanly written service can carry severe debt if nobody can operate it, access rules are inconsistent, or every change requires knowledge held by one person.

I use the following working definition:

> Technical debt is a current technical condition that creates a recurring cost, increases the probability or impact of failure, or constrains a valuable future option.

This definition has three useful consequences.

First, debt needs a consequence. “I dislike this implementation” is not enough.

Second, debt can exist outside application code. It can live in architecture, tests, delivery workflows, observability, security controls, ownership, documentation, or team knowledge.

Third, debt is contextual. The same condition may be tolerable in an experiment and unacceptable in a payment path or an access-control boundary.

## Why a single backlog fails

A flat technical-debt backlog loses meaning for predictable reasons.

### Items have incompatible units

“Upgrade the framework,” “split the service,” “add tracing,” and “remove a shared database” may all be important, but they do not describe comparable risks or outcomes. Ranking them by intuition creates an argument, not a portfolio decision.

### Urgency decays faster than the ticket

A workaround created for a launch may stop mattering when the feature is retired. A low-priority logging problem may become critical when a service enters a regulated or financially sensitive flow. Static priority cannot represent changing exposure.

### Ownership is ambiguous

Many debt items sit between a product team, a platform team, security, and architecture. When everyone is affected but nobody owns the next decision, the backlog becomes a storage system for organizational uncertainty.

### The list contains solutions disguised as problems

“Migrate to technology X” commits the organization to a solution before the constraint is understood. The real debt may be slow delivery, unsupported software, operational fragility, or a missing capability. Different treatments may address the same exposure at radically different cost.

### Product work and debt are presented as opposites

Teams are asked to choose between “features” and “technical work,” even when the technical investment is what makes the feature safe, supportable, or economically viable. The portfolio model reconnects both sides through outcomes and constraints.

## The minimum viable debt register

The register should contain enough information to support a decision and no more. If creating an entry feels like writing an architecture document, people will stop capturing debt.

I use these fields:

| Field | Question it answers |
|---|---|
| Condition | What is true today? |
| Consequence | What cost, failure, or constraint does it create? |
| Evidence | What signals show that the consequence is real? |
| Scope | Which users, teams, services, or flows are exposed? |
| Owner | Who owns the next decision, not necessarily all implementation? |
| Treatment | Repay, reduce, contain, accept, or retire? |
| Trigger | What event would change the decision? |
| Review date | When must the decision be reconsidered? |

A useful entry is specific enough to challenge.

Weak:

> Logging is bad. Move everything to a new stack.

Stronger:

> Twelve services emit incompatible request identifiers, so incidents crossing the gateway and asynchronous workers cannot be reconstructed reliably. Recent investigations required manual correlation across multiple data sources. The platform owner will evaluate a shared logging contract and rollout path before the next product-area expansion.

The stronger entry does not pretend that the solution is already known. It states the condition, consequence, evidence, scope, owner, and decision horizon.

## Classify by exposure, not by code smell

Taxonomies can become elaborate. I prefer six categories that correspond to operating decisions:

1. **Delivery friction** — changes are slow, repetitive, or difficult to validate.
2. **Reliability and performance** — the system is more likely to fail, recover slowly, or violate capacity expectations.
3. **Security and compliance** — controls are inconsistent, unverifiable, or too dependent on manual action.
4. **Architecture and changeability** — boundaries, dependencies, or data ownership make valuable change expensive.
5. **Operability** — teams cannot observe, deploy, support, or diagnose the system consistently.
6. **Knowledge and ownership** — critical behavior is undocumented, unowned, or concentrated in too few people.

One item may belong to several categories. The purpose is not perfect classification; it is to reveal which operating system must respond.

For example, inconsistent authorization across services is not merely a security issue. It creates delivery friction because each team reinvents policy, architecture debt because identity context crosses boundaries differently, and knowledge debt because behavior depends on local experts.

## Score only what improves the decision

Teams often respond to ambiguity by inventing a precise formula. The result looks objective but hides assumptions inside numbers.

A lightweight score is still useful if it structures discussion rather than replacing judgment. For each item, estimate:

- **Impact:** how severe is the consequence if exposure materializes?
- **Likelihood or frequency:** how often does it occur, or how probable is it within the review horizon?
- **Reach:** how many critical flows, services, teams, or customers are exposed?
- **Carrying cost:** what recurring engineering or operational cost is already being paid?
- **Option value:** which valuable future decisions are blocked or made significantly more expensive?

Use a small scale such as 1–5 and keep the evidence next to the number. I normally treat `impact × likelihood` as an initial exposure signal, then use reach, carrying cost, and option value to discuss ordering. I do not collapse everything into one magic number.

The most valuable output of scoring is often disagreement. If product sees low impact and operations sees high impact, the team has discovered a missing shared model of the system.

## Choose a treatment, not just a priority

Repayment is only one possible response.

### Repay

Remove the condition: replace the fragile component, redesign the boundary, complete the migration, or build the missing capability.

Use this when exposure is high, the target state is understood, and the remaining lifetime of the system justifies the investment.

### Reduce

Lower probability, reach, or carrying cost without eliminating the debt. A shared library, compatibility layer, automated check, or paved-road template can turn many local risks into one managed platform concern.

### Contain

Limit blast radius. Isolate a legacy component, restrict change, add a gateway or policy boundary, introduce a circuit breaker, or separate a risky data path.

Containment is often the fastest rational response when full repayment is too disruptive.

### Accept

Keep the debt deliberately. Record why the exposure is tolerable and define the trigger that reopens the decision. Acceptance without a trigger is usually just neglect written in formal language.

### Retire

Delete the product, feature, service, or integration that creates the debt. Teams frequently underestimate retirement because the backlog assumes every existing capability must survive.

## Run the portfolio at three cadences

Technical debt needs a recurring operating rhythm. An annual cleanup initiative is too slow; reviewing every item every sprint is noise.

### Continuous: capture and local treatment

Engineers capture a debt condition when evidence appears in delivery, incidents, reviews, or operational work. Teams can resolve local, low-cost items without portfolio ceremony. Definition of Done should prevent a temporary shortcut from becoming invisible: document the exception, owner, and trigger before closing the work.

### Monthly: team or product-area review

Review new high-exposure items, changes in evidence, and work that is repeatedly delayed by the same condition. Remove duplicates and dead items. Confirm that every material entry has an owner and a next decision date.

The output is not “more tickets.” It is a small set of proposed treatments with product and engineering consequences.

### Quarterly: cross-team portfolio review

Architecture, product, platform, security, and operational owners examine systemic exposure and investment allocation. This is where repeated local symptoms should become a platform initiative, an architectural migration, or an explicit accepted risk.

The quarterly review should answer:

- Where is exposure increasing despite local work?
- Which debt creates recurring cost across several teams?
- Which product bets depend on a technical option we are losing?
- Which accepted risks have reached their trigger?
- Which initiatives can be stopped because the affected capability should be retired?

## Allocate capacity through triggers, not ritual percentages

“Reserve 20% for technical debt” is easy to communicate and sometimes useful, but it can become a substitute for prioritization. A team may spend the allocation on comfortable refactoring while a cross-service risk remains untouched.

I prefer a base allocation plus explicit triggers.

The base allocation funds continuous maintenance, dependency updates, test health, tooling, and small reductions in delivery friction. The exact percentage depends on product stage and system condition.

Triggers temporarily raise investment when:

- a critical product initiative depends on a blocked technical option;
- incidents or operational load cross an agreed threshold;
- the same workaround appears in several teams;
- a security or compliance boundary cannot be demonstrated;
- onboarding or lead time degrades because the platform is inconsistent;
- a migration window is closing because an upstream dependency is ending support.

This frames debt work as a response to observable system conditions rather than as an engineering entitlement.

## A platform example: from local fixes to portfolio treatment

Consider a product that grows from roughly thirty services toward one hundred. Different teams and external contributors join at different stages. Logging formats, request identifiers, error models, access-control checks, and service ownership begin to diverge.

The flat backlog contains dozens of items:

- add structured logs to service A;
- fix missing correlation in service B;
- document access rules in service C;
- add metrics to service D;
- decide who owns an abandoned integration;
- standardize another deployment template.

Individually, none wins against product work. Together, they reveal portfolio exposure:

- incidents take longer to reconstruct across service boundaries;
- new engineers learn several local conventions;
- policy behavior is difficult to audit consistently;
- each product team pays the cost of solving the same platform problem;
- migrations stall because ownership is unclear.

The treatment is not a heroic rewrite. It is a sequence:

1. Define contracts for logging, correlation, metrics, access context, and ownership.
2. Put those contracts into shared libraries, templates, and gateway or policy boundaries where appropriate.
3. Add automated conformance checks and make exceptions visible.
4. Roll out by exposure and product timing, not alphabetically by repository.
5. Track adoption and retire the old paths.

Architecture reviews, CODEOWNERS, observability standards, and Definition of Done then become repayment mechanisms. Their value is not that they create governance. Their value is that they stop the same debt from being issued independently in every service.

## Measure the carrying system, not lines of debt

The number of tickets closed is a poor outcome metric. Deleting ten low-impact entries does not prove that the portfolio improved.

Useful directional measures include:

- lead time for changes in affected areas;
- repeated manual steps per release or service onboarding;
- incident investigation time and missing diagnostic context;
- change failure and rollback patterns;
- age and count of active exceptions;
- concentration of ownership and review bottlenecks;
- time required for a new team or external contributor to reach production;
- percentage of services conforming to a selected platform contract;
- product initiatives delayed by technical constraints.

Not every organization has clean historical data. Do not invent precision. Establish the boundary, record a baseline where possible, and look for direction over several review cycles.

## Common failure modes

### The debt register becomes a second product backlog

If every item is decomposed into delivery tasks before treatment is selected, the register becomes another queue to maintain. Keep conditions and decisions in the register; track approved implementation in the normal delivery system.

### Architecture owns all debt

Architecture can expose systemic patterns and facilitate decisions, but ownership must remain close to the consequence. A platform owner, product team, security owner, or business owner may hold the real decision.

### Engineers hide product changes inside debt work

Some “refactoring” changes behavior, operating cost, or product capability. Make that impact explicit. Technical work does not become easier to prioritize by pretending it has no product consequences.

### Accepted debt has no expiry condition

An accepted risk without a trigger or review date quietly becomes permanent. Record what would make the decision invalid.

### Standardization creates a larger single point of failure

Shared libraries and paved roads reduce repeated debt, but they also centralize responsibility. They need compatibility policy, ownership, rollout support, and observability like any other product.

## A copyable review template

```markdown
# Debt condition

## Current condition
What is true today? Describe the constraint, not the desired solution.

## Consequence
What recurring cost, failure exposure, or blocked option does it create?

## Evidence
Incidents, lead-time data, repeated work, support load, audit gaps, or examples.

## Scope
Critical flows, services, teams, users, and expected system lifetime.

## Exposure
- Impact: 1-5, with rationale
- Likelihood/frequency: 1-5, with rationale
- Reach: local / product area / platform
- Carrying cost: low / medium / high, with evidence
- Option value: what future decision is constrained?

## Owner
Who owns the next decision?

## Proposed treatment
Repay / reduce / contain / accept / retire.

## Trigger and review date
What changes the decision, and when will it be reviewed?
```

## The goal is a better delivery system

Technical debt will not disappear, and eliminating it should not be the goal. Products need options, experiments, deadlines, and occasionally deliberate shortcuts.

The failure is not taking on debt. The failure is losing the ability to explain what was taken on, what it costs, who owns the next decision, and which conditions require a different response.

A portfolio model restores that ability. It connects engineering conditions to product outcomes, gives architecture governance a concrete purpose, and lets teams invest where the system is actually paying interest.

That is the standard I use: not a clean backlog, but a delivery system that can make its technical trade-offs visible and change them before they become irreversible.
