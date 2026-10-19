# Order Book and Matching Engine

A Python limit order book and matching engine implementing **price-time priority**. It maintains resting orders, matches incoming orders, and produces deterministic events for trades, acknowledgements, cancellations, and rejections.

## Features

- **Order book:** Bid and ask sides organized by price level.
- **Price-time priority:** Best price executes first; orders at the same price execute FIFO.
- **Order types:** Limit, market, Immediate-or-Cancel (IOC), and Fill-or-Kill (FOK).
- **Order management:** Cancellation and modification of existing orders.
- **Trade execution:** Matches orders and records trades at the resting maker order's price.
- **Testing:** Unit tests, adversarial cases, property-based tests, and differential testing against a reference implementation.
- **Benchmarks:** Measures performance for insertion, matching, cancellation, modification, and different book sizes.

## Requirements

- Python 3.14 or later
- pip

## Installation

Clone the repository and enter the project directory:

```bash
git clone https://github.com/prathameshdhadbale/OrderBook_matching.git
cd OrderBook_matching
```

Install the project and development dependencies:

```bash
python -m pip install -e ".[dev]"
```

## Usage

Create a matching engine and submit orders:

```python
from matching import MatchingEngine

BUY = 0
SELL = 1

engine = MatchingEngine()

# Add a sell limit order at price 100 for quantity 10
events = engine.matching_order(price=100, side=SELL, quantity=10)
print(events)

# Submit a buy order at price 100 for quantity 5
events = engine.matching_order(price=100, side=BUY, quantity=5)
print(events)

# Inspect the best bid and ask
print("Best bid:", engine.book.best_bid())
print("Best ask:", engine.book.best_ask())
```

The buy order can match against the resting sell order at price 100. Returned events describe the operation and any resulting trades.

## Supported Operations

| Operation | Behavior |
|---|---|
| Limit order | Matches eligible resting orders; rests any remaining quantity |
| Market order | Executes against available liquidity; discards any unfilled remainder |
| IOC order | Executes immediately where possible; cancels the unfilled remainder |
| FOK order | Executes fully or is rejected without consuming existing liquidity |
| Cancel | Cancels an existing order |
| Modify | Changes an existing order's price or quantity, subject to priority rules |

Orders execute according to price-time priority. Trades execute at the resting order's price.

## Testing

Run the complete test suite:

```bash
python -m pytest -v
```

The tests cover matching rules, cancellation, partial fills, FIFO priority, FOK and IOC behavior, randomized operation sequences, and book invariants.

## Benchmarks

Run the benchmark suite:

```bash
python benchmarks/benchmark_matching.py
```

Benchmarks measure selected operations under synthetic workloads. Results depend on the machine, Python version, and workload; they are not exchange-grade latency guarantees.

## Project Structure

```text
OrderBook_matching/
├── benchmarks/
│   └── benchmark_matching.py
├── tests/
│   ├── test_adversarial.py
│   ├── test_differential.py
│   ├── test_matching_rules.py
│   └── test_properties.py
├── main.py
├── matching.py
├── order_book.py
├── pyproject.toml
├── requirements.txt
└── requirements-dev.txt
```

## Scope and Limitations

This project focuses on order book management, matching correctness, and data-structure behavior. It is a library project, not a complete exchange or trading platform.

It does not currently implement a network event loop, trading strategies, portfolio management, exchange connectivity, or production-grade concurrency and latency guarantees.