# Regime-Aware Market Making Simulator

This project is a market making simulator designed to understand how inventory control and kill-switch logic interact with changing volatility regimes under adverse selection.

## Overview

The goal is not realism at the microstructure level, but to isolate and test core control problems faced by market makers.

### Key Features

- Markov-switching volatility regimes
- Simple probabilistic fill model
- Inventory-aware, asymmetric quoting
- Risk controls (pause vs widen vs no kill switch)
- Adverse selection proxy

## Core Components

### 1. Price Process (Markov-Switching GBM)

Price evolves according to a Geometric Brownian Motion (GBM) whose volatility is governed by a hidden Markov regime:

- **Regime 0:** Low volatility
- **Regime 1:** Medium volatility
- **Regime 2:** High volatility

Regimes are persistent (sticky transition matrix) and switch stochastically over time, creating clustered volatility which is critical for testing risk controls.

### 2. Market Making Model

At each timestep, the market maker quotes:

```
bid = mid - spread/2 - inventory_skew
ask = mid + spread/2 - 0.5 * inventory_skew
```

**Spread behavior:**
- Widens automatically in higher volatility regimes

**Inventory skew (asymmetric):**
- When long: bids move further away to discourage buying, asks move slightly closer to encourage selling
- When short: opposite behavior

**Fill probability:**
- Fills occur probabilistically, with probability decreasing as quotes move further from mid
- Designed to mimic mean reversion of inventory

### 3. Inventory and PnL

**Tracked metrics:**
- Inventory units
- Cash
- Mark-to-market equity

**PnL sources:**
- Spread capture
- Inventory drift
- Exposure during regime transitions

### 4. Risk Controls

Three strategies are compared on the same price path:

| Strategy | Behavior |
|----------|----------|
| **No kill switch** | Always quotes |
| **Pause** | Stops quoting entirely in high volatility regime |
| **Widen** | Continues quoting but widens spread in high volatility regime |

### 5. Adverse Selection (Toxic Flow)

The market making model simulates adverse selection. When the next period return moves against the market maker's inventory, the probability of fills on that side is increased. This models the intuition that informed traders are more likely to trade with the market maker when prices are about to move unfavorably.

**Regime-dependent toxicity:**
- **Low volatility:** Minimal adverse selection effect
- **Medium volatility:** Moderate toxicity
- **High volatility:** High toxicity

## Results

### Example Run Performance

| Strategy | PnL | Max Drawdown | Inv Std | Inv Max (Abs) | % Quoted |
|----------|-----|--------------|---------|---------------|----------|
| **No kill switch** | 21.80 | -4.02 | 1.38 | 3.0 | 100.0% |
| **Pause** | 0.11 | -6.96 | 1.19 | 3.0 | 74.4% |
| **Widen** | 10.41 | -2.63 | 1.10 | 3.0 | 100.0% |

### Key Insights

**No kill switch:**
- Highest PnL (21.80) but highest risk
- Must deal with inventory volatility and meaningful drawdown (-4.02)
- Always in the market

**Pause:**
- Lowest PnL (0.11) with worst drawdown (-6.96)
- Avoids toxic flow during high volatility but doesn't capture profit
- Inventory gets stuck (risk exists) while PnL stagnates
- Only quotes 74.4% of the time

**Widen (Best risk-adjusted strategy):**
- Balanced PnL (10.41) with lowest drawdown (-2.63)
- Lowest inventory volatility (1.10)
- Stays in the market 100% of the time but with adjusted spreads
- Best balance between profit capture and risk management

## Scope and Limitations

### Intentionally Not Modeled

- Order book dynamics
- Latency and cancellations
- Fees
- Cross-venue hedging
- Predictive alpha signals
