from __future__ import annotations


class BaseProductTrader:
    def __init__(self, product: str, position_limit: int) -> None:
        self.product = product
        self.position_limit = position_limit

    def run(self, state):
        raise NotImplementedError


class Trader:
    def __init__(self) -> None:
        self.product_traders = {}

    def run(self, state):
        orders = {}
        for product, trader in self.product_traders.items():
            orders[product] = trader.run(state)
        return orders, 0, ""

