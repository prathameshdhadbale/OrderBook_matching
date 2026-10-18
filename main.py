from matching import MatchingEngine, Ack, Trade, Rejected


# ============================================================
# HELPERS
# ============================================================

def add_resting_order(engine, price, side, quantity):
    order = engine.book.create_order(price, side, quantity)
    engine.book.order_details(order, side)
    return order


def add_resting_buy(engine, price, quantity):
    return add_resting_order(engine, price, 0, quantity)


def add_resting_sell(engine, price, quantity):
    return add_resting_order(engine, price, 1, quantity)


def get_trades(events):
    return [event for event in events if isinstance(event, Trade)]


def check_book_consistency(engine):
    book = engine.book
    order_ids = []

    for price, orders in book.bid_level.items():
        assert orders, f"Empty bid level at {price}"
        for order in orders:
            assert order.side == 0
            assert order.price == price
            assert order.quantity > 0
            order_ids.append(order.id)

    for price, orders in book.ask_level.items():
        assert orders, f"Empty ask level at {price}"
        for order in orders:
            assert order.side == 1
            assert order.price == price
            assert order.quantity > 0
            order_ids.append(order.id)

    assert len(order_ids) == len(set(order_ids))
    assert set(order_ids) == set(book.order_lookup.keys())
    assert set(book.bid) == set(book.bid_level.keys())
    assert set(book.ask) == set(book.ask_level.keys())

    assert book.best_bid() == max(book.bid_level.keys(), default=None)
    assert book.best_ask() == min(book.ask_level.keys(), default=None)


# ============================================================
# BUY-SIDE MATCHING TESTS
# ============================================================

def test_buy_maker_quantity_greater():
    engine = MatchingEngine()
    maker = add_resting_sell(engine, 100, 10)

    events = engine.matching_order(100, 0, 4)

    assert isinstance(events[0], Ack)
    assert len(get_trades(events)) == 1
    assert maker.quantity == 6


def test_buy_equal_quantities():
    engine = MatchingEngine()
    maker = add_resting_sell(engine, 100, 5)

    events = engine.matching_order(100, 0, 5)

    assert len(get_trades(events)) == 1
    assert maker.id not in engine.book.order_lookup
    assert engine.book.best_ask() is None


def test_buy_maker_quantity_smaller():
    engine = MatchingEngine()
    maker = add_resting_sell(engine, 100, 3)

    events = engine.matching_order(110, 0, 5)

    assert sum(t.quantity for t in get_trades(events)) == 3
    assert maker.id not in engine.book.order_lookup
    assert engine.book.quantity_in_bid(110) == 2


def test_buy_multiple_price_levels():
    engine = MatchingEngine()
    add_resting_sell(engine, 100, 2)
    add_resting_sell(engine, 105, 3)

    events = engine.matching_order(110, 0, 4)
    trades = get_trades(events)

    assert [t.price for t in trades] == [100, 105]
    assert [t.quantity for t in trades] == [2, 2]
    assert engine.book.quantity_in_ask(105) == 1


def test_buy_fifo_same_price():
    engine = MatchingEngine()
    first = add_resting_sell(engine, 100, 2)
    second = add_resting_sell(engine, 100, 3)

    events = engine.matching_order(100, 0, 4)
    trades = get_trades(events)

    assert [t.maker_id for t in trades] == [first.id, second.id]
    assert [t.quantity for t in trades] == [2, 2]
    assert second.quantity == 1


def test_buy_ask_below_limit():
    engine = MatchingEngine()
    add_resting_sell(engine, 90, 2)

    events = engine.matching_order(100, 0, 2)

    assert get_trades(events)[0].price == 90


def test_buy_ask_equals_limit():
    engine = MatchingEngine()
    add_resting_sell(engine, 100, 2)

    events = engine.matching_order(100, 0, 2)

    assert len(get_trades(events)) == 1


def test_buy_ask_above_limit():
    engine = MatchingEngine()
    add_resting_sell(engine, 110, 2)

    events = engine.matching_order(100, 0, 2)

    assert get_trades(events) == []
    assert engine.book.quantity_in_bid(100) == 2


def test_buy_empty_ask_book():
    engine = MatchingEngine()

    events = engine.matching_order(100, 0, 5)

    assert get_trades(events) == []
    assert engine.book.quantity_in_bid(100) == 5


