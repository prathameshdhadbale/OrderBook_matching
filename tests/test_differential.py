
from dataclasses import dataclass

from hypothesis import given, settings, strategies as st

from matching import MatchingEngine, Ack, Trade


BUY = 0
SELL = 1


@dataclass
class RefOrder:
    order_id: int
    price: int
    side: int
    quantity: int


class ReferenceBook:
    """Simple reference implementation using lists instead of heaps."""

    def __init__(self):
        self.orders: list[RefOrder] = []

    def eligible(self, price, side):
        """Return eligible opposite-side orders in price-time priority."""
        if side == BUY:
            candidates = [
                order
                for order in self.orders
                if order.side == SELL
                and (price is None or order.price <= price)
            ]

            # Stable sorting preserves FIFO for equal prices.
            return sorted(candidates, key=lambda order: order.price)

        candidates = [
            order
            for order in self.orders
            if order.side == BUY
            and (price is None or order.price >= price)
        ]

        # Stable sorting preserves FIFO for equal prices.
        return sorted(candidates, key=lambda order: -order.price)

    def execute(self, order_id, price, side, quantity, tif="GTC"):
        """
        Simulate an incoming order.

        GTC: execute eligible quantity and rest any remainder.
        MARKET: execute eligible quantity and discard the remainder.
        IOC: execute eligible quantity and discard the remainder.
        FOK: execute only if the full quantity can be filled.
        """
        candidates = self.eligible(price, side)

        if tif == "FOK":
            available = sum(order.quantity for order in candidates)

            if available < quantity:
                return []

        remaining = quantity
        trades = []

        for maker in candidates:
            if remaining == 0:
                break

            traded = min(remaining, maker.quantity)

            trades.append(
                (
                    maker.order_id,
                    order_id,
                    maker.price,
                    traded,
                )
            )

            maker.quantity -= traded
            remaining -= traded

            if maker.quantity == 0:
                self.orders.remove(maker)

        # Only GTC limit orders rest in this project.
        if remaining > 0 and tif == "GTC":
            self.orders.append(
                RefOrder(
                    order_id=order_id,
                    price=price,
                    side=side,
                    quantity=remaining,
                )
            )

        return trades

    def cancel(self, order_id):
        """Remove a resting order and return whether it existed."""
        order = next(
            (
                order
                for order in self.orders
                if order.order_id == order_id
            ),
            None,
        )

        if order is None:
            return False

        self.orders.remove(order)
        return True

    def modify(self, old_id, new_id, price, quantity):
        """
        Simulate the current MatchingEngine.modify_order() behavior.

        Price change:
            Remove the old order and submit a new GTC limit order.
            This can execute trades.

        Same price, quantity increase:
            Preserve ID but lose FIFO priority.

        Same price, quantity decrease:
            Preserve ID and FIFO priority.

        No change:
            Preserve the existing order.
        """
        order = next(
            (
                order
                for order in self.orders
                if order.order_id == old_id
            ),
            None,
        )

        if order is None:
            return []

        # None means retain the current price.
        new_price = order.price if price is None else price

        # No-op modification.
        if (
            new_price == order.price
            and quantity == order.quantity
        ):
            return []

        # A price change replaces the old order and runs matching.
        if new_price != order.price:
            side = order.side
            self.orders.remove(order)

            return self.execute(
                order_id=new_id,
                price=new_price,
                side=side,
                quantity=quantity,
                tif="GTC",
            )

        # Same price, increased quantity: lose FIFO priority.
        if quantity > order.quantity:
            self.orders.remove(order)
            order.quantity = quantity
            self.orders.append(order)

        else:
            # Same price, decreased quantity: retain FIFO priority.
            order.quantity = quantity

        return []

    def snapshot(self):
        """Return the resting book in deterministic price/FIFO order."""
        result = []

        for side in (BUY, SELL):
            side_orders = [
                order
                for order in self.orders
                if order.side == side
            ]

            prices = sorted(
                {order.price for order in side_orders},
                reverse=(side == BUY),
            )

            for price in prices:
                # The original list order preserves FIFO at each price.
                for order in side_orders:
                    if order.price == price:
                        result.append(
                            (
                                order.order_id,
                                order.side,
                                order.price,
                                order.quantity,
                            )
                        )

        return result


def engine_snapshot(engine):
    """Read the actual price levels and FIFO queues from the engine."""
    book = engine.book
    result = []

    for side, levels in (
        (BUY, book.bid_level),
        (SELL, book.ask_level),
    ):
        prices = sorted(
            levels.keys(),
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


def event_trades(events):
    """Extract trades in the order emitted by the engine."""
    return [
        (
            event.maker_id,
            event.taker_id,
            event.price,
            event.quantity,
        )
        for event in events
        if isinstance(event, Trade)
    ]


def assert_same_book(engine, reference):
    assert engine_snapshot(engine) == reference.snapshot()


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
def test_random_operations_against_reference(operations):
    engine = MatchingEngine()
    reference = ReferenceBook()
    known_ids = []

    for operation, price, side, quantity in operations:

        if operation in ("limit", "market", "ioc", "fok"):

            if operation == "limit":
                events = engine.matching_order(price, side, quantity)
                tif = "GTC"
                ref_price = price

            elif operation == "market":
                events = engine.market_order(side, quantity)
                tif = "MARKET"
                ref_price = None

            elif operation == "ioc":
                events = engine.ioc_order(price, side, quantity)
                tif = "IOC"
                ref_price = price

            else:
                events = engine.fok_order(price, side, quantity)
                tif = "FOK"
                ref_price = price

            ack = next(
                (
                    event
                    for event in events
                    if isinstance(event, Ack)
                ),
                None,
            )

            if ack is not None:
                order_id = ack.order_id
                known_ids.append(order_id)

                expected_trades = reference.execute(
                    order_id=order_id,
                    price=ref_price,
                    side=side,
                    quantity=quantity,
                    tif=tif,
                )

                assert event_trades(events) == expected_trades

        elif operation == "cancel":

            if known_ids:
                order_id = known_ids[price % len(known_ids)]
            else:
                order_id = 999999

            engine.cancel_order(order_id)
            reference.cancel(order_id)

        elif operation == "modify":

            current_ids = list(engine.book.order_lookup)

            if current_ids:
                old_id = current_ids[price % len(current_ids)]

                events = engine.modify_order(
                    old_id,
                    price,
                    quantity,
                )

                ack = next(
                    (
                        event
                        for event in events
                        if isinstance(event, Ack)
                    ),
                    None,
                )

                if ack is not None:
                    expected_trades = reference.modify(
                        old_id=old_id,
                        new_id=ack.order_id,
                        price=price,
                        quantity=quantity,
                    )

                    # A price-changing modification may execute trades.
                    assert event_trades(events) == expected_trades

                    known_ids.append(ack.order_id)

        # Check book consistency after every operation.
        assert_same_book(engine, reference)
