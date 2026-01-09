import numpy as np
import matplotlib.pyplot as plt

from price_process import MSGBMParams, simulate_markov_switching_gbm, regime_summary


def main():
    params = MSGBMParams(
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

    n_steps = 24 * 60  # 1 day of 1-minute steps
    prices, states, sigmas = simulate_markov_switching_gbm(n_steps=n_steps, params=params, seed=7)

    print("Regime counts:", regime_summary(states))

    # Plot price
    plt.figure()
    plt.plot(prices)
    plt.title("Markov-switching GBM price path")
    plt.xlabel("Minute")
    plt.ylabel("Price")
    plt.show()

    # Plot regimes (as a step chart)
    plt.figure()
    plt.step(np.arange(len(states)), states, where="post")
    plt.title("Regime path (0=LOW, 1=MED, 2=HIGH)")
    plt.xlabel("Minute")
    plt.ylabel("Regime")
    plt.ylim(-0.2, 2.2)
    plt.show()


if __name__ == "__main__":
    main()