def test_buy_multiple_fills_with_remainder():
    engine = MatchingEngine()
    add_resting_sell(engine, 100, 2)
    add_resting_sell(engine, 101, 2)

    events = engine.matching_order(110, 0, 7)

    assert sum(t.quantity for t in get_trades(events)) == 4
    assert engine.book.quantity_in_bid(110) == 3


def test_buy_maker_sequence_preserved():
    engine = MatchingEngine()
    first = add_resting_sell(engine, 100, 5)
    second = add_resting_sell(engine, 100, 5)

    engine.matching_order(100, 0, 2)
    events = engine.matching_order(100, 0, 4)

    trades = get_trades(events)

    assert [t.maker_id for t in trades] == [first.id, second.id]
    assert [t.quantity for t in trades] == [3, 1]


# ============================================================
# SELL-SIDE MATCHING TESTS
# ============================================================

def test_sell_maker_quantity_greater():
    engine = MatchingEngine()
    maker = add_resting_buy(engine, 100, 10)

    events = engine.matching_order(100, 1, 4)

    assert len(get_trades(events)) == 1
    assert maker.quantity == 6


def test_sell_equal_quantities():
    engine = MatchingEngine()
    maker = add_resting_buy(engine, 100, 5)

    events = engine.matching_order(100, 1, 5)

    assert len(get_trades(events)) == 1
    assert maker.id not in engine.book.order_lookup
    assert engine.book.best_bid() is None


def test_sell_maker_quantity_smaller():
    engine = MatchingEngine()
    maker = add_resting_buy(engine, 110, 3)

    events = engine.matching_order(100, 1, 5)

    assert sum(t.quantity for t in get_trades(events)) == 3
    assert maker.id not in engine.book.order_lookup
    assert engine.book.quantity_in_ask(100) == 2


def test_sell_multiple_price_levels():
    engine = MatchingEngine()
    add_resting_buy(engine, 110, 2)
    add_resting_buy(engine, 105, 3)

    events = engine.matching_order(100, 1, 4)
    trades = get_trades(events)

    assert [t.price for t in trades] == [110, 105]
    assert [t.quantity for t in trades] == [2, 2]
    assert engine.book.quantity_in_bid(105) == 1


def test_sell_fifo_same_price():
    engine = MatchingEngine()
    first = add_resting_buy(engine, 100, 2)
    second = add_resting_buy(engine, 100, 3)

    events = engine.matching_order(100, 1, 4)
    trades = get_trades(events)

    assert [t.maker_id for t in trades] == [first.id, second.id]
    assert [t.quantity for t in trades] == [2, 2]
    assert second.quantity == 1


def test_sell_bid_below_limit():
    engine = MatchingEngine()
    add_resting_buy(engine, 90, 2)

    events = engine.matching_order(100, 1, 2)

    assert get_trades(events) == []
    assert engine.book.quantity_in_ask(100) == 2


def test_sell_bid_equals_limit():
    engine = MatchingEngine()
    add_resting_buy(engine, 100, 2)

    events = engine.matching_order(100, 1, 2)

    assert len(get_trades(events)) == 1


def test_sell_bid_above_limit():
    engine = MatchingEngine()
    add_resting_buy(engine, 110, 2)

    events = engine.matching_order(100, 1, 2)

    assert get_trades(events)[0].price == 110


def test_sell_empty_bid_book():
    engine = MatchingEngine()

    events = engine.matching_order(100, 1, 5)

    assert get_trades(events) == []
    assert engine.book.quantity_in_ask(100) == 5


# ============================================================
# INPUT VALIDATION TESTS
# ============================================================

def test_zero_quantity_rejected():
    engine = MatchingEngine()
    events = engine.matching_order(100, 0, 0)

    assert len(events) == 1
    assert isinstance(events[0], Rejected)
    assert engine.book.order_lookup == {}


def test_negative_quantity_rejected():
    engine = MatchingEngine()
    events = engine.matching_order(100, 0, -5)

    assert isinstance(events[0], Rejected)
    assert engine.book.order_lookup == {}


def test_zero_price_rejected():
    engine = MatchingEngine()
    events = engine.matching_order(0, 0, 5)

    assert isinstance(events[0], Rejected)
    assert engine.book.order_lookup == {}


def test_negative_price_rejected():
    engine = MatchingEngine()
    events = engine.matching_order(-100, 0, 5)

    assert isinstance(events[0], Rejected)
    assert engine.book.order_lookup == {}


