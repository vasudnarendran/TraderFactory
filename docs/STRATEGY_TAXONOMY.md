# Strategy Taxonomy

This document turns the broad "model families" collection into a working `TraderFactory` taxonomy.

Its purpose is not to dump every strategy ever mentioned in quant trading. Its purpose is to answer three practical questions:

1. What question does each model family answer?
2. When should `TraderFactory` consider that family from product mechanics?
3. Is that family currently factory-ready, research-only, or reference-only?

## How To Use This Document

Use this taxonomy in three layers:

- `references/` for broad background and examples
- [trader_factory/core/registry.py](/Users/vasudravinarendran/Documents/Prosperity/TraderFactory/trader_factory/core/registry.py) for capabilities the factory can actively recommend today
- generation and planning output for deciding what to build first for a new round

The most important distinction is:

- `factory_ready`: the family already maps to concrete capabilities the factory can recommend today
- `research_only`: the family is part of the workflow, but as a diagnostic or research tool rather than a production sleeve
- `reference_only`: the family belongs in the repo because future rounds may need it, but it is not yet wired into active planning/generation

## The Working Stack

Most useful trading systems are not one model. They are a stack:

- value model: what should this thing be worth?
- signal model: what is likely to happen next?
- execution model: how should we enter or quote?
- risk model: how much exposure should we tolerate?
- optimization and diagnostics: how do we tune and verify the system?

That is the reason `TraderFactory` should store model families by role, not just by name.

## Family Map

### 1. Pricing And Derivatives

Question answered:
- What is the theoretical value of this instrument under an explicit pricing model?

Typical examples:
- Black-Scholes
- binomial trees
- local volatility
- stochastic-volatility models such as Heston

Use when:
- the product is an option or another derivative
- volatility is part of the contract economics
- hedging relationships matter

Typical inputs:
- spot or underlying price
- strike
- expiry or time to maturity
- interest/carry assumptions
- volatility estimate or implied volatility

Typical outputs:
- theoretical value
- Greeks or hedge sensitivities
- implied volatility diagnostics

Mechanics that should trigger attention:
- `option`
- `derivative`
- `expiry`
- `convertible`
- `volatility_surface`

TraderFactory status:
- `factory_ready` for the basic derivative sleeve already represented by `option_parity_and_hedging`
- `reference_only` for richer models such as local vol and Heston

Notes:
- Black-Scholes is not important for the current EMERALDS/TOMATOES-style example round.
- It is still important in `TraderFactory` because future rounds may include option-style products, and the factory should know that pricing-model families exist before the round starts.

### 2. Fair Value And Mean Reversion

Question answered:
- Where should price or residual drift back toward?

Typical examples:
- Ornstein-Uhlenbeck
- cointegration
- Kalman filtering
- state-space fair estimation
- residual z-score models

Use when:
- price has a stable anchor or a latent fair
- a spread, basket residual, or premium reverts
- the product is noisy and fair must be filtered rather than observed directly

Typical inputs:
- recent prices
- spread or residual series
- slow fair estimates
- detrended state

Typical outputs:
- fair proxy
- reversion score
- chase brake or veto signal

Mechanics that should trigger attention:
- `anchored`
- `stable_fair`
- `latent_fair`
- `mean_reversion`
- `residual`
- `pair_linked`
- `spread_relationship`

TraderFactory status:
- `factory_ready`

Registry mapping:
- `static_anchor_mm`
- `residual_mean_reversion`
- `pair_or_spread_trading`

### 3. Trend And Forecasting

Question answered:
- Where is the market likely to move next?

Typical examples:
- linear regression
- momentum
- moving-average forecast variants
- ARIMA-style forecasting
- lightweight machine-learned predictors

Use when:
- short-horizon directional pressure matters
- products drift or trend intraday
- continuation or breakout behavior exists

Typical inputs:
- short price history
- microstructure features
- filtered fair vs price gap
- persistence and burst signals

Typical outputs:
- predicted edge
- directional conviction
- aggression scaling

Mechanics that should trigger attention:
- `trend`
- `microstructure_alpha`
- `flow_sensitive`
- `breakout`
- `burst`

TraderFactory status:
- `factory_ready`

Registry mapping:
- `short_horizon_regression_alpha`
- `breakout_confirmation`

### 4. Volatility And State Uncertainty

