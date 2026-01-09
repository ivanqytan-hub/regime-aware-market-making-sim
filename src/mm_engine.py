from __future__ import annotations
from dataclasses import dataclass
import numpy as np


@dataclass
class MMParams:
    spread_bps_low: float = 8.0
    spread_bps_med: float = 12.0
    spread_bps_high: float = 25.0

    # inventory skew: moves quotes to reduce inventory
    skew_bps_per_unit: float = 2.0  # bps per 1 unit inventory

    # execution / fill model
    base_fill_prob: float = 0.20     # baseline per minute
    kappa: float = 1.5               # higher => fills drop faster as quotes move away from mid

    # risk controls
    inv_cap: float = 3.0             # hard cap (units)
    kill_switch_regime: int = 2      # 2 = HIGH
    kill_switch_mode: str = "pause"  # "pause" or "widen"


@dataclass
class MMState:
    cash: float = 0.0
    inv: float = 0.0


def spread_bps_for_regime(params: MMParams, regime: int) -> float:
    if regime == 0:
        return params.spread_bps_low
    if regime == 1:
        return params.spread_bps_med
    return params.spread_bps_high


def quote_prices(mid: float, regime: int, st: MMState, params: MMParams) -> tuple[float, float, bool]:
    """
    Returns (bid, ask, quoting_enabled).

    kill_switch_mode:
      - None    : no kill switch (always quote)
      - "pause" : stop quoting when regime >= kill_switch_regime
      - "widen" : quote but widen spreads massively when regime >= kill_switch_regime
    """
    quoting_enabled = True
    spread_bps = spread_bps_for_regime(params, regime)

    # ---- Kill switch behavior ----
    if params.kill_switch_mode is None:
        pass  # no kill switch at all
    elif regime >= params.kill_switch_regime:
        if params.kill_switch_mode == "pause":
            return np.nan, np.nan, False
        elif params.kill_switch_mode == "widen":
            spread_bps = max(spread_bps, 80.0)  # widen a lot
        else:
            raise ValueError("kill_switch_mode must be None, 'pause', or 'widen'")

    # Convert bps to price spread
    spread = mid * (spread_bps / 10_000.0)

    # Inventory skew in bps: if inv > 0 (long), we want to sell -> ask closer, bid further
    skew = mid * (params.skew_bps_per_unit / 10_000.0) * st.inv

    bid = mid - spread / 2.0 - skew
    ask = mid + spread / 2.0 - skew

    return bid, ask, quoting_enabled


def fill_probability(mid: float, quote: float, params: MMParams) -> float:
    """
    Simple probabilistic fill model:
    further from mid => lower fill prob.
    """
    dist = abs(quote - mid) / mid  # fractional distance
    p = params.base_fill_prob * np.exp(-params.kappa * dist * 10_000.0 / 10.0)  # scaled
    return float(np.clip(p, 0.0, 1.0))


def step_mm(mid: float, regime: int, st: MMState, params: MMParams, rng: np.random.Generator) -> dict:
    bid, ask, enabled = quote_prices(mid, regime, st, params)

    if not enabled:
        # no quoting; equity still moves with mark-to-market
        return {"bid": np.nan, "ask": np.nan, "filled": None}

    # Enforce inventory cap by disabling the side that would increase exposure
    # If already long near cap, stop bidding; if short near cap, stop offering.
    can_buy = st.inv < params.inv_cap
    can_sell = st.inv > -params.inv_cap

    filled = None

    # Try buy fill at bid
    if can_buy:
        p_bid = fill_probability(mid, bid, params)
        if rng.random() < p_bid:
            st.inv += 1.0
            st.cash -= bid
            filled = "buy"

    # Try sell fill at ask
    if can_sell:
        p_ask = fill_probability(mid, ask, params)
        if rng.random() < p_ask:
            st.inv -= 1.0
            st.cash += ask
            filled = "sell" if filled is None else "buy+sell"

    return {"bid": bid, "ask": ask, "filled": filled}
