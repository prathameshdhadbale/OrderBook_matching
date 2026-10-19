
import random
import statistics
import time
from collections.abc import Callable

from matching import MatchingEngine


BUY = 0
SELL = 1

DEFAULT_TRIALS = 5
DEFAULT_ORDER_COUNT = 10_000


# ============================================================
# 1. MEASUREMENT
# ============================================================

def measure(
    prepare_trial: Callable[[], Callable[[], None]],
    operations: int,
    trials: int = DEFAULT_TRIALS,
):
    """Measure median runtime and throughput across fresh trials."""
    if trials <= 0:
        raise ValueError("trials must be positive")
    if operations <= 0:
        raise ValueError("operations must be positive")

    elapsed_times = []

    for _ in range(trials):
        # Prepare the engine and its initial state outside timing.
        run_workload = prepare_trial()

        start = time.perf_counter_ns()
        run_workload()
        end = time.perf_counter_ns()

        elapsed = (end - start) / 1_000_000_000

        if elapsed <= 0:
            raise RuntimeError("Measured duration must be positive")

        elapsed_times.append(elapsed)

    median_elapsed = statistics.median(elapsed_times)

    if median_elapsed <= 0:
        raise RuntimeError("Median duration must be positive")

    throughput = operations / median_elapsed
    return median_elapsed, throughput


def report(name: str, elapsed: float, throughput: float, operations: int):
    print(f"\nBenchmark: {name}")
    print(f"Operations per trial: {operations:,}")
    print(f"Median elapsed time: {elapsed:.6f} seconds")
    print(f"Throughput: {throughput:,.2f} operations/second")


# ============================================================
# 2. DETERMINISTIC INPUT GENERATION
# ============================================================

def generate_limit_orders(number_of_orders: int):
    """Generate deterministic, non-crossing limit-order inputs."""
    if number_of_orders <= 0:
        raise ValueError("number_of_orders must be positive")

    rng = random.Random(42)
    orders = []

    for _ in range(number_of_orders):
        side = rng.randint(BUY, SELL)

        if side == BUY:
            price = rng.randint(75, 95)
        else:
            price = rng.randint(100, 120)

        quantity = rng.randint(20, 60)
        orders.append((price, side, quantity))

    return orders


# ============================================================
# 3. LIMIT-ORDER INSERTION
# ============================================================

def prepare_insertion_trial(orders):
    """Time submission of non-crossing orders to a fresh engine."""
    engine = MatchingEngine()

    def run():
        for price, side, quantity in orders:
            engine.matching_order(price, side, quantity)

    return run


def benchmark_insertion(number_of_orders: int, trials: int):
    orders = generate_limit_orders(number_of_orders)

    elapsed, throughput = measure(
        lambda: prepare_insertion_trial(orders),
        operations=number_of_orders,
        trials=trials,
    )

    report("Limit-order insertion", elapsed, throughput, number_of_orders)


# ============================================================
# 4. SINGLE-LEVEL MATCHING
# ============================================================

def prepare_single_level_trial(number_of_orders: int):
    """Preload resting sells; time incoming buys at the same price."""
    engine = MatchingEngine()

    for _ in range(number_of_orders):
        engine.matching_order(100, SELL, 10)

    def run():
        for _ in range(number_of_orders):
            engine.matching_order(100, BUY, 10)

    return run


def benchmark_single_level(number_of_orders: int, trials: int):
    elapsed, throughput = measure(
        lambda: prepare_single_level_trial(number_of_orders),
        operations=number_of_orders,
        trials=trials,
    )

    report("Single-level matching", elapsed, throughput, number_of_orders)


# ============================================================
# 5. MULTI-LEVEL MATCHING
# ============================================================

