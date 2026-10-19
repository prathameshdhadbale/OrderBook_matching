
from hypothesis import given, settings, strategies as st

from matching import MatchingEngine


BUY = 0
SELL = 1


def assert_book_invariants(engine):
    book = engine.book
    resting_ids = []

    # Validate bid price levels and queues.
    for price, orders in book.bid_level.items():
        assert orders, f"Empty bid level: {price}"

        for order in orders:
            assert order.side == BUY
            assert order.price == price
            assert order.quantity > 0
            assert order.id not in resting_ids
            resting_ids.append(order.id)

    # Validate ask price levels and queues.
    for price, orders in book.ask_level.items():
        assert orders, f"Empty ask level: {price}"

        for order in orders:
            assert order.side == SELL
            assert order.price == price
            assert order.quantity > 0
            assert order.id not in resting_ids
            resting_ids.append(order.id)

    # Price-level queues and order lookup must contain the same orders.
    assert set(resting_ids) == set(book.order_lookup.keys())
    assert len(resting_ids) == len(set(resting_ids))

    for order_id, order in book.order_lookup.items():
        assert order.id == order_id
        assert order.quantity > 0

    # Heap entries are price keys in this implementation.
    assert set(book.bid) == set(book.bid_level.keys())
    assert set(book.ask) == set(book.ask_level.keys())

    # Best-price queries must agree with the available price levels.
    assert book.best_bid() == max(book.bid_level, default=None)
    assert book.best_ask() == min(book.ask_level, default=None)

    # A correctly matched resting book must not be crossed.
    best_bid = book.best_bid()
    best_ask = book.best_ask()

    if best_bid is not None and best_ask is not None:
        assert best_bid < best_ask


@given(
    operations=st.lists(
        st.tuples(
            st.sampled_from(
                ["limit", "market", "ioc", "fok", "cancel", "modify"]
            ),
            st.integers(min_value=1, max_value=20),
            st.integers(min_value=BUY, max_value=SELL),
            st.integers(min_value=1, max_value=20),
        ),
        min_size=1,
        max_size=150,
    )
)
@settings(max_examples=300, deadline=None)
def test_random_operation_sequences_preserve_invariants(operations):
    engine = MatchingEngine()

    for operation, price, side, quantity in operations:
        if operation == "limit":
            engine.matching_order(price, side, quantity)

        elif operation == "market":
            engine.market_order(side, quantity)

        elif operation == "ioc":
            engine.ioc_order(price, side, quantity)

        elif operation == "fok":
            engine.fok_order(price, side, quantity)

        elif operation == "cancel":
            # Include unknown IDs to exercise rejection handling.
            engine.cancel_order(price)

        elif operation == "modify":
            existing_ids = list(engine.book.order_lookup)

            if existing_ids:
                order_id = existing_ids[price % len(existing_ids)]
                engine.modify_order(order_id, price, quantity)

        assert_book_invariants(engine)
