class DataHandler:
    """DataHandler is a platform for the main and web threads to communicate and transfer data."""

    # stores orders in a buffer if there is a queue.
    _order_buffer: list[dict]

    def __init__(self, products: dict, metrics, ping):
        # initialize shared objects
        self.ping = ping
        self.products = products
        self._order_buffer = []
        # metrics is a function from main that has been mirrored as a 'pipe' in _metrics
        self._metrics = metrics

    @property
    def metrics(self):
        """Get metrics values from main, can be called from any instance of DataHandler"""
        return self._metrics()

    @property
    def available(self):
        """Returns True if there are orders queued from the web thread"""
        return len(self._order_buffer) > 0

    def add_order(self, order: dict):
        """Queue an order to be handled by main thread"""
        self._order_buffer.append(order)

    def get_order(self):
        """Gets the earliest order in the queue."""
        if self.available:
            return self._order_buffer.pop(0)
        else:
            raise IndexError("No available orders")
