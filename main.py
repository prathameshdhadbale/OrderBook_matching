
from order_book import Order_Book


def main():
    book = Order_Book()

    # 1. Add BUY orders (side = 0)
    buy1 = book.order_details(100, 0, 10)
    buy2 = book.order_details(105, 0, 20)
    buy3 = book.order_details(100, 0, 15)

    # 2. Add SELL orders (side = 1)
    sell1 = book.order_details(110, 1, 12)
    sell2 = book.order_details(108, 1, 25)
    sell3 = book.order_details(110, 1, 18)

    print("=== ORDER BOOK ===")

    # 3. Display BUY orders
    print("\nBUY SIDE:")
    for price in sorted(book.bid_level.keys(), reverse=True):
        orders = book.bid_level[price]
        print(f"Price: {price}, Total Quantity: {book.quantity_in_bid(price)}")

        for order in orders:
            print(
                f"  ID: {order.id}, "
                f"Quantity: {order.quantity}, "
                f"Sequence: {order.sequence_no}"
            )

    # 4. Display SELL orders
    print("\nSELL SIDE:")
    for price in sorted(book.ask_level.keys()):
        orders = book.ask_level[price]
        print(f"Price: {price}, Total Quantity: {book.quantity_in_ask(price)}")

        for order in orders:
            print(
                f"  ID: {order.id}, "
                f"Quantity: {order.quantity}, "
                f"Sequence: {order.sequence_no}"
            )

    # 5. Query best prices
    print("\n=== BEST PRICES ===")
    print("Best Bid:", book.best_bid())
    print("Best Ask:", book.best_ask())

    # 6. Query quantity at a price
    print("\n=== QUANTITY QUERIES ===")
    print("BUY quantity at 100:", book.quantity_in_bid(100))
    print("SELL quantity at 110:", book.quantity_in_ask(110))

    # 7. Look up an order
    print("\n=== ORDER LOOKUP ===")
    order = book.get_order(buy2.id)
    print("Order found:", order)

    # 8. Cancel a BUY order
    print("\n=== CANCELLATION ===")
    book.cancel_order(buy2.id)
    print(f"Cancelled BUY order ID: {buy2.id}")
    print("Order after cancellation:", book.get_order(buy2.id))
    print("New Best Bid:", book.best_bid())

    # 9. Cancel a SELL order
    book.cancel_order(sell2.id)
    print(f"Cancelled SELL order ID: {sell2.id}")
    print("New Best Ask:", book.best_ask())

    # 10. Display final state
    print("\n=== FINAL STATE ===")
    print("Active order IDs:", list(book.order_lookup.keys()))
    print("Bid price levels:", book.bid_level)
    print("Ask price levels:", book.ask_level)


if __name__ == "__main__":
    main()
