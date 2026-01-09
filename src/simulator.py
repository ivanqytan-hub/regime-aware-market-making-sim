import numpy as np
import matplotlib.pyplot as plt

from price_process import MSGBMParams, simulate_markov_switching_gbm
from mm_engine import MMParams, MMState, step_mm


def run_simulation(
    n_steps: int = 24 * 60,
    seed: int = 42,
):
    rng = np.random.default_rng(seed)

    # ----- Price process -----
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

    prices, regimes, _ = simulate_markov_switching_gbm(
        n_steps=n_steps,
        params=price_params,
        seed=seed,
    )

    # ----- Market maker -----
    mm_params = MMParams(
        spread_bps_low=8.0,
        spread_bps_med=12.0,
        spread_bps_high=25.0,
        skew_bps_per_unit=2.0,
        base_fill_prob=0.20,
        kappa=1.5,
        inv_cap=3.0,
        kill_switch_regime=2,
        kill_switch_mode="pause",
    )

    state = MMState(cash=0.0, inv=0.0)

    # ----- Tracking -----
    inventory = []
    cash = []
    equity = []
    fills = []
    quoting_enabled = []

    for t in range(n_steps):
        mid = prices[t]
        regime = regimes[t]

        info = step_mm(mid, regime, state, mm_params, rng)

        inventory.append(state.inv)
        cash.append(state.cash)
        equity.append(state.cash + state.inv * mid)
        fills.append(info["filled"])
        quoting_enabled.append(info["filled"] is not None or info["bid"] == info["bid"])

    return prices, regimes, inventory, cash, equity, fills, quoting_enabled


def plot_results(prices, regimes, inventory, equity):
    t = np.arange(len(prices) - 1)

    fig, axs = plt.subplots(4, 1, figsize=(12, 10), sharex=True)

    axs[0].plot(prices[:-1])
    axs[0].set_title("Price")

    axs[1].step(t, regimes, where="post")
    axs[1].set_title("Regime (0=LOW, 1=MED, 2=HIGH)")
    axs[1].set_ylim(-0.2, 2.2)

    axs[2].plot(inventory)
    axs[2].set_title("Inventory")

    axs[3].plot(equity)
    axs[3].set_title("Equity (MTM)")

    for ax in axs:
        ax.grid(alpha=0.3)

    plt.xlabel("Minute")
    plt.tight_layout()
    plt.show()


def main():
    results = run_simulation()
    plot_results(*results[:4])


if __name__ == "__main__":
    main()
