from dataclasses import dataclass
import heapq

@dataclass
class Order:
    price:int | None
    id:int
    side:int
    quantity:int

    def __lt__(self,other):
        if(self.side == 0):
            return self.price < other.price 
        if(self.side == 1):
            return self.price < other.price 


class Order_Book:

    def __init__(self):
        self.bid = []
        self.ask = []
        self.id = 0
        self.bid_level = {}
        self.ask_level = {}
        self.order_lookup = {}

    def order_details(self,o:Order,side:int):
        if o.price is None:
            raise ValueError('Price is None')
        if side == 0 :
            #bid
            self.order_lookup[o.id] = o
            
            if o.price in self.bid_level:
                self.bid_level[o.price].append(o)
            else:
                self.bid_level[o.price] = [o]
                heapq.heappush_max(self.bid,o.price)
            return o

        elif side == 1 :
            #ask
            self.order_lookup[o.id] = o
            
            if o.price in self.ask_level:
                self.ask_level[o.price].append(o)
            else:
                self.ask_level[o.price] = [o]
                heapq.heappush(self.ask,o.price)
        
            return o

    def best_bid(self):
        if self.bid == []:
            return None
        return self.bid[0]
    
    def best_ask(self):
        if self.ask == []:
            return None
        return self.ask[0]

    def quantity_in_ask(self,price:int):
        if price not in self.ask_level:
            return 0
        return sum(order.quantity for order in self.ask_level[price])
    
    def quantity_in_bid(self,price:int):
        if price not in self.bid_level:
            return 0
        return sum(order.quantity for order in self.bid_level[price])


    def get_order(self,order_id:int):
        return self.order_lookup.get(order_id)

    def cancel_order(self,order_id:int):
        order = self.order_lookup.get(order_id)
        if order is None:
            return None
        if order.side == 0:
            self.bid_level[order.price].remove(order)
            if self.bid_level[order.price] == []:
                self.bid_level.pop(order.price)
                self.bid = list(self.bid_level.keys())
                heapq.heapify_max(self.bid)

        elif order.side == 1:
            self.ask_level[order.price].remove(order)
            if self.ask_level[order.price] == []:
                self.ask_level.pop(order.price)
                self.ask = list(self.ask_level.keys())
                heapq.heapify(self.ask)


        self.order_lookup.pop(order_id)



    def create_order(self,price:int, side:int, quantity:int):
        self.id += 1
        o = Order(price,self.id,side,quantity)

        return o