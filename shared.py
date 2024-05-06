class DataHandler:
    _order_buffer: list[dict]
    def __init__(self, test: str, products:dict, metrics):
        self.test = test
        self.products = products
        self._order_buffer = []
        self._metrics = metrics

    @property
    def metrics(self):
        return self._metrics()


    @property
    def available(self):
        return len(self._order_buffer)>0

    def add_order(self, order: dict):
        self._order_buffer.append(order)

    def get_order(self):
        if self.available:
            return self._order_buffer.pop(0)
        else:
            raise IndexError("No available orders")

