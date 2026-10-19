
from matching import MatchingEngine, Trade, Ack, Cancelled

BUY = 0
SELL = 1


def show_events(events):
    for event in events:
        if isinstance(event, Ack):
            print(f"Order accepted: ID={event.order_id}")

        elif isinstance(event, Trade):
            print(
                f"TRADE | Price={event.price} | "
                f"Quantity={event.quantity} | "
                f"Maker={event.maker_id} | Taker={event.taker_id}"
            )

        elif isinstance(event, Cancelled):
            print(
                f"Order cancelled: ID={event.order_id} | "
                f"Remaining quantity={event.quantity}"
            )

        else:
            print(f"Event: {event}")


def main():
    engine = MatchingEngine()

    print("=== Limit Order Book & Matching Engine Demo ===\n")

    # 1. Add resting sell orders.
    print("1. Submit SELL orders")
    show_events(engine.matching_order(101, SELL, 10))
    show_events(engine.matching_order(102, SELL, 5))

    # 2. Submit a BUY order that matches the best ask.
    print("\n2. Submit BUY order at price 101")
    show_events(engine.matching_order(101, BUY, 6))

    # 3. Submit a market BUY order.
    print("\n3. Submit MARKET BUY order")
    show_events(engine.market_order(BUY, 3))

    # 4. Add a resting BUY order and cancel it.
    print("\n4. Submit and cancel a BUY order")
    events = engine.matching_order(95, BUY, 4)
    show_events(events)

    order_id = events[0].order_id
    show_events(engine.cancel_order(order_id))

    # 5. Display the remaining order book.
    print("\n5. Final Order Book")
    print(f"Best bid: {engine.book.best_bid()}")
    print(f"Best ask: {engine.book.best_ask()}")


if __name__ == "__main__":
    main()
