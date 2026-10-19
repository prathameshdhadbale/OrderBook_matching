
from matching import MatchingEngine, Ack, Trade, Cancelled


BUY = 0
SELL = 1


def get_trades(events):
    """Return trades in the order emitted by the matching engine."""
    return [
        event
        for event in events
        if isinstance(event, Trade)
    ]


def get_ack(events):
    """Return the acknowledgement, if present."""
    return next(
        (event for event in events if isinstance(event, Ack)),
        None,
    )


def book_snapshot(engine):
    """Return all resting orders in deterministic price/FIFO order."""
    result = []

    for side, levels in (
        (BUY, engine.book.bid_level),
        (SELL, engine.book.ask_level),
    ):
        prices = sorted(
            levels,
            reverse=(side == BUY),
        )

        for price in prices:
            for order in levels[price]:
                result.append(
                    (
                        order.id,
                        order.side,
                        order.price,
                        order.quantity,
                    )
                )

    return result


def assert_book_not_crossed(engine):
    best_bid = engine.book.best_bid()
    best_ask = engine.book.best_ask()

    if best_bid is not None and best_ask is not None:
        assert best_bid < best_ask


def test_fok_fills_across_multiple_price_levels():
    """FOK should completely fill when eligible liquidity is sufficient."""
    engine = MatchingEngine()

    first = engine.matching_order(101, SELL, 2)
    second = engine.matching_order(102, SELL, 3)

    first_id = get_ack(first).order_id
    second_id = get_ack(second).order_id

    events = engine.fok_order(102, BUY, 4)

    trades = get_trades(events)

    assert [(t.maker_id, t.price, t.quantity) for t in trades] == [
        (first_id, 101, 2),
        (second_id, 102, 2),
    ]

    assert engine.book.quantity_in_ask(101) == 0
    assert engine.book.quantity_in_ask(102) == 1
    assert_book_not_crossed(engine)


def test_failed_fok_leaves_existing_book_unchanged():
    """An unfillable FOK must not consume liquidity or rest in the book."""
    engine = MatchingEngine()

    engine.matching_order(101, SELL, 2)
    engine.matching_order(102, SELL, 1)

    before = book_snapshot(engine)
    trade_count_before = len(engine.trade_book)

    events = engine.fok_order(102, BUY, 4)

    assert get_trades(events) == []
    assert any(isinstance(event, Cancelled) for event in events)

    assert book_snapshot(engine) == before
    assert len(engine.trade_book) == trade_count_before
    assert_book_not_crossed(engine)


def test_price_changing_modification_can_execute_trade():
    """A modified order crossing the spread should match eligible liquidity."""
    engine = MatchingEngine()

    buy_events = engine.matching_order(100, BUY, 2)
    sell_events = engine.matching_order(110, SELL, 2)

    buy_id = get_ack(buy_events).order_id
    sell_id = get_ack(sell_events).order_id

    # Reprice the resting SELL from 110 to 100.
    events = engine.modify_order(sell_id, 100, 2)

    ack = get_ack(events)
    trades = get_trades(events)

    assert ack is not None
    assert ack.order_id != sell_id

    assert [
        (t.maker_id, t.taker_id, t.price, t.quantity)
        for t in trades
    ] == [
        (buy_id, ack.order_id, 100, 2)
    ]

    assert book_snapshot(engine) == []
    assert_book_not_crossed(engine)


def test_quantity_increase_preserves_id_but_loses_fifo_priority():
    """Increasing quantity at the same price moves an order to queue end."""
    engine = MatchingEngine()

    first_events = engine.matching_order(100, BUY, 2)
    second_events = engine.matching_order(100, BUY, 3)

    first_id = get_ack(first_events).order_id
    second_id = get_ack(second_events).order_id

    events = engine.modify_order(first_id, None, 4)

    assert get_ack(events).order_id == first_id

    queue = engine.book.bid_level[100]

    assert [order.id for order in queue] == [
        second_id,
        first_id,
    ]

    assert queue[1].quantity == 4
    assert_book_not_crossed(engine)


def test_quantity_decrease_preserves_id_and_fifo_priority():
    """Decreasing quantity at the same price retains the queue position."""
    engine = MatchingEngine()

    first_events = engine.matching_order(100, BUY, 5)
    second_events = engine.matching_order(100, BUY, 3)

    first_id = get_ack(first_events).order_id
    second_id = get_ack(second_events).order_id

    events = engine.modify_order(first_id, None, 2)

    assert get_ack(events).order_id == first_id

    queue = engine.book.bid_level[100]

    assert [order.id for order in queue] == [
        first_id,
        second_id,
    ]

    assert queue[0].quantity == 2
    assert_book_not_crossed(engine)


def test_market_order_discards_unfilled_remainder():
    """A market order consumes available liquidity and never rests."""
    engine = MatchingEngine()

    first_events = engine.matching_order(100, SELL, 2)
    second_events = engine.matching_order(101, SELL, 1)

    first_id = get_ack(first_events).order_id
    second_id = get_ack(second_events).order_id

    events = engine.market_order(BUY, 5)

    assert [
        (t.maker_id, t.price, t.quantity)
        for t in get_trades(events)
    ] == [
        (first_id, 100, 2),
        (second_id, 101, 1),
    ]

    # Available liquidity was 3; the remaining 2 must not rest.
    assert book_snapshot(engine) == []
    assert_book_not_crossed(engine)


def test_same_price_orders_execute_in_fifo_order():
    """Earlier orders at the same price must fill before later orders."""
    engine = MatchingEngine()

    first_events = engine.matching_order(100, SELL, 2)
    second_events = engine.matching_order(100, SELL, 3)

    first_id = get_ack(first_events).order_id
    second_id = get_ack(second_events).order_id

    events = engine.market_order(BUY, 4)

    assert [
        (t.maker_id, t.price, t.quantity)
        for t in get_trades(events)
    ] == [
        (first_id, 100, 2),
        (second_id, 100, 2),
    ]

    # The second SELL order has one unit remaining.
    assert engine.book.quantity_in_ask(100) == 1
    assert [
        order.id for order in engine.book.ask_level[100]
    ] == [second_id]

    assert_book_not_crossed(engine)

