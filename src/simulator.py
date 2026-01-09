import numpy as np
import matplotlib.pyplot as plt

from price_process import MSGBMParams, simulate_markov_switching_gbm
from mm_engine import MMParams, MMState, step_mm


def compute_metrics(prices, equity, inventory, quoted_mask):
    prices = np.asarray(prices)
    equity = np.asarray(equity)
    inventory = np.asarray(inventory)
    quoted_mask = np.asarray(quoted_mask, dtype=bool)

    total_pnl = equity[-1] - equity[0]

    # max drawdown on equity curve
    peak = np.maximum.accumulate(equity)
    dd = equity - peak
    max_dd = dd.min()

    inv_std = float(inventory.std())
    inv_max_abs = float(np.max(np.abs(inventory)))

    pct_quoted = float(quoted_mask.mean()) * 100.0

    return {
        "TotalPnL": float(total_pnl),
        "MaxDD": float(max_dd),
        "InvStd": inv_std,
        "InvMaxAbs": inv_max_abs,
        "PctQuoted": pct_quoted,
    }


def run_mm_on_path(prices, regimes, mm_params: MMParams, seed: int = 42):
    rng = np.random.default_rng(seed)
    state = MMState(cash=0.0, inv=0.0)

    n_steps = len(regimes)

    inventory = []
    cash = []
    equity = []
    quoted_mask = []  # True if quoting enabled this step

    for t in range(n_steps):
        mid = prices[t]
        regime = int(regimes[t])

        info = step_mm(mid, regime, state, mm_params, rng)

        inventory.append(state.inv)
        cash.append(state.cash)
        equity.append(state.cash + state.inv * mid)

        # quoting enabled if bid is not NaN (NaN != NaN is True, so use that)
        bid = info["bid"]
        quoted_mask.append(bid == bid)

    return {
        "inventory": np.array(inventory, dtype=float),
        "cash": np.array(cash, dtype=float),
        "equity": np.array(equity, dtype=float),
        "quoted": np.array(quoted_mask, dtype=bool),
    }


def main():
    # ----- Generate ONE shared price path -----
    price_params = MSGBMParams(
        dt_minutes=1.0,
        s0=100.0,
        mu_annual=0.0,
        sigmas_annual=(0.40, 0.80, 1.60),
        transition=(
            (0.97, 0.03, 0.00),
            (0.02, 0.96, 0.02),
            (0.00, 0.03, 0.97),
        ),
    )

    n_steps = 24 * 60
    prices, regimes, _ = simulate_markov_switching_gbm(
        n_steps=n_steps,
        params=price_params,
        seed=7,  # keep fixed so comparisons are apples-to-apples
    )

    # ----- Base MM parameters (shared) -----
    base_kwargs = dict(
        spread_bps_low=8.0,
        spread_bps_med=12.0,
        spread_bps_high=25.0,
        skew_bps_per_unit=2.0,
        base_fill_prob=0.20,
        kappa=1.5,
        inv_cap=3.0,
        kill_switch_regime=2,
    )

    configs = [
        ("No kill switch", MMParams(**base_kwargs, kill_switch_mode=None)),
        ("Kill switch: pause", MMParams(**base_kwargs, kill_switch_mode="pause")),
        ("Kill switch: widen", MMParams(**base_kwargs, kill_switch_mode="widen")),
    ]

    results = {}

    for name, params in configs:
        out = run_mm_on_path(prices, regimes, params, seed=42)
        metrics = compute_metrics(prices[:-1], out["equity"], out["inventory"], out["quoted"])
        results[name] = {"out": out, "metrics": metrics}

    # ----- Print metrics -----
    print("\n=== Comparison (same price path) ===")
    for name, r in results.items():
        m = r["metrics"]
        print(
            f"{name:18s} | "
            f"PnL: {m['TotalPnL']:8.2f} | "
            f"MaxDD: {m['MaxDD']:8.2f} | "
            f"InvStd: {m['InvStd']:6.2f} | "
            f"InvMaxAbs: {m['InvMaxAbs']:4.1f} | "
            f"%Quoted: {m['PctQuoted']:6.1f}%"
        )

    # ----- Plot equity curves -----
    t = np.arange(n_steps)

    plt.figure(figsize=(12, 5))
    for name, r in results.items():
        plt.plot(t, r["out"]["equity"], label=name)
    plt.title("Equity (MTM) comparison: no kill vs pause vs widen")
    plt.xlabel("Minute")
    plt.ylabel("Equity")
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()

    # ----- Optional: plot inventory comparison -----
    plt.figure(figsize=(12, 5))
    for name, r in results.items():
        plt.plot(t, r["out"]["inventory"], label=name)
    plt.title("Inventory comparison")
    plt.xlabel("Minute")
    plt.ylabel("Inventory (units)")
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
