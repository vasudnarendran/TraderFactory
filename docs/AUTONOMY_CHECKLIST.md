# TraderFactory Autonomy Checklist

This document is the working checklist from the current `TraderFactory` state to the final goal:

- give the repo a round spec and resource mechanics
- let the repo plus an agent produce a serious first trading model
- validate it locally
- optimize it
- submit it officially
- analyze the result
- iterate with minimal manual glue work

This is intentionally more concrete than the architecture docs.
It is meant to be used as a planning and tracking document.

## Target End State

The real target is not:

- a collection of tools
- a collection of strategy notes
- a collection of versioned bots

The real target is:

- a mechanic-driven factory that can accept a round spec
- generate a runnable baseline trader with relevant sleeves already wired
- run the full development workflow with limited human intervention
- switch into research mode when the official simulator disagrees with local evidence
- preserve discoveries and feed them back into the next round

## Status Legend

- `Done`: implemented and usable now
- `Partial`: meaningful pieces exist, but the layer is not yet strong enough to rely on by itself
- `Missing`: not really present yet, or only present as manual reasoning

## Milestone Dashboard

### 1. Infrastructure Layer
Status: `Done`

What exists:
- deterministic replay
- Monte Carlo robustness
- CMA-ES
- official diagnostics
- official submission automation
- queue-aware official workflow
- development-mode workflow
- baseline policy support

Why it matters:
- this is the operational backbone
- without it, the repo cannot function as a reusable factory

Definition of done:
- already met for the current scope

Remaining work:
- mostly maintenance and extension, not foundational buildout

Extra information needed:
- none critical; this layer is already grounded

### 2. Spec Layer
Status: `Partial`

What exists:
- competition, product, and mechanic specs

What is missing:
- richer schemas for future rounds
- explicit support for cross-product links, settlement rules, conversions, expiries, auctions, and nonlinear payoffs

Why it matters:
- the repo can only reason as well as the round description it receives

Definition of done:
- a new round can be fully described in one machine-readable spec with no ad hoc translation in chat

Extra information needed:
- product definitions
- position limits
- tick sizes
- observation channels
- scoring rules
- settlement rules
- any conversion, expiry, or linkage rules

### 3. Mechanic Vocabulary
Status: `Partial`

What exists:
- generic mechanic labels
- strategy taxonomy

What is missing:
- stronger formal vocabulary for:
  - options
  - baskets
  - conversions
  - storage/transport constraints
  - auction-like rounds
  - external latent signals

Why it matters:
- if mechanics are described vaguely, model selection becomes guesswork

Definition of done:
- every future product can be broken down into a compact set of recognized mechanic primitives

Extra information needed:
- real examples of future-round mechanics
- exact formulas or rules where relevant

### 4. Strategy Registry
Status: `Partial`

What exists:
- strategy taxonomy
- capability registry

What is missing:
- more executable strategy sleeves rather than documentation-only families

Why it matters:
- a taxonomy alone does not generate a trader

Definition of done:
- for every major mechanic family, the repo has a reusable runnable module with clear inputs and outputs

Extra information needed:
- more rounds
- more validated examples of which families actually fit which mechanics

### 5. Baseline Project Generation
Status: `Partial`

What exists:
- baseline scaffolding
- capability-aware project generator
- starter sleeves

What is missing:
- stronger generated sleeves
- better automatic assembly of multi-product logic

Why it matters:
- today the repo produces a good starting architecture
- it does not yet produce a strong first model by itself

Definition of done:
- a generated project is not just runnable, but strategically sensible for the given mechanics

Extra information needed:
- clearer generation rules from mechanic families to code templates
- desired defaults for trader structure in future rounds

### 6. Mechanic-to-Model Mapping
Status: `Missing`

What exists:
- manual reasoning
- partial registry guidance

What is missing:
- formal decision rules such as:
  - anchored asset -> anchored MM sleeve
  - directional microstructure asset -> directional + inventory-aware execution sleeve
  - option -> pricing + vol/risk sleeve
  - basket -> residual spread sleeve

Why it matters:
- this is the core missing intelligence layer between “spec” and “generated model”

Definition of done:
- given a spec, the repo can select a first-pass architecture without requiring a human to describe it in prose

Extra information needed:
- more round examples
- explicit mapping rules from mechanics to sleeves
- failure cases where a family should not be used

### 7. Parameterization Layer
Status: `Partial`

What exists:
- optimization engines
- config-driven CMA-ES
- generated experiment directories

What is missing:
- automatic parameter priors for generated sleeves
- better default parameter blocks per mechanic family

Why it matters:
- automatically generated models need to be optimization-ready immediately

Definition of done:
- every generated sleeve comes with a sensible parameter block and optimization config

Extra information needed:
- parameter priors by strategy family
- experience across more mechanic types

### 8. Evaluation and Gating Layer
Status: `Strong but Partial`

What exists:
- deterministic evaluation
- Monte Carlo robustness
- development-mode gating
- official comparison

What is missing:
- richer gate policies by round/mechanic family
- promotion logic for successful candidates

Why it matters:
- this is what turns the repo from “toolbox” into “disciplined factory”

Definition of done:
- the repo can apply explicit accept/reject/promotion rules rather than relying on ad hoc human judgment each cycle

