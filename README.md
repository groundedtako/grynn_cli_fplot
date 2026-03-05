# fplot - Financial Plotting & Options Analysis CLI

[![PyPI version](https://img.shields.io/pypi/v/grynn-fplot.svg)](https://pypi.org/project/grynn-fplot/)
[![Python versions](https://img.shields.io/pypi/pyversions/grynn-fplot.svg)](https://pypi.org/project/grynn-fplot/)

A command-line tool for plotting comparative stock price history and analyzing options contracts.
Surfaces implied leverage (Ω), probability of expiry ITM, theta decay, and a composite efficiency
score — all computed from live market data — so you can quickly identify the best bang-for-buck
option on any chain.

## Installation

### From PyPI

```shell
pip install grynn-fplot
```

Or with uv:

```shell
uv tool install grynn-fplot
```

### From Source

```shell
make dev     # editable install for development
make install # uv tool install .
```

---

## Quick-start: finding the best option on a chain

The core use case is comparing implied leverage across strikes and expirations to find the
option with the best risk/reward for your directional view.

```bash
# Show all IBIT calls with >180 DTE, sorted by leverage (highest first)
fplot IBIT --call --all --filter "dte>180" --sort leverage

# Same chain, sorted by composite efficiency score
fplot IBIT --call --all --filter "dte>180" --sort efficiency

# Only options with >30% probability of expiring in the money
fplot IBIT --call --all --filter "prob>0.30, dte>180" --sort leverage

# Compare two specific strikes directly
fplot IBIT --call --all --filter "strike>=35, strike<=45, dte>300"
```

### Understanding the output

```
IBIT 58C 365DTE ($11.20, 33.10%, 4.6x, p:35%, θ-0.02, eff:71)
  │    │    │      │       │       │     │       │        └─ efficiency percentile (0–100)
  │    │    │      │       │       │     │       └─ daily theta decay ($/share)
  │    │    │      │       │       │     └─ prob of expiring in the money (N(d2))
  │    │    │      │       │       └─ implied leverage Ω = Δ × (S/O)
  │    │    │      │       └─ CAGR the stock needs to reach for you to break even
  │    │    │      └─ mid-price (bid+ask)/2 — what you actually pay
  │    │    └─ days to expiry
  │    └─ strike + option type
  └─ ticker
```

If the last traded price is stale (>5% off mid), both are shown:
```
IBIT 40C 365DTE (mid$4.20/last$3.90, 18.50%, 12.3x, p:38%, θ-0.02, eff:72)
```

**Puts** show the same fields minus theta (annualized cash-secured put yield replaces CAGR):
```
IBIT 45P 90DTE ($3.80, 28.40%, 8.1x, p:62%, eff:68)
```

### Picking between options: a worked example

```
$ fplot IBIT --call --all --filter "dte>180" --sort leverage

IBIT 65C 365DTE ($8.50,  48.20%, 5.8x, p:26%, θ-0.02, eff:62)   ← maximum leverage, binary risk
IBIT 58C 365DTE ($11.20, 33.10%, 4.6x, p:35%, θ-0.02, eff:71)
IBIT 52C 365DTE ($14.80, 22.00%, 3.6x, p:47%, θ-0.03, eff:78)   ← sweet spot (top efficiency)
IBIT 46C 486DTE ($16.40, 20.30%, 3.0x, p:57%, θ-0.03, eff:55)
IBIT 40C 486DTE ($19.80, 14.80%, 2.4x, p:68%, θ-0.03, eff:42)   ← stock replacement, high prob
```

| Goal | Sort by | Look for |
|---|---|---|
| Maximum exposure per dollar | `leverage` | Highest leverage with acceptable prob |
| Best risk-adjusted value | `efficiency` | eff > 70, leverage > 3x |
| High probability of profit | `prob` | p: > 50%, low CAGR hurdle |
| Stock replacement (LEAPS) | `prob` | p: > 60%, deep ITM or ATM |

**Reading the tradeoff:** moving down the list you give up leverage but gain probability. The
`eff` score (0–100 percentile rank within the scan) tells you which option has the best
leverage-per-unit-of-required-stock-growth after adjusting for DTE. The `p:` field tells
you whether that leverage is realistic.

---

## Metrics reference

### Implied Leverage (Ω)
```
Ω = |Δ| × (S / O)
```
A 1% move in the stock produces approximately Ω% move in the option.
Delta is computed from the Black-Scholes formula using **live implied volatility from Yahoo
Finance** — no hardcoded σ fallback. Shows `N/A` if IV is unavailable.

### CAGR to Breakeven (calls)
```
breakeven = strike + premium
CAGR = (breakeven / spot)^(365/DTE) − 1
```
The annualized stock return required to not lose money. Lower = easier hurdle.

### Annualized Return (puts)
```
AR = (premium / (spot − premium)) × (365 / DTE)
```
Cash-secured put yield, annualized. Higher = better income.

### Prob ITM
`N(d2)` from Black-Scholes — the risk-neutral probability of the option expiring in the money.
Use this alongside leverage: a 10x option with `p:8%` is a lottery ticket; the same leverage
at `p:35%` is a real directional bet.

### Theta (θ)
Daily time decay in dollars per share (always negative for long options). Tells you the
daily cost of holding the position. `θ-0.02` means you lose $0.02/share per day purely
from time passing, independent of stock movement.

### Efficiency
```
raw = Ω / (CAGR × √(DTE/365))
efficiency = percentile_rank(raw, across all options in scan)  [0–100]
```
A composite score: high leverage relative to the breakeven hurdle, adjusted for DTE so
short-dated and long-dated options compete fairly. **Expressed as a percentile within the
current scan** — eff:80 means this option is in the top 20% of what you're looking at.

---

## Options Calculator (`--calc`)

Calculate metrics from your own broker data — useful when you want to check a specific
contract before pulling the trigger:

```bash
# From implied volatility
fplot --calc -s 52 -k 58 -p 11.20 -d 365 --call --iv 0.75

# From broker-provided delta (no IV needed)
fplot --calc -s 52 -k 45 -p 3.80 -d 90 --put --delta -0.38
```

**Output with `--iv`:**
```
Input Parameters
──────────────────────────────  ──────────────────────────────
Spot Price                      $52.00
Strike Price                    $58.00
Option Price                    $11.20
Days to Expiry                  365 days
Option Type                     CALL

Calculated Metrics
──────────────────────────────  ──────────────────────────────
Strike vs Spot                  +11.54%
CAGR to Breakeven               33.10%
Delta                           +0.4821 (Calculated (IV=75.0%))
Leverage (Ω)                    2.24x
Efficiency (DTE-adj)            6.74

Greeks (from IV)
──────────────────────────────  ──────────────────────────────
Implied Volatility              75.00%
Gamma                           0.01204
Theta (daily $/share)          -0.0213
Vega ($ per 1% IV)              0.1580
Prob ITM (N(d2))                34.8%

Interpretation:
  • A 1% move in stock → ~2.2% move in option
  • Prob of expiring ITM: 34.8%
  • Losing $0.02/share per day to time decay
  • Efficiency 6.74 = Average
```

**Required flags:**
- `--calc`: enable calculator mode
- `-s, --spot`: current stock price
- `-k, --strike`: strike price
- `-p, --price`: option price (use mid-price for accuracy)
- `-d, --dte`: days to expiry
- `--call` or `--put`: option type
- `--iv` **or** `--delta`: implied volatility (decimal) or delta from broker

---

## Options Listing

```shell
fplot <ticker> --call                          # calls, 6 month max (default)
fplot <ticker> --put                           # puts, 6 month max
fplot <ticker> --call --max 3m                 # calls expiring within 3 months
fplot <ticker> --call --all                    # all available expiries
fplot <ticker> --call --min-dte 1y             # long-dated calls (1+ year)
fplot <ticker> --call --all --sort leverage    # sorted by highest leverage
fplot <ticker> --call --all --sort prob        # sorted by highest prob ITM
fplot <ticker> --call --all --sort efficiency  # sorted by best efficiency score
```

### `--sort` options

| Value | Sorts by | Best for |
|---|---|---|
| `return` | CAGR (calls) / AR (puts) ascending | Default — cheapest hurdle first |
| `leverage` | Implied leverage descending | Finding highest bang-for-buck |
| `prob` | Prob ITM descending | Finding highest-confidence options |
| `efficiency` | Efficiency percentile descending | Best composite score |
| `dte` | Days to expiry ascending | Comparing by expiration |
| `strike` | Strike price ascending | Scanning the chain top to bottom |
| `volume` | Volume descending | Liquidity-first |

### Expiry filtering

| Flag | Default | Description |
|---|---|---|
| `--max <time>` | `6m` | Only show options expiring within this window |
| `--min-dte <time>` | — | Exclude options with fewer than this many days (implies `--all`) |
| `--all` | off | Show all available expiries, ignore `--max` |

Time expressions: `30d`, `2w`, `3m`, `6m`, `1y`, `2y`, or plain integer days.

### Advanced filtering (`--filter`)

```bash
# Single condition
fplot IBIT --call --all --filter "prob>0.30"

# AND (comma)
fplot IBIT --call --all --filter "lev>8, dte>180"

# OR (plus)
fplot IBIT --call --all --filter "dte<30 + dte>300"

# Compound
fplot IBIT --call --all --filter "lev>10, theta>-0.05, prob>0.20" --sort leverage
```

**All filterable fields:**

| Field | Aliases | Description |
|---|---|---|
| `dte` | — | Days to expiry |
| `volume` | — | Contract volume |
| `price` | — | Mid-price (bid+ask)/2 |
| `mid` | — | Same as `price` (explicit mid-price) |
| `return` | `ret`, `ar` | CAGR (calls) or annualized return (puts) |
| `strike_pct` | `sp` | Strike % above/below spot (+= above, −= below) |
| `lt_days` | — | Days since last trade (filter stale contracts) |
| `leverage` | `lev` | Implied leverage Ω |
| `efficiency` | `eff` | Efficiency percentile (0–100) |
| `prob` | `prob_itm` | Probability of expiring ITM (0.0–1.0) |
| `theta` | `th` | Daily theta decay in $/share (negative) |
| `vega` | — | $/share per 1% absolute IV move |
| `gamma` | — | Delta change per $1 stock move |
| `iv` | — | Implied volatility (decimal, e.g. 0.30 = 30%) |

**Operators:** `>`, `<`, `>=`, `<=`, `=`, `!=`

**Examples:**
```bash
--filter "prob>0.30"              # >30% chance of expiring ITM
--filter "lev>8, dte>180"         # high leverage + time
--filter "iv<0.50"                # relatively cheap IV
--filter "mid<5.0, prob>0.25"     # under $5 with decent odds
--filter "theta>-0.03"            # slow decay (less than $0.03/day)
--filter "eff>70, prob>0.25"      # top efficiency + reasonable odds
--filter "dte>1y"                 # time expressions work too
--filter "lt_days<=7"             # traded in the last week (liquid)
```

---

## Stock Plotting

```shell
fplot <ticker> [--since <date>] [--interval <interval>]
```

```shell
fplot AAPL
fplot AAPL --since 2020
fplot AAPL,TSLA --since "mar 2023"
fplot SPY --since 5y --interval 1wk
```

Compares the ticker against SPY, plots normalized price and drawdowns, and prints CAGR and
rolling median 1-year / 3-year return.

---

## Web Interface

```shell
fplot AAPL --web           # opens browser at http://127.0.0.1:8000
fplot AAPL --web --port 9000
```

Interactive chart with moving averages, RSI, and MACD.

---

## Options data caching

Yahoo Finance options data is cached to `~/.cache/grynn_fplot/` for 1 hour to avoid
redundant API calls when you run multiple scans on the same ticker in quick succession.
