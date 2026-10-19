
from matching import MatchingEngine, Ack, Trade, Cancelled, Rejected


BUY = 0
SELL = 1


def get_trades(events):
    return [event for event in events if isinstance(event, Trade)]


def add_resting_order(engine, price, side, quantity):
    order = engine.book.create_order(price, side, quantity)
    engine.book.order_details(order, side)
    return order


def test_repeated_cancellation_and_unknown_ids():
    engine = MatchingEngine()
    order = add_resting_order(engine, 100, BUY, 5)

    first = engine.cancel_order(order.id)
    second = engine.cancel_order(order.id)
    unknown = engine.cancel_order(999999)

    assert isinstance(first[0], Cancelled)
    assert isinstance(second[0], Rejected)
    assert isinstance(unknown[0], Rejected)
    assert order.id not in engine.book.order_lookup


def test_partial_fill_then_cancel_remainder():
    engine = MatchingEngine()
    maker = add_resting_order(engine, 100, SELL, 10)

    events = engine.matching_order(100, BUY, 4)

    assert sum(t.quantity for t in get_trades(events)) == 4
    assert maker.id in engine.book.order_lookup
    assert engine.book.get_order(maker.id).quantity == 6

    cancelled = engine.cancel_order(maker.id)

    assert isinstance(cancelled[0], Cancelled)
    assert maker.id not in engine.book.order_lookup
    assert 100 not in engine.book.ask_level


def test_empty_price_level_can_be_recreated():
    engine = MatchingEngine()

    first = add_resting_order(engine, 100, SELL, 2)
    events = engine.matching_order(100, BUY, 2)

    assert len(get_trades(events)) == 1
    assert first.id not in engine.book.order_lookup
    assert 100 not in engine.book.ask_level

    second = add_resting_order(engine, 100, SELL, 7)

    assert engine.book.ask_level[100] == [second]
    assert engine.book.quantity_in_ask(100) == 7


def test_fifo_survives_partial_fill_and_cancellation():
    engine = MatchingEngine()

    first = add_resting_order(engine, 100, SELL, 3)
    second = add_resting_order(engine, 100, SELL, 5)
    third = add_resting_order(engine, 100, SELL, 4)

    engine.cancel_order(second.id)

    events = engine.matching_order(100, BUY, 5)
    trades = get_trades(events)

    assert [trade.maker_id for trade in trades] == [
        first.id,
        third.id,
    ]
    assert [trade.quantity for trade in trades] == [3, 2]
    assert engine.book.ask_level[100][0].id == third.id
    assert engine.book.ask_level[100][0].quantity == 2


def test_very_large_quantity():
    engine = MatchingEngine()
    large_quantity = 10**12

    maker = add_resting_order(engine, 100, SELL, large_quantity)

    events = engine.matching_order(100, BUY, large_quantity - 1)

    trades = get_trades(events)

    assert len(trades) == 1
    assert trades[0].quantity == large_quantity - 1
    assert engine.book.get_order(maker.id).quantity == 1


def test_failed_fok_does_not_consume_liquidity():
    engine = MatchingEngine()
    first = add_resting_order(engine, 100, SELL, 3)
    second = add_resting_order(engine, 101, SELL, 2)

    events = engine.fok_order(101, BUY, 6)

    assert get_trades(events) == []
    assert engine.book.get_order(first.id).quantity == 3
    assert engine.book.get_order(second.id).quantity == 2
    assert engine.book.quantity_in_ask(100) == 3
    assert engine.book.quantity_in_ask(101) == 2


def test_ioc_partial_fill_does_not_rest_remainder():
    engine = MatchingEngine()
    maker = add_resting_order(engine, 100, SELL, 3)

    events = engine.ioc_order(100, BUY, 10)

    assert sum(t.quantity for t in get_trades(events)) == 3
    assert maker.id not in engine.book.order_lookup

    ack = next(event for event in events if isinstance(event, Ack))
    assert ack.order_id not in engine.book.order_lookup

    assert any(
        isinstance(event, Cancelled) and event.quantity == 7
        for event in events
    )
