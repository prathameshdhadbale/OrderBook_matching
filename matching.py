from dataclasses import dataclass
from order_book import Order_Book

@dataclass(frozen=True)
class Ack:
    order_id:int
    response:str | None

@dataclass(frozen=True)
class Trade:
    maker_id:int
    taker_id:int
    price:int
    quantity:int

@dataclass(frozen=True)
class Cancelled:
    order_id:int
    quantity:int

@dataclass(frozen=True)
class Rejected:
    order_id: int | None
    reason : str

class MatchingEngine:
    def __init__(self):
        self.book = Order_Book()
        self.trade_book = []

    def matching_order(self,price:int,side:int,quantity:int):
        ret_list = []

        if quantity <= 0:
            ret_list.append(Rejected(None,"invalid Quantity"))
            return ret_list
        if price <= 0:
            ret_list.append(Rejected(None,"invalid Price"))
            return ret_list
            
            
        if side != 0 and side != 1 :
            ret_list.append(Rejected(None,"Choose either buy or sell"))
            return ret_list
            
        
        o = self.book.create_order(price, side, quantity)
        ret_list.append(Ack(o.id,None))

        if side == 0 : #Buy order

            while(o.quantity):

                best_ask = self.book.best_ask()
                if(best_ask is None):
                    break
                
                if(best_ask <= o.price):

                    while(best_ask in self.book.ask_level and o.quantity > 0 and  len(self.book.ask_level[best_ask]) != 0):

                        maker_quantity = self.book.ask_level[best_ask][0].quantity
                        maker_id = self.book.ask_level[best_ask][0].id
                        trade_quantity = min(o.quantity,maker_quantity)

                        trade = Trade(maker_id , o.id,best_ask,trade_quantity)
                        self.trade_book.append(trade)

                        o.quantity -= trade_quantity
                        self.book.ask_level[best_ask][0].quantity -= trade_quantity
                        ret_list.append(trade)

                        if(self.book.ask_level[best_ask][0].quantity == 0):
                            self.book.cancel_order(maker_id)


                else:
                    break
                
            if o.quantity > 0:
                self.book.order_details(o,o.side)
                return ret_list
        
        
        
        
        elif side == 1 : #ask order

            while(o.quantity):

                best_bid = self.book.best_bid()
                if(best_bid is None):
                    break
                
                if(best_bid >= o.price):

                    while(best_bid in self.book.bid_level and o.quantity > 0 and  len(self.book.bid_level[best_bid]) != 0):

                        maker_quantity = self.book.bid_level[best_bid][0].quantity
                        maker_id = self.book.bid_level[best_bid][0].id
                        trade_quantity = min(o.quantity,maker_quantity)

                        trade = Trade(maker_id , o.id,best_bid,trade_quantity)
                        self.trade_book.append(trade)

                        o.quantity -= trade_quantity
                        self.book.bid_level[best_bid][0].quantity -= trade_quantity
                        ret_list.append(trade)

                        if(self.book.bid_level[best_bid][0].quantity == 0):
                            self.book.cancel_order(maker_id)


                else:
                    break
                
            if o.quantity > 0:
                self.book.order_details(o,o.side)
                return ret_list

        return ret_list

    def market_order(self,side:int,quantity:int):
        ret_list = []

        if quantity <= 0:
                    ret_list.append(Rejected(None,"invalid Quantity"))
                    return ret_list

        if side != 0 and side != 1 :
            ret_list.append(Rejected(None,"Choose either buy or sell"))
            return ret_list


        o = self.book.create_order(None,side,quantity)
        ret_list.append(Ack(o.id,None))

        if side == 0 :

            while(o.quantity):
                best_ask = self.book.best_ask()
                if(best_ask is None):
                    break

                while(best_ask in self.book.ask_level and o.quantity > 0 and  len(self.book.ask_level[best_ask]) != 0):

                    maker_quantity = self.book.ask_level[best_ask][0].quantity
                    maker_id = self.book.ask_level[best_ask][0].id
                    trade_quantity = min(o.quantity,maker_quantity)

                    trade = Trade(maker_id , o.id,best_ask,trade_quantity)
                    self.trade_book.append(trade)

                    o.quantity -= trade_quantity
                    self.book.ask_level[best_ask][0].quantity -= trade_quantity
                    ret_list.append(trade)

                    if(self.book.ask_level[best_ask][0].quantity == 0):
                        self.book.cancel_order(maker_id)

            return ret_list


        if side == 1 :

            while(o.quantity):
                best_bid = self.book.best_bid()
                if(best_bid is None):
                    break

                while(best_bid in self.book.bid_level and o.quantity > 0 and  len(self.book.bid_level[best_bid]) != 0):

                    maker_quantity = self.book.bid_level[best_bid][0].quantity
                    maker_id = self.book.bid_level[best_bid][0].id
                    trade_quantity = min(o.quantity,maker_quantity)

                    trade = Trade(maker_id , o.id,best_bid,trade_quantity)
                    self.trade_book.append(trade)

                    o.quantity -= trade_quantity
                    self.book.bid_level[best_bid][0].quantity -= trade_quantity
                    ret_list.append(trade)

                    if(self.book.bid_level[best_bid][0].quantity == 0):
                        self.book.cancel_order(maker_id)

            return ret_list
        return ret_list

    def ioc_order(self,price:int,side:int,quantity:int):
        ret_list = []

        if quantity <= 0:
            ret_list.append(Rejected(None,"invalid Quantity"))
            return ret_list
        if price <= 0:
            ret_list.append(Rejected(None,"invalid Price"))
            return ret_list

        if side != 0 and side != 1 :
            ret_list.append(Rejected(None,"Choose either buy or sell"))
            return ret_list


        o = self.book.create_order(price, side, quantity)
        ret_list.append(Ack(o.id,None))

        if side == 0 : #Buy order

            while(o.quantity):

                best_ask = self.book.best_ask()
                if(best_ask is None):
                    break

                if(best_ask <= o.price):

                    while(best_ask in self.book.ask_level and o.quantity > 0 and  len(self.book.ask_level[best_ask]) != 0):

                        maker_quantity = self.book.ask_level[best_ask][0].quantity
                        maker_id = self.book.ask_level[best_ask][0].id
                        trade_quantity = min(o.quantity,maker_quantity)

                        trade = Trade(maker_id , o.id,best_ask,trade_quantity)
                        self.trade_book.append(trade)

                        o.quantity -= trade_quantity
                        self.book.ask_level[best_ask][0].quantity -= trade_quantity
                        ret_list.append(trade)

                        if(self.book.ask_level[best_ask][0].quantity == 0):
                            self.book.cancel_order(maker_id)


                else:
                    break

            if o.quantity > 0:
                ret_list.append(Cancelled(o.id,o.quantity))
                return ret_list


        elif side == 1 : #ask order

            while(o.quantity):

                best_bid = self.book.best_bid()
                if(best_bid is None):
                    break

                if(best_bid >= o.price):

                    while(best_bid in self.book.bid_level and o.quantity > 0 and  len(self.book.bid_level[best_bid]) != 0):

                        maker_quantity = self.book.bid_level[best_bid][0].quantity
                        maker_id = self.book.bid_level[best_bid][0].id
                        trade_quantity = min(o.quantity,maker_quantity)

                        trade = Trade(maker_id , o.id,best_bid,trade_quantity)
                        self.trade_book.append(trade)

                        o.quantity -= trade_quantity
                        self.book.bid_level[best_bid][0].quantity -= trade_quantity
                        ret_list.append(trade)

                        if(self.book.bid_level[best_bid][0].quantity == 0):
                            self.book.cancel_order(maker_id)


                else:
                    break

            if o.quantity > 0:
                ret_list.append(Cancelled(o.id,o.quantity))
                return ret_list


        return ret_list


    def fok_order(self,price:int,side:int, quantity:int):
        ret_list = []

        if quantity <= 0:
            ret_list.append(Rejected(None,"invalid Quantity"))
            return ret_list
        if price <= 0:
            ret_list.append(Rejected(None,"invalid Price"))
            return ret_list

        if side != 0 and side != 1 :
            ret_list.append(Rejected(None,"Choose either buy or sell"))
            return ret_list


        if side == 0:
            total = 0
            for k in self.book.ask_level.keys():
                if k<=price:
                    total += self.book.quantity_in_ask(k)

            if total >= quantity :
                return self.matching_order(price,side,quantity)

            else:
                o = self.book.create_order(price,side,quantity)
                ret_list.append(Ack(o.id,None))
                ret_list.append(Cancelled(o.id,o.quantity))
                return ret_list

        elif side == 1:
            total = 0
            for k in self.book.bid_level.keys():
                if k>=price:
                    total += self.book.quantity_in_bid(k)

            if total >= quantity :
                return self.matching_order(price,side,quantity)

            else:
                o = self.book.create_order(price,side,quantity)
                ret_list.append(Ack(o.id,None))
                ret_list.append(Cancelled(o.id,o.quantity))
                return ret_list

        return ret_list

    def cancel_order(self, id:int):
        ret_list = []
        if not self.book.get_order(id):
            ret_list.append(Rejected(None,"No order with this id exists"))
            return ret_list

        o = self.book.get_order(id)
        quantity = o.quantity
        self.book.cancel_order(id)
        ret_list.append(Cancelled(id,quantity))

        return ret_list

    def modify_order(self, id: int, price: int | None, quantity: int):
        if self.book.get_order(id) is None:
            return [Rejected(None, "No order with this id exists")]

        if price is not None and price <= 0:
            return [Rejected(None, "Invalid Price")]

        if quantity <= 0:
            return [Rejected(None, "Invalid Quantity")]

        order = self.book.get_order(id)

        # None means retain the current price.
        new_price = order.price if price is None else price

        # No change: preserve ID and FIFO priority.
        if new_price == order.price and quantity == order.quantity:
            return [Ack(order.id, None)]

        # A price change loses priority and must go through matching.
        # Cancel the old resting order, then submit the replacement
        # as a new limit order. This also handles crossing prices.
        if new_price != order.price:
            side = order.side
            self.book.cancel_order(id)

            return self.matching_order(
                new_price,
                side,
                quantity,
            )

        # Price is unchanged. Update the existing order in its queue.
        if quantity > order.quantity:
            if order.side == 0:
                level = self.book.bid_level[order.price]
            else:
                level = self.book.ask_level[order.price]

            # Quantity increase loses FIFO priority but retains the ID.
            level.remove(order)
            order.quantity = quantity
            level.append(order)

        else:
            # Quantity decrease preserves FIFO priority and the ID.
            order.quantity = quantity

        return [Ack(order.id, "order modified")]
