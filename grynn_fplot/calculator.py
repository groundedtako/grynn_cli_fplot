"""Options calculator for manual broker data input"""

import click
from tabulate import tabulate
from grynn_fplot.core import (
    calculate_cagr_to_breakeven,
    calculate_put_annualized_return,
    calculate_bs_greeks,
)


def run_calculator(spot, strike, price, dte, is_call, is_put, iv, delta):
    """Calculate option metrics from broker data"""

    # Validate required parameters
    if spot is None or strike is None or price is None or dte is None:
        click.echo("Error: Calculator mode requires --spot, --strike, --price, and --dte")
        click.echo("Example: fplot --calc -s 100 -k 110 -p 5.25 -d 35 --call --iv 0.35")
        return

    # Determine option type
    if is_call and is_put:
        click.echo("Error: Cannot specify both --call and --put")
        return
    elif not is_call and not is_put:
        click.echo("Error: Must specify either --call or --put")
        return

    option_type = "call" if is_call else "put"

    # Calculate time to expiry in years
    time_to_expiry = dte / 365.0

    # Calculate CAGR/Return metric
    if option_type == "call":
        return_metric = calculate_cagr_to_breakeven(spot, strike, price, dte)
        return_label = "CAGR to Breakeven"
    else:  # put
        return_metric = calculate_put_annualized_return(spot, price, dte)
        return_label = "Annualized Return"

    # Calculate Greeks from IV or use provided delta
    greeks = None
    delta_source = None
    if iv is not None:
        greeks = calculate_bs_greeks(spot, strike, time_to_expiry, volatility=iv, option_type=option_type)
        calc_delta = greeks["delta"]
        delta_source = f"Calculated (IV={iv:.1%})"
    elif delta is not None:
        calc_delta = delta
        delta_source = "Provided by broker"
    else:
        click.echo("Error: Either --iv or --delta must be provided")
        return

    # When broker delta is supplied without IV, use it directly for leverage only
    if delta is not None and iv is None:
        calc_delta = delta

    # Calculate leverage
    leverage = abs(calc_delta) * (spot / price) if price > 0 else None

    # Calculate DTE-weighted efficiency (leverage / (CAGR × √(DTE/365)))
    efficiency_raw = None
    if leverage and return_metric and return_metric > 0 and dte > 0:
        dte_weight = (dte / 365.0) ** 0.5
        efficiency_raw = leverage / (return_metric * dte_weight)

    # Calculate strike percentage
    strike_pct = ((strike - spot) / spot) * 100

    # Prepare output table
    results = [
        ["Input Parameters", ""],
        ["─" * 30, "─" * 30],
        ["Spot Price", f"${spot:.2f}"],
        ["Strike Price", f"${strike:.2f}"],
        ["Option Price", f"${price:.2f}"],
        ["Days to Expiry", f"{dte} days"],
        ["Option Type", option_type.upper()],
        ["", ""],
        ["Calculated Metrics", ""],
        ["─" * 30, "─" * 30],
        ["Strike vs Spot", f"{strike_pct:+.2f}%"],
        [return_label, f"{return_metric:.2%}"],
        ["Delta", f"{calc_delta:+.4f} ({delta_source})"],
        ["Leverage (Ω)", f"{leverage:.2f}x" if leverage else "N/A"],
        ["Efficiency (DTE-adj)", f"{efficiency_raw:.2f}" if efficiency_raw else "N/A"],
    ]

    # Add IV-derived Greeks if IV was provided
    if greeks is not None:
        results.append(["", ""])
        results.append(["Greeks (from IV)", ""])
        results.append(["─" * 30, "─" * 30])
        results.append(["Implied Volatility", f"{iv:.2%}"])
        results.append(["Gamma", f"{greeks['gamma']:.5f}"])
        results.append(["Theta (daily $/share)", f"{greeks['theta']:.4f}"])
        results.append(["Vega ($ per 1% IV)", f"{greeks['vega']:.4f}"])
        results.append(["Prob ITM (N(d2))", f"{greeks['prob_itm']:.1%}"])

    click.echo()
    click.echo(tabulate(results, tablefmt="simple"))
    click.echo()

    # Interpretation
    click.echo("Interpretation:")
    click.echo(f"  • A 1% move in stock → ~{leverage:.1f}% move in option" if leverage else "  • Leverage unavailable")
    if greeks is not None:
        click.echo(f"  • Prob of expiring ITM: {greeks['prob_itm']:.1%}")
        click.echo(f"  • Losing ${abs(greeks['theta']):.2f}/share per day to time decay")
    if efficiency_raw:
        if efficiency_raw > 20:
            click.echo(f"  • Efficiency {efficiency_raw:.1f} = Excellent (high leverage relative to breakeven hurdle)")
        elif efficiency_raw > 10:
            click.echo(f"  • Efficiency {efficiency_raw:.1f} = Good")
        elif efficiency_raw > 5:
            click.echo(f"  • Efficiency {efficiency_raw:.1f} = Average")
        else:
            click.echo(f"  • Efficiency {efficiency_raw:.1f} = Below average")
    click.echo()
