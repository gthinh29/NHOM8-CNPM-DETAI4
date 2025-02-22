class InsufficientStockError(Exception):
    def __init__(self, product_name, available_stock):
        self.message = f"{product_name} chỉ còn {available_stock} sản phẩm trong kho"
        super().__init__(self.message)