from dataclasses import dataclass
from order_book import Order_Book

@dataclass(frozen=True)
class Ack:
    order_id:int

@dataclass(frozen=True)
class Trade:
    maker_id:int
    taker_id:int
    price:int
    quantity:int

@dataclass(frozen=True)
class Cancelled:
    order_id:int

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
        ret_list.append(Ack(o.id))

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









            