Question answered:
- How noisy or unstable is the market right now?

Typical examples:
- EWMA volatility
- realized volatility
- GARCH
- stochastic volatility side models

Use when:
- quote width should adapt
- sizing should shrink in turbulence
- derivative pricing needs a volatility estimate

Typical inputs:
- returns
- book movement
- realized spread/mid changes

Typical outputs:
- volatility estimate
- quote-width multiplier
- confidence penalty

Mechanics that should trigger attention:
- `volatile`
- `uncertain_fair`
- `turbulent`
- `derivative`

TraderFactory status:
- `reference_only`

Notes:
- This family is clearly useful, but it is not yet represented as a named capability in the active registry.
- It should eventually become a first-class overlay family rather than being hidden inside ad hoc parameters.

### 5. Market Making And Quoting

Question answered:
- Where should we quote, and how should inventory affect those quotes?

Typical examples:
- anchored market making
- join/improve quoting
- inventory control
- Avellaneda-Stoikov style reservation-price logic
- Guéant-Lehalle style quote-control approximations

Use when:
- passive spread capture is a real edge source
- inventory control matters
- market structure is sufficiently stable to reward quoting

Typical inputs:
- fair value
- touch and spread
- inventory
- volatility and execution conditions

Typical outputs:
- bid/ask quotes
- reservation shift
- passive size bias

Mechanics that should trigger attention:
- `market_making`
- `maker_friendly`
- `spread_capture`
- `inventory_sensitive`
- `book_stable`

TraderFactory status:
- `factory_ready`

Registry mapping:
- `static_anchor_mm`
- `join_improve_mm`
- `inventory_skew_mm`

### 6. Execution And Participation

Question answered:
- How should we trade without paying unnecessary cost or losing too much fill probability?

Typical examples:
- Almgren-Chriss style scheduling
- participation models
- impact/slippage models
- passive-vs-aggressive execution controls

Use when:
- execution quality is the main uncertainty
- the backtester and official simulator diverge
- fill probability and slippage determine whether edge survives

Typical inputs:
- fill history
- quote distance
- side, spread, and imbalance context
- time remaining
- inventory urgency

Typical outputs:
- take/wait decisions
- quote distance choices
- size throttles
- execution-quality diagnostics

Mechanics that should trigger attention:
- `unknown_execution`
- `hidden_simulator`
- `transfer_gap`
- `thin_liquidity`
- `impact_sensitive`

TraderFactory status:
- `research_only` for the current probe-driven workflow
- partially `factory_ready` for generic participation controls, but not yet promoted as a full first-class family

Registry mapping:
- `execution_probe_suite`

### 7. Order Flow And Microstructure

Question answered:
- What is the book, queue, or participant flow telling us right now?

Typical examples:
- microprice
- order-book imbalance
- queue models
- trade-sign models
- Hawkes-style event intensity ideas
- participant-conditioned flow following

Use when:
- short-horizon prediction depends on the book
- adverse selection matters
- named or informed participants exist

Typical inputs:
- best bid/ask and depth
- imbalance
- queue depletion/rebuild
- participant tags

Typical outputs:
- microstructure bias
- toxicity estimate
- participant-following signal

Mechanics that should trigger attention:
- `microstructure_alpha`
- `flow_following`
- `informed_trader`
- `named_participant`
- `queue_sensitive`

TraderFactory status:
- `factory_ready` for the participant-following slice
- `reference_only` for richer queue and event-process models

Registry mapping:
- `informed_flow_tracking`

### 8. Regime Detection

Question answered:
- What kind of market are we in, and should the strategy switch behavior?

Typical examples:
- hidden Markov models
- regime-switching filters
- Bayesian state filters
- simpler state machines and confidence gating

Use when:
- one strategy behaves differently in range vs trend vs volatile conditions
- thresholds are too brittle without state awareness

Typical inputs:
- trend persistence
- volatility
- imbalance or flow stability
- residual stretch

Typical outputs:
- regime label
- confidence level
- mode switch

Mechanics that should trigger attention:
- `mixed`
- `volatile`
- `trend`
- `range`

TraderFactory status:
- `reference_only`

Notes:
- Regime ideas are already used implicitly in many strategies, but the family itself is not yet represented as an explicit reusable sleeve or overlay in the active registry.

### 9. Portfolio And Allocation

Question answered:
- How should we allocate exposure across multiple products or opportunities?