Extra information needed:
- preferred gate thresholds
- tolerance for false positives vs false negatives
- round-specific objective preferences

### 9. Research and Probe Integration
Status: `Strong but Partial`

What exists:
- probe framework
- boundary probes
- passive ladder probes
- aggressive markout probes
- discovery documentation

What is missing:
- automatic recommendation of the right probe when a failure mode is detected

Why it matters:
- the official simulator is still a major source of uncertainty

Definition of done:
- when local and official diverge, TraderFactory can recommend the next probe family automatically

Extra information needed:
- more official divergence cases
- more validated execution findings from future rounds

### 10. Official Loop Automation
Status: `Strong`

What exists:
- official submission automation
- queue-aware upload waiting
- baseline snapshotting
- result download and analysis
- development cycle orchestration

What is missing:
- automatic promotion of the best official candidate into the baseline policy
- possible future-proofing if the site changes

Why it matters:
- this removed one of the biggest manual bottlenecks already

Definition of done:
- after validation, the repo can promote or reject the candidate with minimal human intervention

Extra information needed:
- future site/API changes
- any round-specific official submission quirks

### 11. Cross-Round Knowledge Base
Status: `Partial`

What exists:
- strategy docs
- research docs
- probe discoveries
- handoff material

What is missing:
- more structured reusable knowledge from future rounds

Why it matters:
- without this, each round still starts too close to zero

Definition of done:
- a new round benefits from structured lessons learned in previous rounds, not just human memory

Extra information needed:
- more rounds
- more postmortems
- stronger canonical documentation discipline

### 12. Automatic Model Assembly
Status: `Missing`

What exists:
- all the surrounding infrastructure

What is missing:
- the actual autonomous model-builder layer

Why it matters:
- this is the layer that would turn TraderFactory into the push-button system you ultimately want

Definition of done:
- the repo can take a round spec, generate a serious first model, and push it through the full development workflow

Extra information needed:
- stronger sleeves
- stronger mapping rules
- broader mechanic examples
- more structured priors

### 13. Fully Clean Multi-Agent Usability
Status: `Partial`

What exists:
- good repo docs
- explicit workflow split
- research durability

What is missing:
- more standardized policies
- more encoded defaults
- less need for chat-specific context

Why it matters:
- the repo should be usable by another agent or teammate without replaying the entire history

Definition of done:
- a new agent can work effectively from the repo alone

Extra information needed:
- nothing exotic; mostly documentation and policy discipline

## Information Still Needed For Full Clean Functionality

The following information is needed to make `TraderFactory` truly autonomous and clean across future rounds.

### A. Round-Input Information

For each new round, ideally we need:

- product symbols and descriptions
- position limits
- tick sizes
- book structure and order constraints
- observation channels
- objective / scoring rules
- settlement rules
- penalties, fees, or carrying costs
- expiry rules if derivatives exist
- conversion rules if products can transform
- basket/index linkage rules if products are related
- external or latent signals if the round exposes them

### B. Mechanic Examples

To make the factory genuinely generic, we need more real examples of:

- options / derivative products
- conversion mechanics
- basket relationships
- storage / transport constraints
- auction or periodic-clearing mechanisms
- nonlinear payoff products
- external-signal products

Without those examples, abstractions can still be built, but some of them will be guesses.

### C. Execution Information

To improve official-loop reliability across rounds, we still benefit from:

- official execution quirks
- queue behavior
- fill semantics
- submission site/API changes

### D. Policy Information

For full automation, the repo also needs explicit policy choices:

- local gate thresholds
- robustness thresholds
- when to submit officially
- when to promote a candidate
- what counts as “better enough” to replace the baseline

## Practical Remaining Roadmap

### Phase 1. Strengthen the Factory Brain

Focus:
- mechanic-to-model mapping
- stronger reusable sleeves
- better generated project output

Checklist:
- [ ] formalize mapping rules from mechanics to strategy sleeves
- [ ] add stronger runnable sleeves for major current families
- [ ] teach project generation to assemble these sleeves automatically

### Phase 2. Make Generated Models Optimization-Ready

Focus:
- parameter priors
- experiment generation
- baseline policies

Checklist:
- [ ] generate parameter blocks automatically per sleeve
- [ ] generate experiment configs automatically
- [ ] add promotion/replacement policy after successful official runs

### Phase 3. Make Research More Automatic

Focus:
- failure-mode detection
- probe recommendation
- durable knowledge accumulation

Checklist:
- [ ] infer likely divergence class from local vs official evidence
- [ ] recommend the right probe automatically
- [ ] feed discoveries back into strategy planning

### Phase 4. Reach First Real Autonomy

Focus:
- end-to-end first-pass model creation from a spec

Checklist:
- [ ] accept full round spec
- [ ] choose sleeves automatically
- [ ] generate runnable baseline model
- [ ] run local validation
- [ ] optimize
- [ ] submit officially
- [ ] summarize promote/reject verdict

## Bottom Line

`TraderFactory` is already a strong model-development system.

It is not yet a fully autonomous model-construction system.

The biggest remaining gap is not tooling.
It is:

- stronger reusable strategy sleeves
- stronger mechanic-to-model mapping
- more real mechanic examples from future rounds

That is the path to the final goal.