def prepare_multi_level_trial(
    cycles: int,
    levels_per_order: int,
    quantity_per_level: int = 10,
):
    """Preload distinct sell levels and time buys that consume them."""
    if cycles <= 0:
        raise ValueError("cycles must be positive")
    if levels_per_order <= 1:
        raise ValueError("levels_per_order must exceed one")
    if quantity_per_level <= 0:
        raise ValueError("quantity_per_level must be positive")

    engine = MatchingEngine()

    # Every cycle uses a separate range of prices.
    for cycle in range(cycles):
        base_price = 100 + cycle * levels_per_order

        for level in range(levels_per_order):
            engine.matching_order(
                base_price + level,
                SELL,
                quantity_per_level,
            )

    def run():
        for cycle in range(cycles):
            base_price = 100 + cycle * levels_per_order
            limit_price = base_price + levels_per_order - 1
            quantity = levels_per_order * quantity_per_level

            engine.matching_order(limit_price, BUY, quantity)

    return run


def benchmark_multi_level(cycles: int, levels_per_order: int, trials: int):
    elapsed, throughput = measure(
        lambda: prepare_multi_level_trial(cycles, levels_per_order),
        operations=cycles,
        trials=trials,
    )

    report(
        f"Multi-level matching ({levels_per_order} levels per buy)",
        elapsed,
        throughput,
        cycles,
    )


def validate_multi_level_matching(
    cycles: int = 10,
    levels_per_order: int = 5,
    quantity_per_level: int = 10,
):
    """Validate trade prices, quantities and final book state."""
    if cycles <= 0:
        raise ValueError("cycles must be positive")
    if levels_per_order <= 1:
        raise ValueError("levels_per_order must exceed one")
    if quantity_per_level <= 0:
        raise ValueError("quantity_per_level must be positive")

    engine = MatchingEngine()

    # Insert resting sells.
    for cycle in range(cycles):
        base_price = 100 + cycle * levels_per_order

        for level in range(levels_per_order):
            engine.matching_order(
                base_price + level,
                SELL,
                quantity_per_level,
            )

    # Execute one buy per cycle, consuming all levels in that cycle.
    for cycle in range(cycles):
        base_price = 100 + cycle * levels_per_order
        limit_price = base_price + levels_per_order - 1
        quantity = levels_per_order * quantity_per_level

        engine.matching_order(limit_price, BUY, quantity)

    expected_trades = cycles * levels_per_order

    assert len(engine.trade_book) == expected_trades, (
        f"Expected {expected_trades} trades, got {len(engine.trade_book)}"
    )

    # Verify each trade's price and quantity.
    for cycle in range(cycles):
        base_price = 100 + cycle * levels_per_order

        trades = engine.trade_book[
            cycle * levels_per_order:
            (cycle + 1) * levels_per_order
        ]

        expected_prices = [
            base_price + level for level in range(levels_per_order)
        ]
        actual_prices = [trade.price for trade in trades]
        actual_quantities = [trade.quantity for trade in trades]

        assert actual_prices == expected_prices, (
            f"Cycle {cycle}: expected prices {expected_prices}, "
            f"got {actual_prices}"
        )

        assert actual_quantities == [quantity_per_level] * levels_per_order, (
            f"Cycle {cycle}: unexpected quantities {actual_quantities}"
        )

    assert not engine.book.ask_level, (
        f"Unexpected resting asks: {engine.book.ask_level}"
    )
    assert not engine.book.bid_level, (
        f"Unexpected resting bids: {engine.book.bid_level}"
    )

    print("\nMulti-level matching validation: PASS")
    print(f"Cycles validated: {cycles}")
    print(f"Price levels per BUY: {levels_per_order}")
    print(f"Expected trades: {expected_trades}")
    print("Trade prices and quantities verified.")
    print("No resting orders remain.")


# ============================================================
# 6. PARTIAL FILLS
# ============================================================

def prepare_partial_fill_trial(number_of_orders: int):
    """Repeatedly partially fill one large resting sell order."""
    engine = MatchingEngine()
    engine.matching_order(100, SELL, number_of_orders + 1)

    def run():
        for _ in range(number_of_orders):
            engine.matching_order(100, BUY, 1)

    return run