Typical examples:
- mean-variance
- risk parity
- factor exposure controls
- Kelly-like capital allocation

Use when:
- there are multiple simultaneous products with real capital tradeoffs
- basket or pair sleeves compete for balance sheet

Typical inputs:
- per-product edge
- covariance or dependency estimates
- inventory and capital usage

Typical outputs:
- capital allocation
- cross-product scaling
- exposure caps

Mechanics that should trigger attention:
- `basket`
- `portfolio_coupled`
- `shared_risk_budget`

TraderFactory status:
- `reference_only`

### 10. Risk And Stress Modeling

Question answered:
- How much can we lose, and what failure modes do we need to survive?

Typical examples:
- stress tests
- scenario analysis
- drawdown rules
- expected shortfall

Use when:
- protecting against regime breaks
- designing inventory limits
- comparing candidate robustness

Typical inputs:
- PnL paths
- scenario perturbations
- inventory and exposure profiles

Typical outputs:
- limits
- kill switches
- stress sensitivity summaries

Mechanics that should trigger attention:
- all products, but especially fragile or leveraged structures

TraderFactory status:
- `factory_ready` in workflow terms through Monte Carlo and diagnostics
- `reference_only` as a strategy-family sleeve

Notes:
- This family already exists strongly in the tooling layer even though it is not yet modeled as a named strategy capability.

### 11. Optimization And Calibration

Question answered:
- Which parameter settings survive both nominal replay and robustness checks?

Typical examples:
- CMA-ES
- Bayesian optimization
- random search
- grid search

Use when:
- a valid baseline already exists
- the search space is small enough to constrain
- the objective is meaningful

Typical inputs:
- bot source
- parameter schema
- replay engine
- robustness metrics

Typical outputs:
- tuned parameter sets
- best-bot materialization
- sensitivity knowledge

Mechanics that should trigger attention:
- this is workflow-level, not product-level

TraderFactory status:
- `factory_ready`

Notes:
- This family belongs in `TraderFactory` because optimization is part of the development system, even though it is not a product sleeve.

### 12. Signal Combination And Blending

Question answered:
- How do we combine overlapping weak signals without double-counting them?

Typical examples:
- weighted linear blends
- factor blending
- PCA-style reductions
- ensemble models

Use when:
- multiple alpha terms overlap
- a bot is accumulating many hand-tuned nudges
- feature interaction is real but full ML is unnecessary

Typical inputs:
- individual signal scores
- fit quality
- confidence metrics
- residual correlation between signals

Typical outputs:
- blended alpha
- confidence-weighted forecast
- veto or consensus score

Mechanics that should trigger attention:
- `multi_signal`
- `feature_overlap`
- `mixed_regime`

TraderFactory status:
- `reference_only`

Notes:
- This family is strategically important because many bad bots become complicated before they become principled.
- `TraderFactory` should eventually treat signal blending as a first-class design decision, not as scattered coefficients.

## How This Maps Into The Current Registry

The active registry is intentionally narrower than the full taxonomy.

Currently represented as live capabilities:

- `pricing_and_derivatives`
  - `option_parity_and_hedging`
- `fair_value_and_mean_reversion`
  - `static_anchor_mm`
  - `residual_mean_reversion`
  - `pair_or_spread_trading`
- `trend_and_forecasting`
  - `short_horizon_regression_alpha`
  - `breakout_confirmation`
- `market_making_and_quoting`
  - `static_anchor_mm`
  - `join_improve_mm`
  - `inventory_skew_mm`
- `order_flow_and_microstructure`
  - `informed_flow_tracking`
- `execution_and_participation`
  - `execution_probe_suite`

Not yet in the registry as active families:

- volatility and state uncertainty
- regime detection
- portfolio and allocation
- signal combination and blending

Those families should remain documented because future rounds may make them important even if the current example round does not.

## Practical Guidance For Agents

When building a new round plan:

1. Start from mechanics, not favorite strategies.
2. Map each product to one primary value family and one primary execution family.
3. Add forecasting only if the mechanics justify it.
4. Treat optimization and diagnostics as mandatory workflow families, not optional extras.
5. Keep `reference_only` families visible in the documentation, but do not pretend they are already automated.

That is the main reason this taxonomy exists: to preserve strategic breadth without turning the repo into a pile of disconnected notes.
