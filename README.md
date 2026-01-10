# regime-aware-market-making-sim
This project is a regime-aware market making simulator designed to understand how inventory control and kill-switch logic interact with changing volatility regimes under adverse selection.

The goal is not realism at the microstructure level here, but to isolate and test core control problems faced by market makers.

This simulator combines:
- Markov-switching volatility regimes
- A simple probabilistic fill model
- Inventory-aware, asymmetric quoting
- Risk controls (pause vs widen vs no kill switch)
- A simple Adverse selection proxy

Key Ideas:

1. Price Process (Markov-Switching GBM)

Price evolves according to a Geometric Brownian Motion (GBM) whose volatility is governed by a hidden Markov regime:

Regime 0: Low volatility
Regime 1: Medium volatility
Regime 2: High volatility

Regimes are persistent (sticky transition matrix) and switch stochastically over time.

This creates clustered volatility, which is critical for testing risk controls.

2. Market Making Model

At each timestep, the market maker quotes:

bid = mid - spread/2 - inventory skew
ask = mid + spread/2 - 0.5 * inventory skew

Spread widens automatically in higher volatility regimes.

Inventory skew is asymmetric. When long, bids are further to discourage buying more and ask moves slightly closer to encourage selling. When short, behavior is the opposite.

Fills occur probabilistically, with probability decreasing as quotes move further from mid.

This aims to mimic mean reversion of inventory.

3. Inventory and PnL

The simulator tracks:
- Inventory units
- Cash
- Mark-to-market equity

PnL comes from:
- Spread capture
- Inventory drift
- Exposure during regime transitions

4. Risk Controls:

Three strategies are compared on the same price path.

No kill switch: Always quotes
Pause: Stops quoting entirely in high volatility regime
Widen: Continues quoting but widens spread in high volatility regime.

5. Modeling Adverse Selection (Toxic Flow)

The market making model simulates adverse selection. When the next period return moves against the market maker's inventory, the probability of fills on that side is increased.
This models the intuition that informed traders are more likely to trade with the market maker when prices are about to move unfavorably.

Adverse selection intensity is modeled to be regime-dependent:
- Low volatility: minimal effect
- Medium volatility: moderate toxicity
- High volatility: high toxicity

Results on example run
No kill switch     | PnL:    21.80 | MaxDD:    -4.02 | InvStd:   1.38 | InvMaxAbs:  3.0 | %Quoted:  100.0%
Kill switch: pause | PnL:     0.11 | MaxDD:    -6.96 | InvStd:   1.19 | InvMaxAbs:  3.0 | %Quoted:   74.4%
Kill switch: widen | PnL:    10.41 | MaxDD:    -2.63 | InvStd:   1.10 | InvMaxAbs:  3.0 | %Quoted:  100.0%

6. Insights

No kill switch: Highest PnL but highest risk. Have to deal with inventory volatility and meaningful drawdown.

Pause: Stopping quotes in high volatility avoids toxic flow but doesn't capture profit, inventory gets stuck (risk exists) while PnL stagnates.

Widen: Staying in the market but widening spread in high volatility gives best balance of PnL and drawdown, and lowest inventory volatility.

7. Scope and Limitations

Intentionally not modeled:
- Order book dynamics
- Latency and cancellations
- Fees
- Cross-venue Hedging
- Predictive alpha signals