def test_invalid_side_rejected():
    engine = MatchingEngine()
    events = engine.matching_order(100, 2, 5)

    assert isinstance(events[0], Rejected)
    assert engine.book.order_lookup == {}


def test_valid_buy_starts_with_ack():
    engine = MatchingEngine()
    events = engine.matching_order(100, 0, 5)

    assert isinstance(events[0], Ack)
    assert engine.book.quantity_in_bid(100) == 5


def test_valid_sell_starts_with_ack():
    engine = MatchingEngine()
    events = engine.matching_order(100, 1, 5)

    assert isinstance(events[0], Ack)
    assert engine.book.quantity_in_ask(100) == 5


# ============================================================
# ORDER-BOOK CONSISTENCY TESTS
# ============================================================

def test_complete_fill_consistency():
    engine = MatchingEngine()
    maker = add_resting_sell(engine, 100, 5)

    engine.matching_order(100, 0, 5)

    assert maker.id not in engine.book.order_lookup
    assert 100 not in engine.book.ask_level
    check_book_consistency(engine)


def test_partial_fill_consistency():
    engine = MatchingEngine()
    maker = add_resting_sell(engine, 100, 10)

    engine.matching_order(100, 0, 4)

    assert engine.book.get_order(maker.id).quantity == 6
    assert engine.book.quantity_in_ask(100) == 6
    check_book_consistency(engine)


def test_fifo_consistency_after_multiple_orders():
    engine = MatchingEngine()
    first = add_resting_sell(engine, 100, 3)
    second = add_resting_sell(engine, 100, 5)

    engine.matching_order(100, 0, 6)

    assert first.id not in engine.book.order_lookup
    assert engine.book.get_order(second.id).quantity == 2
    assert engine.book.ask_level[100][0].id == second.id
    check_book_consistency(engine)


# ============================================================
# EVENT TESTS
# ============================================================

def test_every_return_is_a_list():
    engine = MatchingEngine()

    results = [
        engine.matching_order(100, 0, 5),
        engine.matching_order(0, 0, 5),
        engine.matching_order(100, 2, 5),
    ]

    assert all(isinstance(result, list) for result in results)


def test_event_list_contains_event_objects():
    engine = MatchingEngine()
    add_resting_sell(engine, 100, 2)

    events = engine.matching_order(100, 0, 2)

    assert isinstance(events[0], Ack)
    assert all(
        isinstance(event, (Ack, Trade, Rejected))
        for event in events
    )


def test_trade_history_matches_emitted_trades():
    engine = MatchingEngine()
    add_resting_sell(engine, 100, 2)
    add_resting_sell(engine, 101, 3)

    events = engine.matching_order(105, 0, 5)

    assert get_trades(events) == engine.trade_book


# ============================================================
# TEST RUNNER
# ============================================================

tests = [
    test_buy_maker_quantity_greater,
    test_buy_equal_quantities,
    test_buy_maker_quantity_smaller,
    test_buy_multiple_price_levels,
    test_buy_fifo_same_price,
    test_buy_ask_below_limit,
    test_buy_ask_equals_limit,
    test_buy_ask_above_limit,
    test_buy_empty_ask_book,
    test_buy_multiple_fills_with_remainder,
    test_buy_maker_sequence_preserved,

    test_sell_maker_quantity_greater,
    test_sell_equal_quantities,
    test_sell_maker_quantity_smaller,
    test_sell_multiple_price_levels,
    test_sell_fifo_same_price,
    test_sell_bid_below_limit,
    test_sell_bid_equals_limit,
    test_sell_bid_above_limit,
    test_sell_empty_bid_book,

    test_zero_quantity_rejected,
    test_negative_quantity_rejected,
    test_zero_price_rejected,
    test_negative_price_rejected,
    test_invalid_side_rejected,
    test_valid_buy_starts_with_ack,
    test_valid_sell_starts_with_ack,

    test_complete_fill_consistency,
    test_partial_fill_consistency,
    test_fifo_consistency_after_multiple_orders,

    test_every_return_is_a_list,
    test_event_list_contains_event_objects,
    test_trade_history_matches_emitted_trades,
]


if __name__ == "__main__":
    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            print(f"PASS: {test.__name__}")
            passed += 1
        except Exception as error:
            print(f"FAIL: {test.__name__}")
            print(f"      {type(error).__name__}: {error}")
            failed += 1

    print("\n" + "=" * 45)
    print(f"Results: {passed}/{len(tests)} tests passed")
    print(f"Failed:  {failed}")
    print("=" * 45)
