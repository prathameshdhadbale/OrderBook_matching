from order_book import Order_Book


def main():

    # price = int(input())
    # side = int(input())
    # quantity = int(input())

    # order = Order_Book()
    # order.order_details(price,side,quantity)
    # print(order.id) 

    book = Order_Book()

    o1 = book.order_details(105, 1, 5)
    o2 = book.order_details(105, 1, 8)

    print("Best ask:", book.ask[0])




if __name__ == "__main__":
    main()