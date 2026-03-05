"""Unit tests for calculate_bs_greeks() — full Black-Scholes Greeks in a single pass"""

import pytest
from math import isclose
from grynn_fplot.core import calculate_bs_greeks, calculate_black_scholes_delta, calculate_implied_leverage


class TestBSGreeksReturnStructure:
    """Verify the return structure and types"""

    def test_returns_all_keys(self):
        greeks = calculate_bs_greeks(100, 100, 90 / 365.0, volatility=0.30, option_type="call")
        assert set(greeks.keys()) == {"delta", "gamma", "theta", "vega", "prob_itm"}

    def test_zero_inputs_return_zeros(self):
        empty = calculate_bs_greeks(0, 100, 0.25, volatility=0.30)
        assert empty == {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "prob_itm": 0.0}

    def test_zero_volatility_returns_zeros(self):
        empty = calculate_bs_greeks(100, 100, 0.25, volatility=0.0)
        assert empty == {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "prob_itm": 0.0}

    def test_zero_dte_returns_zeros(self):
        empty = calculate_bs_greeks(100, 100, 0.0, volatility=0.30)
        assert empty == {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "prob_itm": 0.0}


class TestDelta:
    """Delta values match the existing calculate_black_scholes_delta function"""

    def test_call_delta_matches_standalone(self):
        greeks = calculate_bs_greeks(100, 100, 90 / 365.0, volatility=0.30, option_type="call")
        expected = calculate_black_scholes_delta(100, 100, 90 / 365.0, volatility=0.30, option_type="call")
        assert isclose(greeks["delta"], expected, rel_tol=1e-9)

    def test_put_delta_matches_standalone(self):
        greeks = calculate_bs_greeks(100, 100, 90 / 365.0, volatility=0.30, option_type="put")
        expected = calculate_black_scholes_delta(100, 100, 90 / 365.0, volatility=0.30, option_type="put")
        assert isclose(greeks["delta"], expected, rel_tol=1e-9)

    def test_atm_call_delta_near_half(self):
        greeks = calculate_bs_greeks(100, 100, 90 / 365.0, volatility=0.30, option_type="call")
        assert 0.5 <= greeks["delta"] <= 0.65

    def test_itm_call_delta_high(self):
        greeks = calculate_bs_greeks(100, 90, 90 / 365.0, volatility=0.30, option_type="call")
        assert 0.7 <= greeks["delta"] <= 0.95

    def test_otm_call_delta_low(self):
        greeks = calculate_bs_greeks(100, 110, 90 / 365.0, volatility=0.30, option_type="call")
        assert 0.1 <= greeks["delta"] <= 0.5

    def test_put_call_parity_delta(self):
        """call delta - put delta ≈ 1"""
        c = calculate_bs_greeks(100, 100, 90 / 365.0, volatility=0.30, option_type="call")
        p = calculate_bs_greeks(100, 100, 90 / 365.0, volatility=0.30, option_type="put")
        assert abs((c["delta"] - p["delta"]) - 1.0) < 0.01

    def test_put_delta_negative(self):
        greeks = calculate_bs_greeks(100, 100, 90 / 365.0, volatility=0.30, option_type="put")
        assert greeks["delta"] < 0


class TestGamma:
    """Gamma should be identical for calls and puts, positive, and peak at ATM"""

    def test_gamma_positive(self):
        greeks = calculate_bs_greeks(100, 100, 90 / 365.0, volatility=0.30, option_type="call")
        assert greeks["gamma"] > 0

    def test_gamma_call_equals_put(self):
        c = calculate_bs_greeks(100, 100, 90 / 365.0, volatility=0.30, option_type="call")
        p = calculate_bs_greeks(100, 100, 90 / 365.0, volatility=0.30, option_type="put")
        assert isclose(c["gamma"], p["gamma"], rel_tol=1e-9)

    def test_atm_gamma_larger_than_deep_otm(self):
        atm = calculate_bs_greeks(100, 100, 90 / 365.0, volatility=0.30, option_type="call")
        otm = calculate_bs_greeks(100, 140, 90 / 365.0, volatility=0.30, option_type="call")
        assert atm["gamma"] > otm["gamma"]