def benchmark_partial_fills(number_of_orders: int, trials: int):
    elapsed, throughput = measure(
        lambda: prepare_partial_fill_trial(number_of_orders),
        operations=number_of_orders,
        trials=trials,
    )

    report("Partial fills", elapsed, throughput, number_of_orders)


# ============================================================
# 7. CANCELLATION
# ============================================================

def prepare_cancellation_trial(number_of_orders: int):
    """Preload orders and time their cancellation."""
    engine = MatchingEngine()
    order_ids = []

    for i in range(number_of_orders):
        price = 75 + (i % 21)
        events = engine.matching_order(price, BUY, 20)
        order_ids.append(events[0].order_id)

    def run():
        for order_id in order_ids:
            engine.cancel_order(order_id)

    return run


def benchmark_cancellation(number_of_orders: int, trials: int):
    elapsed, throughput = measure(
        lambda: prepare_cancellation_trial(number_of_orders),
        operations=number_of_orders,
        trials=trials,
    )

    report("Order cancellation", elapsed, throughput, number_of_orders)


# ============================================================
# 8. MODIFICATION
# ============================================================

def prepare_modification_trial(number_of_orders: int):
    """Preload orders and time same-price quantity decreases."""
    engine = MatchingEngine()
    order_ids = []

    for i in range(number_of_orders):
        price = 75 + (i % 21)
        events = engine.matching_order(price, BUY, 20)
        order_ids.append(events[0].order_id)

    def run():
        for order_id in order_ids:
            engine.modify_order(order_id, None, 10)

    return run


def benchmark_modification(number_of_orders: int, trials: int):
    elapsed, throughput = measure(
        lambda: prepare_modification_trial(number_of_orders),
        operations=number_of_orders,
        trials=trials,
    )

    report(
        "Order modification (quantity decrease)",
        elapsed,
        throughput,
        number_of_orders,
    )


# ============================================================
# 9. BOOK-SIZE SCALING
# ============================================================

def benchmark_book_sizes(sizes, trials: int):
    print("\n" + "=" * 60)
    print("BOOK-SIZE SCALING")
    print("=" * 60)
    print(f"{'Orders':>12} | {'Median (s)':>12} | {'Orders/s':>16}")
    print("-" * 48)

    for size in sizes:
        orders = generate_limit_orders(size)

        elapsed, throughput = measure(
            lambda orders=orders: prepare_insertion_trial(orders),
            operations=size,
            trials=trials,
        )

        print(f"{size:>12,} | {elapsed:>12.6f} | {throughput:>16,.2f}")


# ============================================================
# 10. RUN THE COMPLETE SUITE
# ============================================================

if __name__ == "__main__":
    trials = DEFAULT_TRIALS
    number_of_orders = DEFAULT_ORDER_COUNT

    print("=" * 60)
    print("ORDER BOOK AND MATCHING ENGINE BENCHMARKS")
    print("=" * 60)
    print(f"Trials per benchmark: {trials}")
    print(f"Default order count: {number_of_orders:,}")

    # Validate matching correctness before measuring performance.
    validate_multi_level_matching(
        cycles=10,
        levels_per_order=5,
        quantity_per_level=10,
    )

    benchmark_insertion(number_of_orders, trials)
    benchmark_single_level(number_of_orders, trials)

    benchmark_multi_level(
        cycles=1_000,
        levels_per_order=5,
        trials=trials,
    )

    benchmark_partial_fills(number_of_orders, trials)
    benchmark_cancellation(number_of_orders, trials)
    benchmark_modification(number_of_orders, trials)

    benchmark_book_sizes(
        sizes=[1_000, 5_000, 10_000, 25_000],
        trials=trials,
    )

    print("\n" + "=" * 60)
    print("ALL BENCHMARKS COMPLETED")
    print("=" * 60)
