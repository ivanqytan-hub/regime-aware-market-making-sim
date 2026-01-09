from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np


@dataclass(frozen=True)
class MSGBMParams:
    """Parameters for Markov-switching GBM."""
    dt_minutes: float = 1.0           # timestep in minutes
    s0: float = 100.0                 # initial price
    mu_annual: float = 0.0            # annual drift (keep 0 for now)
    sigmas_annual: Tuple[float, ...] = (0.40, 0.80, 1.60)  # low/med/high vol (annualized)
    transition: Tuple[Tuple[float, ...], ...] = (
        (0.97, 0.03, 0.00),  # from LOW
        (0.02, 0.96, 0.02),  # from MED
        (0.00, 0.03, 0.97),  # from HIGH
    )


def _validate_transition(P: np.ndarray) -> None:
    if P.ndim != 2 or P.shape[0] != P.shape[1]:
        raise ValueError("transition matrix must be square")
    row_sums = P.sum(axis=1)
    if not np.allclose(row_sums, 1.0, atol=1e-8):
        raise ValueError(f"each row of transition must sum to 1. got {row_sums}")
    if np.any(P < 0):
        raise ValueError("transition matrix must have non-negative probabilities")


def sample_regimes(
    n_steps: int,
    transition: np.ndarray,
    start_state: int = 0,
    rng: Optional[np.random.Generator] = None,
) -> np.ndarray:
    """
    Sample a discrete Markov chain of regimes.

    Returns:
        states: shape (n_steps,) int array with values in {0,1,2,...}
    """
    if rng is None:
        rng = np.random.default_rng()
    _validate_transition(transition)

    n_states = transition.shape[0]
    if not (0 <= start_state < n_states):
        raise ValueError("start_state out of range")

    states = np.empty(n_steps, dtype=int)
    s = start_state
    for t in range(n_steps):
        states[t] = s
        s = rng.choice(n_states, p=transition[s])
    return states


def simulate_markov_switching_gbm(
    n_steps: int,
    params: MSGBMParams,
    start_state: int = 0,
    seed: Optional[int] = 42,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Simulate a Markov-switching GBM price path.

    Returns:
        prices: shape (n_steps+1,) prices, starting at s0
        states: shape (n_steps,) regime state for each step
        sigmas_step: shape (n_steps,) per-step sigma (not annualized), aligned with states
    """
    rng = np.random.default_rng(seed)

    # Transition + regimes
    P = np.array(params.transition, dtype=float)
    states = sample_regimes(n_steps=n_steps, transition=P, start_state=start_state, rng=rng)

    # Time conversion
    minutes_per_year = 365.0 * 24.0 * 60.0
    dt = params.dt_minutes / minutes_per_year  # in years

    # Convert annual parameters to per-step values
    mu = params.mu_annual
    sigmas_annual = np.array(params.sigmas_annual, dtype=float)
    sigmas_step = sigmas_annual[states]  # still annualized, but state-aligned

    # GBM increments
    # log S_{t+1} = log S_t + (mu - 0.5*sigma^2)*dt + sigma*sqrt(dt)*Z
    Z = rng.standard_normal(n_steps)
    drift = (mu - 0.5 * sigmas_step**2) * dt
    diffusion = sigmas_step * np.sqrt(dt) * Z
    log_returns = drift + diffusion

    prices = np.empty(n_steps + 1, dtype=float)
    prices[0] = params.s0
    prices[1:] = params.s0 * np.exp(np.cumsum(log_returns))

    return prices, states, sigmas_step


def regime_summary(states: np.ndarray) -> dict:
    """Quick helper: how much time spent in each regime."""
    unique, counts = np.unique(states, return_counts=True)
    return {int(u): int(c) for u, c in zip(unique, counts)}
