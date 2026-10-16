from dataclasses import dataclass
import heapq

@dataclass
class Order:
    price:int
    sequence_no:int
    id:int
    side:int
    quantity:int

    def __lt__(self,other):
        if(self.side == 0):
            if(self.price == other.price):
                return self.sequence_no > other.sequence_no
            return self.price < other.price 
        if(self.side == 1):
            if(self.price == other.price):
                return self.sequence_no < other.sequence_no
            return self.price < other.price 


class Order_Book:

    def __init__(self):
        self.bid = []
        self.ask = []
        self.sequence = 0
        self.id = 0

    def order_details(self,price:int, side:int,  quantity:int):
        if side == 0 :
            #bid
            self.sequence = self.sequence + 1
            self.id += 1
            o = Order(price,self.sequence,self.id,side,quantity)
            heapq.heappush_max(self.bid,o)
            return o

        elif side == 1 :
            #ask
            self.sequence = self.sequence + 1
            self.id += 1
            o = Order(price,self.sequence,self.id,side,quantity)
            heapq.heappush(self.ask,o)
            return o

    