class TestTheta:
    """Theta should be negative for long options (time decay hurts buyers)"""

    def test_call_theta_negative(self):
        greeks = calculate_bs_greeks(100, 100, 90 / 365.0, volatility=0.30, option_type="call")
        assert greeks["theta"] < 0

    def test_put_theta_negative(self):
        greeks = calculate_bs_greeks(100, 100, 90 / 365.0, volatility=0.30, option_type="put")
        assert greeks["theta"] < 0

    def test_theta_is_daily(self):
        """Theta should be a small daily number, not annualized"""
        greeks = calculate_bs_greeks(100, 100, 90 / 365.0, volatility=0.30, option_type="call")
        # A realistic daily theta for a $5 ATM option is -0.001 to -0.20
        assert -0.5 < greeks["theta"] < 0

    def test_short_dte_theta_larger(self):
        """Shorter DTE options decay faster (more negative theta)"""
        short = calculate_bs_greeks(100, 100, 7 / 365.0, volatility=0.30, option_type="call")
        long = calculate_bs_greeks(100, 100, 365 / 365.0, volatility=0.30, option_type="call")
        assert short["theta"] < long["theta"]  # more negative


class TestVega:
    """Vega should be positive (long options gain from IV expansion)"""

    def test_call_vega_positive(self):
        greeks = calculate_bs_greeks(100, 100, 90 / 365.0, volatility=0.30, option_type="call")
        assert greeks["vega"] > 0

    def test_put_vega_positive(self):
        greeks = calculate_bs_greeks(100, 100, 90 / 365.0, volatility=0.30, option_type="put")
        assert greeks["vega"] > 0

    def test_call_vega_equals_put_vega(self):
        """Vega is the same for calls and puts with same parameters"""
        c = calculate_bs_greeks(100, 100, 90 / 365.0, volatility=0.30, option_type="call")
        p = calculate_bs_greeks(100, 100, 90 / 365.0, volatility=0.30, option_type="put")
        assert isclose(c["vega"], p["vega"], rel_tol=1e-9)

    def test_vega_units_per_pct_iv(self):
        """Vega should represent $ change per 1% IV; sanity-check magnitude"""
        greeks = calculate_bs_greeks(100, 100, 90 / 365.0, volatility=0.30, option_type="call")
        # For S=100, T=0.25y, σ=0.30, vega/share should be roughly 0.05–0.20
        assert 0.01 < greeks["vega"] < 1.0


class TestProbITM:
    """prob_itm = N(d2), the risk-neutral probability of expiring in the money"""

    def test_call_prob_itm_in_range(self):
        greeks = calculate_bs_greeks(100, 100, 90 / 365.0, volatility=0.30, option_type="call")
        assert 0.0 < greeks["prob_itm"] < 1.0

    def test_atm_call_prob_near_half(self):
        greeks = calculate_bs_greeks(100, 100, 90 / 365.0, volatility=0.30, option_type="call")
        # N(d2) for ATM is slightly below 0.5 due to the drift term
        assert 0.35 <= greeks["prob_itm"] <= 0.55

    def test_deep_itm_call_prob_high(self):
        greeks = calculate_bs_greeks(100, 60, 90 / 365.0, volatility=0.30, option_type="call")
        assert greeks["prob_itm"] > 0.85

    def test_deep_otm_call_prob_low(self):
        greeks = calculate_bs_greeks(100, 150, 90 / 365.0, volatility=0.30, option_type="call")
        assert greeks["prob_itm"] < 0.10

    def test_put_prob_itm_complement_of_call(self):
        """For same strike/expiry, call p_itm + put p_itm ≈ 1"""
        c = calculate_bs_greeks(100, 100, 90 / 365.0, volatility=0.30, option_type="call")
        p = calculate_bs_greeks(100, 100, 90 / 365.0, volatility=0.30, option_type="put")
        assert abs(c["prob_itm"] + p["prob_itm"] - 1.0) < 0.01

    def test_put_option_type_aliases(self):
        p1 = calculate_bs_greeks(100, 100, 0.25, volatility=0.30, option_type="put")
        p2 = calculate_bs_greeks(100, 100, 0.25, volatility=0.30, option_type="puts")
        assert p1 == p2

    def test_call_option_type_aliases(self):
        c1 = calculate_bs_greeks(100, 100, 0.25, volatility=0.30, option_type="call")
        c2 = calculate_bs_greeks(100, 100, 0.25, volatility=0.30, option_type="calls")
        assert c1 == c2


class TestConsistencyWithLegacyFunctions:
    """Ensure backward compatibility — legacy wrappers produce same results"""

    def test_leverage_via_greeks_matches_legacy(self):
        spot, strike, price, dte_years, iv = 100, 100, 5.0, 90 / 365.0, 0.30
        greeks = calculate_bs_greeks(spot, strike, dte_years, volatility=iv, option_type="call")
        leverage_new = abs(greeks["delta"]) * (spot / price)
        leverage_old = calculate_implied_leverage(spot, price, strike, dte_years, "call", volatility=iv)
        assert isclose(leverage_new, leverage_old, rel_tol=1e-9)
